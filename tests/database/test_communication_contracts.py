"""SQL callers cannot bypass communication ownership, identity or file guards."""

from dataclasses import replace

import pytest
from sqlalchemy.exc import IntegrityError

from studium.domain.communication import (
    AuthorRole,
    CommunicationChannel,
    ImportedCommunication,
    Message,
    QuestionCaseTopic,
)
from studium.domain.value_objects import EntityId
from studium.infrastructure.database.repositories import entity_values
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow
from tests.unit.test_domain import instant


def raw_insert(connection, table, values):
    columns = list(values)
    return connection.exec_driver_sql(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        tuple(values[c] for c in columns),
    )


def seeded(workflow):
    s, *_ = workflow
    case = s.create_question_case(
        workflow[5].id, "Synthetic question", instant(), course_offering_id=workflow[4].id
    )
    return s, case, s.list_messages(case.id)[0]


@pytest.mark.parametrize(
    "field,value",
    [
        ("channel", "INVALID"),
        ("author_role", "INVALID"),
        ("body", " \n\t "),
        ("external_message_id", "weak-only-id"),
        ("question_case_id", "00000000-0000-0000-0000-000000000000"),
        ("sent_at", "not an instant"),
        ("revision", 0),
        ("created_at", "bad"),
        ("id", "invalid UUID"),
    ],
)
def test_raw_message_insert_rejects_invalid_facts(field, value, workflow, runtime):
    s, case, _ = seeded(workflow)
    message = Message(
        metadata=s._meta(),
        question_case_id=case.id,
        author_role=AuthorRole.STUDENT,
        channel=CommunicationChannel.EMAIL,
        body="Synthetic",
        sent_at=instant(),
    )
    values = entity_values(message)
    values[field] = value
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            raw_insert(conn, "messages", values)
    assert len(s.list_messages(case.id)) == 1


def test_raw_context_cannot_cross_course_or_change_endpoints(workflow, runtime):
    s, case, _ = seeded(workflow)
    wrong_course = s.create_course("Different course")
    wrong_topic = s.create_topic(wrong_course.id, "Different topic")
    link = QuestionCaseTopic(metadata=s._meta(), question_case_id=case.id, topic_id=wrong_topic.id)
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            raw_insert(conn, "question_case_topics", entity_values(link))
    right = s.create_topic(workflow[2].id, "Matching topic")
    saved = s.attach_question_context(case.id, "topic", right.id)
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE question_case_topics SET topic_id=?,revision=revision+1 WHERE id=?",
                (wrong_topic.id.value, saved.id.value),
            )
    s.detach_question_context(saved, "topic")
    s.archive_topic(right)
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE question_case_topics SET deleted_at=NULL,revision=revision+1 WHERE id=?",
                (saved.id.value,),
            )


def test_raw_foreign_keys_indexes_and_no_persisted_status(workflow, runtime):
    seeded(workflow)
    with runtime._engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        for table, count in [
            ("question_cases", 2),
            ("messages", 1),
            ("message_attachments", 2),
            ("question_case_assessments", 2),
            ("question_case_attempts", 2),
            ("question_case_topics", 2),
            ("question_case_skills", 2),
        ]:
            fks = conn.exec_driver_sql(f"PRAGMA foreign_key_list({table})").fetchall()
            assert len(fks) == count and all(row[6] == "RESTRICT" for row in fks)
            assert conn.exec_driver_sql(f"PRAGMA index_list({table})").fetchall()
        columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(question_cases)")]
        assert "status" not in columns and "state" not in columns
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


def test_raw_external_identity_unique_even_after_archive(workflow, runtime):
    s, case, _ = seeded(workflow)
    imported = ImportedCommunication(
        AuthorRole.STUDENT,
        CommunicationChannel.EMAIL,
        instant(),
        "Synthetic",
        "email:rfc822:v1",
        "account",
        "thread",
        "message",
    )
    saved = s.record_imported_message(case.id, imported)
    s.archive_message(saved)
    duplicate = replace(saved, metadata=s._meta())
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            raw_insert(conn, "messages", entity_values(duplicate))


def test_metadata_revision_guard_and_soft_delete_timestamp(workflow, runtime):
    s, case, message = seeded(workflow)
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE messages SET deleted_at=updated_at WHERE id=?", (message.id.value,)
            )
    s.archive_message(message)
    archived = s.list_messages(case.id, include_deleted=True)[0]
    assert archived.revision == 2 and archived.updated_at >= message.updated_at
    assert archived.body == message.body and archived.author_role == message.author_role
    with pytest.raises(IntegrityError):
        with runtime._engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE messages SET deleted_at=NULL,revision=revision+1 WHERE id=?",
                (message.id.value,),
            )


@pytest.mark.parametrize(
    "channel,key",
    [
        (CommunicationChannel.MANUAL, "message"),
        (CommunicationChannel.EMAIL, None),
        (CommunicationChannel.EMAIL, " "),
    ],
)
def test_importer_boundary_requires_scoped_nonmanual_identity(channel, key):
    with pytest.raises(ValueError):
        ImportedCommunication(
            AuthorRole.STUDENT,
            channel,
            instant(),
            "Synthetic",
            "provider",
            "account",
            "thread",
            key,
        )


def test_unknown_author_and_invalid_close_are_domain_errors(workflow):
    s, case, _ = seeded(workflow)
    with pytest.raises(ValueError):
        Message(
            metadata=s._meta(),
            question_case_id=case.id,
            author_role="UNKNOWN",
            channel=CommunicationChannel.OTHER,
            sent_at=instant(),
            body="Synthetic",
        )
    with pytest.raises(ValueError):
        replace(
            case, closed_at=instant().from_epoch_microseconds(case.opened_at.epoch_microseconds - 1)
        )
    with pytest.raises(ValueError):
        Message(
            metadata=s._meta(),
            question_case_id=EntityId.generate(),
            author_role=AuthorRole.STUDENT,
            channel=CommunicationChannel.OTHER,
            sent_at=instant(),
            body=" \n ",
        )
