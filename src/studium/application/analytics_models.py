"""Export-ready, immutable metrics. Rates and normalized scores are 0..1 or None."""

from dataclasses import dataclass

from studium.domain.entities import Assessment
from studium.domain.enums import StudentWorkStatus
from studium.domain.value_objects import EntityId, UtcInstant


@dataclass(frozen=True)
class StudentWorkFacts:
    assessment: Assessment
    work_id: EntityId | None
    status: StudentWorkStatus
    attempts: int
    first_submission: UtcInstant | None
    latest_submission: UtcInstant | None
    completed_at: UtcInstant | None
    deadline_relation: str


@dataclass(frozen=True)
class AttendanceSummary:
    lessons_total: int
    present: int
    absent: int
    late: int
    excused: int
    unknown: int
    unmarked: int
    attendance_rate: float | None


@dataclass(frozen=True)
class QuestionAnalyticsSummary:
    question_cases_count: int
    open_questions: int
    questions_waiting_for_teacher: int
    student_message_count: int
    teacher_message_count: int
    completed_response_count: int
    unanswered_episode_count: int
    ambiguous_response_count: int
    average_teacher_response_seconds: float | None
    median_teacher_response_seconds: float | None
    assessment_linked_count: int
    topic_linked_count: int
    skill_linked_count: int


@dataclass(frozen=True)
class EvidenceSummary:
    id: EntityId
    title: str
    course_id: EntityId
    as_of: UtcInstant
    evidence_count: int
    assessment_attempt_count: int
    students_with_evidence: int
    item_result_count: int
    correct: int
    partial: int
    incorrect: int
    evaluated: int
    not_evaluated: int
    average_normalized_item_score: float | None
    question_cases_linked: int
    questions_by_students_count: int
    student_message_count: int
    lesson_exposure_count: int
    attendance: AttendanceSummary
    evidence_ids: tuple[tuple[str, EntityId], ...]


@dataclass(frozen=True)
class TopicEvidenceSummary(EvidenceSummary):
    assessments_covering_topic: int
    assessment_items_covering_topic: int
    includes_descendants: bool


@dataclass(frozen=True)
class SkillEvidenceSummary(EvidenceSummary):
    assessments_covering_skill: int
    assessment_items_covering_skill: int


@dataclass(frozen=True)
class StudentProgressSummary:
    student_id: EntityId
    offering_id: EntityId
    as_of: UtcInstant
    assessments_total: int
    deadline_assessments_total: int
    assessments_started: int
    assessments_completed: int
    completion_rate: float | None
    attempts_total: int
    average_attempts_per_started_work: float | None
    first_pass_count: int
    first_pass_rate: float | None
    passed_count: int
    overdue_count: int
    on_time_count: int
    late_count: int
    on_time_rate: float | None
    average_normalized_score: float | None
    attendance: AttendanceSummary
    questions: QuestionAnalyticsSummary
    topics: tuple[TopicEvidenceSummary, ...]
    skills: tuple[SkillEvidenceSummary, ...]

    @property
    def question_cases_total(self) -> int:
        return self.questions.question_cases_count

    @property
    def open_questions(self) -> int:
        return self.questions.open_questions

    @property
    def questions_waiting_for_teacher(self) -> int:
        return self.questions.questions_waiting_for_teacher


@dataclass(frozen=True)
class CompletionDistribution:
    completed_count: int
    student_count: int


@dataclass(frozen=True)
class GroupAnalyticsSummary:
    offering_id: EntityId
    as_of: UtcInstant
    student_count: int
    assessments_total: int
    deadline_assessments_total: int
    assessments_started: int
    assessments_completed: int
    completion_distribution: tuple[CompletionDistribution, ...]
    average_completion_rate: float | None
    first_pass_count: int
    first_pass_rate: float | None
    attempts_total: int
    average_attempts: float | None
    on_time_count: int
    late_count: int
    overdue_count: int
    on_time_rate: float | None
    attendance: AttendanceSummary
    questions: QuestionAnalyticsSummary
    students_with_open_questions: int
    students_with_unanswered_questions: int


@dataclass(frozen=True)
class AssessmentItemAnalytics:
    item_id: EntityId
    title: str
    result_count: int
    correct: int
    partial: int
    incorrect: int
    evaluated: int
    not_evaluated: int
    average_normalized_score: float | None


@dataclass(frozen=True)
class AssessmentAnalytics:
    assessment_id: EntityId
    offering_id: EntityId
    as_of: UtcInstant
    deadline_assessments_total: int
    assigned_students: int
    started: int
    not_started: int
    in_progress: int
    passed: int
    revision_required: int
    attempts_total: int
    average_attempts: float | None
    first_pass_count: int
    first_pass_rate: float | None
    on_time_count: int
    on_time_rate: float | None
    late_count: int
    overdue_count: int
    average_normalized_score: float | None
    median_normalized_score: float | None
    items: tuple[AssessmentItemAnalytics, ...]


@dataclass(frozen=True)
class AnalyticsTimePoint:
    as_of: UtcInstant
    assessments_total: int
    assessments_started: int
    assessments_completed: int
    completion_rate: float | None
    attempts_total: int
    first_pass_rate: float | None
    on_time_rate: float | None
    attendance_rate: float | None
    question_cases_count: int
