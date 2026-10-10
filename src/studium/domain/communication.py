"""Factual correspondence; states are projections, never stored workflow flags."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from studium.domain.entities import StudiumEntity, validate_order
from studium.domain.value_objects import EntityId, UtcInstant, require_text


class AuthorRole(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"


class CommunicationChannel(StrEnum):
    MANUAL = "MANUAL"
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    OTHER = "OTHER"


class CommunicationState(StrEnum):
    WAITING = "WAITING"
    ANSWERED = "ANSWERED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, kw_only=True)
class QuestionCase(StudiumEntity):
    student_id: EntityId
    opened_at: UtcInstant
    course_offering_id: EntityId | None = None
    title: str | None = None
    closed_at: UtcInstant | None = None

    def __post_init__(self):
        if self.title is not None:
            require_text(self.title, "title")
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("Question closes before opening")


@dataclass(frozen=True, kw_only=True)
class Message(StudiumEntity):
    question_case_id: EntityId
    author_role: AuthorRole
    channel: CommunicationChannel
    sent_at: UtcInstant
    body: str
    external_system: str | None = None
    external_account_key: str | None = None
    external_thread_id: str | None = None
    external_message_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.author_role, AuthorRole) or not isinstance(
            self.channel, CommunicationChannel
        ):
            raise ValueError("Known author role and channel required")
        require_text(self.body, "body")
        values = self.external_key
        if any(v is not None for v in values):
            if any(v is None or not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError("External identity requires all four nonblank scope fields")
            if self.channel == CommunicationChannel.MANUAL:
                raise ValueError("Manual messages have no external identity")

    @property
    def external_key(self):
        return (
            self.external_system,
            self.external_account_key,
            self.external_thread_id,
            self.external_message_id,
        )


def message_order(message):
    return (message.sent_at, message.created_at, message.id)


def communication_state(case, messages):
    if case.closed_at is not None:
        return CommunicationState.CLOSED
    active = [m for m in messages if m.deleted_at is None]
    latest = max(active, key=message_order, default=None)
    return (
        CommunicationState.ANSWERED
        if latest and latest.author_role == AuthorRole.TEACHER
        else CommunicationState.WAITING
    )


@dataclass(frozen=True, kw_only=True)
class QuestionCaseAssessment(StudiumEntity):
    question_case_id: EntityId
    assessment_id: EntityId


@dataclass(frozen=True, kw_only=True)
class QuestionCaseAttempt(StudiumEntity):
    question_case_id: EntityId
    attempt_id: EntityId


@dataclass(frozen=True, kw_only=True)
class QuestionCaseTopic(StudiumEntity):
    question_case_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class QuestionCaseSkill(StudiumEntity):
    question_case_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class MessageAttachment(StudiumEntity):
    message_id: EntityId
    file_asset_id: EntityId
    caption: str | None = None
    sort_order: int = 0

    def __post_init__(self):
        validate_order(self.sort_order)


@dataclass(frozen=True)
class ImportedCommunication:
    """Adapter output. Scope keys are opaque strings, not credentials or paths."""

    author_role: AuthorRole
    channel: CommunicationChannel
    sent_at: UtcInstant
    body: str
    external_system: str
    external_account_key: str
    external_thread_id: str
    external_message_id: str

    def __post_init__(self):
        if self.channel == CommunicationChannel.MANUAL:
            raise ValueError("Manual messages have no external identity")
        for value in (
            self.external_system,
            self.external_account_key,
            self.external_thread_id,
            self.external_message_id,
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Importer requires a complete external identity")


class CommunicationImporter(Protocol):
    def read_messages(self) -> list[ImportedCommunication]: ...
