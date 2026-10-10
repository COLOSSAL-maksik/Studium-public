from enum import StrEnum


class AssessmentType(StrEnum):
    HOMEWORK = "HOMEWORK"
    TEST = "TEST"
    CONTROL_WORK = "CONTROL_WORK"
    DEFENSE = "DEFENSE"
    LAB = "LAB"
    EXAM = "EXAM"
    OTHER = "OTHER"


class AttemptResult(StrEnum):
    PRESENTED = "PRESENTED"
    NEEDS_REVISION = "NEEDS_REVISION"
    ACCEPTED = "ACCEPTED"
    SCORED = "SCORED"
    REJECTED = "REJECTED"
    COMMENT_ONLY = "COMMENT_ONLY"


class StudentWorkStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUBMITTED = "SUBMITTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    ACCEPTED = "ACCEPTED"
    MISSED = "MISSED"
    EXEMPT = "EXEMPT"
    CANCELLED = "CANCELLED"


class EnrollmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    COMPLETED = "COMPLETED"


class GradeKind(StrEnum):
    PASS_FAIL = "PASS_FAIL"
    NUMERIC = "NUMERIC"
    TRADITIONAL = "TRADITIONAL"


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"
    UNKNOWN = "UNKNOWN"


class ItemOutcome(StrEnum):
    CORRECT = "CORRECT"
    PARTIAL = "PARTIAL"
    INCORRECT = "INCORRECT"
    NOT_EVALUATED = "NOT_EVALUATED"


class LessonType(StrEnum):
    SEMINAR = "SEMINAR"
    LECTURE = "LECTURE"
