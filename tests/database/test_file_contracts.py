from dataclasses import replace

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from studium.domain.entities import AttemptAttachment
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import EntityId, EntityMetadata, UtcInstant
from tests.integration.test_files import files as files
from tests.integration.test_files import imported
from tests.integration.test_files import runtime as runtime
from tests.integration.test_files import workflow as workflow


@pytest.mark.parametrize("table", ["file_assets", "attempt_attachments"])
def test_file_tables_fk_indexes_soft_delete_and_revision(files, table):
    f = files
    imported(f)
    with f.runtime._engine.connect() as c:
        assert inspect(c).get_indexes(table)
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        if table == "attempt_attachments":
            assert {fk["referred_table"] for fk in inspect(c).get_foreign_keys(table)} == {
                "attempts",
                "file_assets",
            }
    for sql in [
        f"DELETE FROM {table}",
        f"UPDATE {table} SET revision=revision+2",
        f"UPDATE {table} SET created_at=created_at+1,updated_at=updated_at+1,revision=revision+1",
        f"UPDATE {table} SET updated_at=updated_at-1,revision=revision+1",
    ]:
        with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
            c.exec_driver_sql(sql)
    with f.runtime._engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(
    "assignment",
    [
        "original_filename='changed.txt'",
        "sha256='" + "0" * 64 + "'",
        "size_bytes=0",
        "storage_key='../outside'",
        "mime_type='other/type'",
    ],
)
def test_file_facts_immutable_under_raw_sql(files, assignment):
    f = files
    imported(f)
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(
            f"UPDATE file_assets SET {assignment},updated_at=updated_at+1,revision=revision+1"
        )


def test_owner_immutable_unique_pair_and_invalid_fk(files):
    f = files
    link, asset = imported(f)
    for changed in [
        replace(link, metadata=EntityMetadata.create(UtcInstant.now())),
        replace(
            link, metadata=EntityMetadata.create(UtcInstant.now()), attempt_id=EntityId.generate()
        ),
        replace(
            link,
            metadata=EntityMetadata.create(UtcInstant.now()),
            file_asset_id=EntityId.generate(),
        ),
    ]:
        with pytest.raises(RepositoryError):
            f.s._r.attempt_attachments.insert(changed)
    attempt2 = f.s.add_attempt(f.work.id, UtcInstant.now(), f.attempt.result)
    changed = replace(link, metadata=link.metadata.touch(UtcInstant.now()), attempt_id=attempt2.id)
    with pytest.raises(RepositoryError):
        f.s._r.attempt_attachments.update(changed, expected_revision=link.revision)
    f.s.detach_attachment(link.id, expected_revision=link.revision)
    detached = f.s._r.attempt_attachments.find_by_id(link.id, include_deleted=True)
    with pytest.raises(RepositoryError):
        f.s._r.attempt_attachments.update(
            replace(
                detached,
                metadata=replace(detached.metadata.touch(UtcInstant.now()), deleted_at=None),
            ),
            expected_revision=detached.revision,
        )
    assert f.s.verify_file_integrity(asset.id).value == "available"


def test_soft_deleted_asset_cannot_receive_link(files):
    f = files
    link, asset = imported(f)
    f.s.detach_attachment(link.id, expected_revision=link.revision)
    f.s.archive_file_asset(asset.id, expected_revision=asset.revision)
    attempt2 = f.s.add_attempt(f.work.id, UtcInstant.now(), f.attempt.result)
    with pytest.raises(RepositoryError):
        f.s._r.attempt_attachments.insert(
            AttemptAttachment(
                metadata=EntityMetadata.create(UtcInstant.now()),
                attempt_id=attempt2.id,
                file_asset_id=asset.id,
            )
        )
