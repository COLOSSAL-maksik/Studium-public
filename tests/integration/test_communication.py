"""Communication facts, context, identity and shared storage on synthetic data."""

import stat
from dataclasses import replace

import pytest
from sqlalchemy import text

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.composition import create_runtime
from studium.domain.communication import (
    AuthorRole,
    CommunicationChannel,
    CommunicationState,
    ImportedCommunication,
    Message,
)
from studium.domain.enums import AttemptResult
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, EntityMetadata
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow
from tests.unit.test_domain import instant


def question(workflow, **kwargs):
    s, _, _, _, offering, student, *_ = workflow
    return s.create_question_case(
        student.id,
        "  Почему знак минус?\n\nВторая строка.  ",
        instant(),
        course_offering_id=offering.id,
        title="Знак момента",
        **kwargs,
    )


@pytest.mark.parametrize("channel", list(CommunicationChannel))
def test_capture_preserves_body_owner_offering_and_channel(workflow, channel):
    s, *_ = workflow
    case = question(workflow, channel=channel)
    message = s.list_messages(case.id)[0]
    assert s.get_question_case(case.id) == case
    assert case.student_id == workflow[5].id and case.course_offering_id == workflow[4].id
    assert message.body == "  Почему знак минус?\n\nВторая строка.  "
    assert message.author_role == AuthorRole.STUDENT and message.channel == channel
    assert all(v is None for v in message.external_key)
    assert s.list_questions_waiting_for_teacher()[0].case == case


def test_chronological_state_backdated_answer_ties_close_reopen(workflow):
    s, *_ = workflow
    case = question(workflow)
    newer = s.add_student_message(case.id, "Новый вопрос", instant(3))
    answer = s.add_teacher_message(case.id, "Ответ на первый вопрос", instant(2))
    assert [m.sent_at for m in s.list_messages(case.id)] == [instant(), instant(2), instant(3)]
    assert s.list_question_cases()[0].state == CommunicationState.WAITING
    final = s.add_teacher_message(case.id, "Последний ответ", instant(3))
    assert s.list_messages(case.id)[-1] == final
    assert s.list_question_cases()[0].state == CommunicationState.ANSWERED
    with pytest.raises(ApplicationError, match="question_close_date"):
        s.close_question_case(case, closed_at=instant(2))
    closed = s.close_question_case(case, closed_at=instant(4))
    assert closed.revision == 2 and s.list_question_cases()[0].state == CommunicationState.CLOSED
    with pytest.raises(ApplicationError, match="question_closed"):
        s.add_student_message(case.id, "Продолжение", instant(4))
    with pytest.raises(RepositoryError) as error:
        s.reopen_question_case(case)
    assert error.value.failure == RepositoryFailure.REVISION_CONFLICT
    reopened = s.reopen_question_case(closed)
    assert reopened.closed_at is None and reopened.revision == 3
    s.archive_message(final)
    assert s.list_question_cases()[0].state == CommunicationState.WAITING
    assert answer in s.list_messages(case.id) and newer in s.list_messages(case.id)


def test_queries_unicode_search_literal_percent_archive_and_restart(workflow, runtime, tmp_path):
    s, _, _, _, offering, student, *_ = workflow
    case = question(workflow)
    s.add_teacher_message(
        case.id, "Ответ с 100% уверенностью", instant(2), channel=CommunicationChannel.EMAIL
    )
    other = s.create_question_case(student.id, "Другой вопрос", instant(3))
    assert len(s.list_student_question_cases(student.id)) == 2
    assert len(s.list_question_cases()) == 2 and len(s.list_open_questions()) == 2
    assert [q.case for q in s.search_questions("МИНУС")] == [case]
    assert [q.case for q in s.search_questions("100%")] == [case]
    assert len(s.search_questions("ТЕСТОВЫЙ")) == 2
    assert [q.case for q in s.list_questions_by_course_offering(offering.id)] == [case]
    assert len(s.list_question_cases(channel=CommunicationChannel.EMAIL)) == 1
    s.archive_question_case(case)
    assert [q.case for q in s.list_question_cases()] == [other]
    assert len(s.list_messages(case.id)) == 2
    assert len(s.list_question_cases(include_deleted=True)) == 2
    runtime.close()
    reopened = create_runtime(tmp_path)
    try:
        assert len(reopened.service.list_messages(case.id)) == 2
        assert (
            reopened.service.get_question_case(case.id, include_deleted=True).deleted_at is not None
        )
    finally:
        reopened.close()


@pytest.mark.parametrize("kind", ["assessment", "attempt", "topic", "skill"])
def test_context_attach_detach_restore_and_duplicate_pair(workflow, kind):
    s, _, course, _, _, _, assessment, work = workflow
    case = question(workflow)
    targets = {
        "assessment": assessment,
        "attempt": s.add_attempt(work.id, instant(), AttemptResult.NEEDS_REVISION),
        "topic": s.create_topic(course.id, "Эпюра M"),
        "skill": s.create_skill(course.id, "Определяет знак M"),
    }
    target = targets[kind]
    first = s.attach_question_context(case.id, kind, target.id)
    assert s.attach_question_context(case.id, kind, target.id) == first
    assert s.list_question_context(case.id)[kind] == [(first, target)]
    s.detach_question_context(first, kind)
    assert not s.list_question_context(case.id)[kind]
    restored = s.attach_question_context(case.id, kind, target.id)
    assert restored.id == first.id and restored.revision == 3
    assert s.list_question_context(case.id)[kind][0][1] == target


def test_wrong_student_attempt_and_cross_course_links_are_rejected_atomically(workflow):
    s, term, _, group, offering, student, assessment, _ = workflow
    case = question(workflow)
    other = s.create_student(offering.id, "Другой синтетический студент")
    work = s.get_or_create_work(other.id, assessment.id)
    attempt = s.add_attempt(work.id, instant(), AttemptResult.PRESENTED)
    with pytest.raises(ApplicationError, match="question_context_mismatch"):
        s.attach_question_context(case.id, "attempt", attempt.id)
    course = s.create_course("Другая дисциплина")
    other_offering = s.create_offering(term.id, course.id, group.id)
    other_assessment = s.create_assessment(other_offering.id, "Другая работа", assessment.type)
    for kind, target in [
        ("assessment", other_assessment),
        ("topic", s.create_topic(course.id, "Другая тема")),
        ("skill", s.create_skill(course.id, "Другой навык")),
    ]:
        with pytest.raises(ApplicationError, match="question_context_mismatch"):
            s.attach_question_context(case.id, kind, target.id)
    before = len(s.list_question_cases())
    with pytest.raises(ApplicationError):
        s.create_question_case(
            student.id,
            "Нельзя сохранить неверный контекст",
            instant(),
            course_offering_id=offering.id,
            context={"assessment": [other_assessment.id]},
        )
    assert len(s.list_question_cases()) == before


def test_nullable_offering_missing_student_empty_body_and_bad_date(workflow):
    s, _, _, _, _, student, *_ = workflow
    with pytest.raises(RepositoryError):
        s.create_question_case(EntityId.generate(), "Вопрос", instant())
    with pytest.raises(ValueError):
        s.create_question_case(student.id, " \n\t ", instant())
    assert not s.list_question_cases()
    case = s.create_question_case(student.id, "Общий вопрос", instant(2))
    assert case.course_offering_id is None
    with pytest.raises(ApplicationError, match="question_offering_required"):
        s.attach_question_context(case.id, "assessment", workflow[6].id)
    with pytest.raises(ApplicationError, match="question_message_date"):
        s.add_teacher_message(case.id, "Неправильная дата", instant())


def test_external_identity_scope_replay_payload_conflict_and_tombstone(workflow):
    s, *_ = workflow
    case = question(workflow)
    imported = ImportedCommunication(
        AuthorRole.TEACHER,
        CommunicationChannel.TELEGRAM,
        instant(2),
        "Исходный ответ",
        "telegram:user:v1",
        "account-A",
        "chat-1",
        "17",
    )
    message = s.record_imported_message(case.id, imported)
    assert s.record_imported_message(case.id, imported) == message
    for field, value in [
        ("external_account_key", "account-B"),
        ("external_thread_id", "chat-2"),
        ("external_system", "telegram:bot:v1"),
    ]:
        assert (
            s.record_imported_message(case.id, replace(imported, **{field: value})).id != message.id
        )
    with pytest.raises(ApplicationError, match="external_message_conflict"):
        s.record_imported_message(case.id, replace(imported, body="Тихая подмена"))
    with pytest.raises(RepositoryError) as error:
        s.add_teacher_message(
            case.id,
            message.body,
            message.sent_at,
            channel=message.channel,
            **dict(
                zip(
                    (
                        "external_system",
                        "external_account_key",
                        "external_thread_id",
                        "external_message_id",
                    ),
                    message.external_key,
                    strict=True,
                )
            ),
        )
    assert error.value.failure == RepositoryFailure.DUPLICATE
    s.archive_message(message)
    assert s.record_imported_message(case.id, imported).deleted_at is not None
    other = s.create_question_case(workflow[5].id, "Другой кейс", instant())
    with pytest.raises(ApplicationError, match="external_message_conflict"):
        s.record_imported_message(other.id, imported)


@pytest.mark.parametrize(
    "external,channel",
    [
        ({"external_message_id": "1"}, CommunicationChannel.EMAIL),
        (
            {
                "external_system": "email",
                "external_account_key": "a",
                "external_thread_id": "t",
                "external_message_id": "1",
            },
            CommunicationChannel.MANUAL,
        ),
        (
            {
                "external_system": "email",
                "external_account_key": " ",
                "external_thread_id": "t",
                "external_message_id": "1",
            },
            CommunicationChannel.EMAIL,
        ),
    ],
)
def test_domain_rejects_partial_external_identity(external, channel):
    with pytest.raises(ValueError):
        Message(
            metadata=EntityMetadata.create(instant()),
            question_case_id=EntityId.generate(),
            author_role=AuthorRole.STUDENT,
            sent_at=instant(),
            body="Fact",
            channel=channel,
            **external,
        )


def test_shared_asset_multiple_files_integrity_detach_guard_and_reopen(workflow, runtime, tmp_path):
    s, *_ = workflow
    case = question(workflow)
    message = s.list_messages(case.id)[0]
    source = tmp_path / "synthetic.txt"
    source.write_text("Only synthetic bytes", encoding="utf-8")
    first = s.import_file_for_message(message.id, source)
    second = s.import_file_for_message(message.id, source)
    answer = s.add_teacher_message(case.id, "Ответ", instant(2))
    shared = s.attach_file_asset_to_message(answer.id, first.file_asset_id)
    entries = s.list_message_attachments(message.id)
    assert len(entries) == 2 and entries[0].asset.sha256 == entries[1].asset.sha256
    assert first.file_asset_id != second.file_asset_id
    assert s.list_message_attachments(answer.id)[0].asset == entries[0].asset
    with pytest.raises(ApplicationError, match="file_asset_in_use"):
        s.archive_file_asset(first.file_asset_id, expected_revision=1)
    s.detach_message_attachment(first.id, expected_revision=1)
    assert s.verify_file_integrity(first.file_asset_id) == FileIntegrity.AVAILABLE
    assert len(s.list_message_attachments(message.id, include_detached=True)) == 2
    path = s.accessible_file_path(second.file_asset_id)
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    path.write_bytes(b"X" * path.stat().st_size)
    assert s.verify_file_integrity(second.file_asset_id) == FileIntegrity.CORRUPTED
    assert len(s.list_message_attachments(message.id)) == 1
    runtime.close()
    reopened = create_runtime(tmp_path)
    try:
        assert reopened.service.list_message_attachments(answer.id)[0].attachment == shared
        assert (
            reopened.service.verify_file_integrity(second.file_asset_id) == FileIntegrity.CORRUPTED
        )
        reopened.service.detach_message_attachment(shared.id, expected_revision=1)
        reopened.service.archive_file_asset(first.file_asset_id, expected_revision=1)
    finally:
        reopened.close()


def test_message_import_db_failure_compensates_source_and_pending_files(
    workflow, monkeypatch, tmp_path
):
    s, *_ = workflow
    case = question(workflow)
    message = s.list_messages(case.id)[0]
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic", encoding="utf-8")
    from studium.infrastructure.database.repositories.communication import (
        MessageAttachmentRepository,
    )

    def fail(*_):
        raise RepositoryError(RepositoryFailure.STORAGE_UNAVAILABLE, "Synthetic failure")

    monkeypatch.setattr(MessageAttachmentRepository, "insert", fail)
    with pytest.raises(RepositoryError):
        s.import_file_for_message(message.id, source)
    assert source.read_text() == "Synthetic"
    assert not s.list_message_attachments(message.id)
    assert not s._r.file_assets.list()
    assert not list((tmp_path / "files").rglob("*.txt"))
    assert not list((tmp_path / "files/.imports").glob("*.json"))


def test_attempt_asset_reused_for_message_keeps_both_owner_histories(workflow, tmp_path):
    s, *_, work = workflow
    case = question(workflow)
    message = s.list_messages(case.id)[0]
    attempt = s.add_attempt(work.id, instant(), AttemptResult.PRESENTED)
    source = tmp_path / "synthetic-shared.txt"
    source.write_text("Synthetic shared file", encoding="utf-8")
    attempt_link = s.import_file_for_attempt(attempt.id, source)
    asset = s.get_file_asset(attempt_link.file_asset_id)
    message_link = s.attach_file_asset_to_message(message.id, asset.id)
    assert len(s._r.file_assets.list()) == 1
    assert (
        s.list_attempt_attachments(attempt.id)[0].asset
        == s.list_message_attachments(message.id)[0].asset
        == asset
    )
    s.detach_attachment(attempt_link.id, expected_revision=1)
    with pytest.raises(ApplicationError, match="file_asset_in_use"):
        s.archive_file_asset(asset.id, expected_revision=1)
    s.detach_message_attachment(message_link.id, expected_revision=1)
    s.archive_file_asset(asset.id, expected_revision=1)
    assert s.get_file_asset(asset.id, include_deleted=True).deleted_at is not None
    assert (
        s.list_attempt_attachments(attempt.id, include_detached=True)[0].asset.sha256
        == asset.sha256
    )


@pytest.mark.parametrize("after_commit", [False, True])
def test_message_import_process_crash_recovery_preserves_only_committed_bytes(
    workflow, tmp_path, after_commit
):
    import os
    import subprocess
    import sys

    s, *_ = workflow
    case = question(workflow)
    message = s.list_messages(case.id)[0]
    source = tmp_path / "synthetic-crash.txt"
    source.write_text("Synthetic crash fixture", encoding="utf-8")
    code = """
import os, sys
from pathlib import Path
from studium.composition import create_runtime
from studium.domain.value_objects import EntityId
from studium.infrastructure.file_storage import LocalFileStorage
runtime = create_runtime(Path(sys.argv[1]))
if sys.argv[4] == 'before':
    publish = LocalFileStorage._publish
    def crash(temporary, final):
        publish(temporary, final)
        os._exit(23)
    LocalFileStorage._publish = staticmethod(crash)
else:
    unlink = Path.unlink
    def crash(path, *args, **kwargs):
        if path.suffix == '.json' and path.parent.name == '.imports':
            os._exit(23)
        return unlink(path, *args, **kwargs)
    Path.unlink = crash
runtime.service.import_file_for_message(EntityId(sys.argv[2]), Path(sys.argv[3]))
raise RuntimeError('Crash hook did not execute')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(tmp_path),
            message.id.value,
            str(source),
            "after" if after_commit else "before",
        ],
        env=dict(os.environ, LOCALAPPDATA=str(tmp_path / "profile")),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 23, result.stderr
    assert list((tmp_path / "files/.imports").glob("*.json"))
    reopened = create_runtime(tmp_path)
    try:
        rows = reopened.service.list_message_attachments(message.id)
        assert len(rows) == int(after_commit)
        assert len(list((tmp_path / "files").rglob("*.txt"))) == int(after_commit)
        assert not list((tmp_path / "files/.imports").glob("*.json"))
        if rows:
            assert rows[0].integrity == FileIntegrity.AVAILABLE
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE messages SET body='overwrite', revision=revision+1",
        "UPDATE messages SET author_role='TEACHER', revision=revision+1",
        "UPDATE messages SET sent_at=sent_at+1, revision=revision+1",
        "DELETE FROM messages",
        "UPDATE question_cases SET student_id='bad', revision=revision+1",
        "DELETE FROM question_cases",
    ],
)
def test_sql_cannot_rewrite_facts_or_physically_delete_history(workflow, runtime, sql):
    s, *_ = workflow
    case = question(workflow)
    with pytest.raises(Exception):
        with runtime._engine.begin() as connection:
            connection.execute(text(sql))
    assert s.list_messages(case.id)[0].body.startswith("  Почему")


def test_sql_message_asset_archive_guard_and_fk(workflow, runtime, tmp_path):
    s, *_ = workflow
    case = question(workflow)
    message = s.list_messages(case.id)[0]
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic", encoding="utf-8")
    link = s.import_file_for_message(message.id, source)
    with pytest.raises(Exception):
        with runtime._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE file_assets SET deleted_at=updated_at,revision=revision+1 WHERE id=:id"
                ),
                {"id": link.file_asset_id.value},
            )
    with runtime._engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
