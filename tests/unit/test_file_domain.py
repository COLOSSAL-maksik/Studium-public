import hashlib
from dataclasses import FrozenInstanceError, replace

import pytest

from studium.domain.entities import AttemptAttachment, FileAsset
from studium.domain.value_objects import EntityId, EntityMetadata, UtcInstant


def asset():
    metadata = EntityMetadata.create(UtcInstant.now())
    return FileAsset(
        metadata=metadata,
        original_filename="синтетический.pdf",
        storage_key=f"files/{metadata.id.value[:2]}/{metadata.id.value}.pdf",
        mime_type="application/pdf",
        size_bytes=0,
        sha256=hashlib.sha256(b"").hexdigest(),
    )


def test_immutable_file_asset_and_explicit_link():
    value = asset()
    link = AttemptAttachment(
        metadata=EntityMetadata.create(UtcInstant.now()),
        attempt_id=EntityId.generate(),
        file_asset_id=value.id,
        caption="page 1",
        details_json='{"page":1}',
    )
    assert link.file_asset_id == value.id and link.sort_order == 0
    with pytest.raises(FrozenInstanceError):
        value.storage_key = "changed"


@pytest.mark.parametrize(
    "changes",
    [
        {"size_bytes": -1},
        {"size_bytes": True},
        {"sha256": "0" * 63},
        {"sha256": "A" * 64},
        {"storage_key": "../outside.pdf"},
        {"storage_key": "C:/private/file.pdf"},
        {"original_filename": "../source.pdf"},
        {"original_filename": "source:stream.pdf"},
        {"original_filename": "\x00bad.pdf"},
        {"mime_type": ""},
    ],
)
def test_file_asset_rejects_invalid_contract(changes):
    with pytest.raises(ValueError):
        replace(asset(), **changes)


@pytest.mark.parametrize(
    "changes",
    [{"sort_order": -1}, {"sort_order": True}, {"details_json": "[]"}, {"details_json": "broken"}],
)
def test_attachment_validates_editable_metadata(changes):
    with pytest.raises(ValueError):
        AttemptAttachment(
            metadata=EntityMetadata.create(UtcInstant.now()),
            attempt_id=EntityId.generate(),
            file_asset_id=EntityId.generate(),
            **changes,
        )
