"""Course content, independent calendars and immutable submission/review facts."""

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation

from studium.domain.entities import StudiumEntity
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind, StudentWorkStatus
from studium.domain.value_objects import EntityId, LocalDate, UtcInstant, require_text

MAX_CENTS = 9223372036854775807


def snapshot_file_ids(value):
    if isinstance(value, dict):
        return (
            {str(value["file_asset_id"])}
            if "file_asset_id" in value
            else set().union(*(snapshot_file_ids(v) for v in value.values()))
        )
    if isinstance(value, list):
        return set().union(*(snapshot_file_ids(v) for v in value))
    return set()


def score_cents(text, *, fractional=False):
    """Parse teacher input without a float conversion, rounding or truncation."""
    if not isinstance(text, (str, Decimal)):
        raise ValueError("Введите балл текстом")
    value = str(text).strip()
    if not re.fullmatch(r"\d+(?:[.,]\d{1,2})?", value):
        raise ValueError("Ожидается неотрицательный балл, не более двух знаков")
    try:
        number = Decimal(value.replace(",", "."))
    except InvalidOperation:
        raise ValueError("Некорректный балл") from None
    if not fractional and number != number.to_integral_value():
        raise ValueError("Дробный ввод выключен")
    # A local context is unnecessary: bound length before multiplying so even
    # hostile long input cannot be rounded by the default Decimal precision.
    if number > Decimal("92233720368547758.07"):
        raise ValueError("Балл превышает диапазон хранения")
    return int(number * 100)


def score_text(cents):
    if cents is None:
        return "—"
    integer, remainder = divmod(cents, 100)
    return str(integer) if not remainder else f"{integer},{remainder:02d}".rstrip("0")


def check_cents(value, *, optional=False):
    if optional and value is None:
        return
    if type(value) is not int or not 0 <= value <= MAX_CENTS:
        raise ValueError("Баллы должны быть точными целыми сотыми в диапазоне int64")


def direction_identity(code):
    code = unicodedata.normalize("NFC", code.strip())
    require_text(code, "code")
    return code, code.casefold()


def day_boundary(day, offset=180):
    local = datetime.combine(
        datetime(day.year, day.month, day.day).date(), time(), timezone(timedelta(minutes=offset))
    ) + timedelta(days=1)
    return UtcInstant(local.astimezone(UTC))


def planned_deadline(work, plan):
    """Resolve the declared deadline type against the current group calendar."""
    if work.deadline_kind == "EXACT_INCLUSIVE":
        return work.exact_due_at, False
    if work.deadline_kind == "WEEK_ONLY" and work.due_week:
        first = plan.first_week_start
        end = datetime(first.year, first.month, first.day).date() + timedelta(
            weeks=work.due_week, days=-1
        )
        return day_boundary(
            LocalDate(end.year, end.month, end.day), plan.week_utc_offset_minutes
        ), True
    if work.deadline_kind == "DATE_EXCLUSIVE" and work.due_date:
        return day_boundary(work.due_date, plan.week_utc_offset_minutes), True
    return None, False


def deadline_state(received_at, now, *, days=7, near_hours=24, offset=180):
    if type(days) is not int or days < 1 or type(near_hours) is not int or near_hours < 0:
        raise ValueError("Некорректный норматив проверки")
    if not -840 <= offset <= 840:
        raise ValueError("Некорректный часовой пояс")
    if received_at is None:
        return None, "unknown"
    local = received_at.value.astimezone(timezone(timedelta(minutes=offset)))
    deadline = UtcInstant((local + timedelta(days=days)).astimezone(UTC))
    state = (
        "overdue"
        if now > deadline
        else "near_due"
        if now.value >= deadline.value - timedelta(hours=near_hours)
        else "waiting"
    )
    return deadline, state


@dataclass(frozen=True, kw_only=True)
class Direction(StudiumEntity):
    code: str
    normalized_key: str
    name: str = ""

    def __post_init__(self):
        if (self.code, self.normalized_key) != direction_identity(self.code):
            raise ValueError("Направление должно иметь нормализованный код и ключ")


@dataclass(frozen=True, kw_only=True)
class CourseProgram(StudiumEntity):
    course_id: EntityId
    title: str
    notes: str = ""

    def __post_init__(self):
        require_text(self.title, "title")


@dataclass(frozen=True, kw_only=True)
class ProgramVersion(StudiumEntity):
    course_program_id: EntityId
    version_no: int
    content_json: str
    label: str = ""

    def __post_init__(self):
        if type(self.version_no) is not int or self.version_no < 1:
            raise ValueError("Некорректная версия содержания")
        if not isinstance(json.loads(self.content_json), dict):
            raise ValueError("Ожидается снимок содержания")


@dataclass(frozen=True, kw_only=True)
class ProgramDirection(StudiumEntity):
    program_version_id: EntityId
    direction_id: EntityId


@dataclass(frozen=True, kw_only=True)
class LegacyProgramMap(StudiumEntity):
    legacy_program_id: EntityId
    program_version_id: EntityId


@dataclass(frozen=True, kw_only=True)
class VersionReference(StudiumEntity):
    program_version_id: EntityId
    topic_id: EntityId | None = None
    skill_id: EntityId | None = None
    definition_id: EntityId | None = None
    seminar_material_id: EntityId | None = None
    literature_item_id: EntityId | None = None
    file_asset_id: EntityId | None = None

    def __post_init__(self):
        if (
            sum(
                value is not None
                for value in (
                    self.topic_id,
                    self.skill_id,
                    self.definition_id,
                    self.seminar_material_id,
                    self.literature_item_id,
                    self.file_asset_id,
                )
            )
            != 1
        ):
            raise ValueError("Ссылка версии должна иметь одну конкретную цель")


@dataclass(frozen=True, kw_only=True)
class SemesterPlan(StudiumEntity):
    offering_id: EntityId
    first_week_start: LocalDate
    weeks: int
    program_version_id: EntityId | None = None
    course_semester: int | None = None
    week_utc_offset_minutes: int = 180
    configured: bool = False

    def __post_init__(self):
        if type(self.weeks) is not int or not 1 <= self.weeks <= 104:
            raise ValueError("Семестр должен содержать 1–104 недели")
        if not -840 <= self.week_utc_offset_minutes <= 840:
            raise ValueError("Некорректный часовой пояс")
        if self.course_semester is not None and self.course_semester < 1:
            raise ValueError("Некорректный номер семестра курса")


@dataclass(frozen=True, kw_only=True)
class PlanModule(StudiumEntity):
    semester_plan_id: EntityId
    title: str
    start_week: int
    end_week: int
    sort_order: int = 0
    source_module_id: EntityId | None = None

    def __post_init__(self):
        require_text(self.title, "title")
        if not 1 <= self.start_week <= self.end_week or self.sort_order < 0:
            raise ValueError("Некорректные границы модуля")


@dataclass(frozen=True, kw_only=True)
class PlannedWork(StudiumEntity):
    semester_plan_id: EntityId
    title: str
    type: AssessmentType
    module_id: EntityId | None = None
    definition_id: EntityId | None = None
    source_work_id: EntityId | None = None
    issue_date: LocalDate | None = None
    due_date: LocalDate | None = None
    exact_due_at: UtcInstant | None = None
    deadline_kind: str = "NONE"
    due_week: int | None = None
    min_cents: int | None = None
    max_cents: int | None = None
    number: str = ""
    sort_order: int = 0
    cancelled: bool = False

    def __post_init__(self):
        require_text(self.title, "title")
        if self.deadline_kind not in {"NONE", "DATE_EXCLUSIVE", "EXACT_INCLUSIVE", "WEEK_ONLY"}:
            raise ValueError("Неизвестный вид срока")
        if self.due_week is not None and (type(self.due_week) is not int or self.due_week < 1):
            raise ValueError("Некорректная учебная неделя срока")
        check_cents(self.min_cents, optional=True)
        check_cents(self.max_cents, optional=True)
        if (self.min_cents is None) != (self.max_cents is None):
            raise ValueError("Укажите обе балльные границы")
        if (
            self.max_cents is not None
            and not 0 <= self.min_cents <= self.max_cents
            or self.max_cents == 0
        ):
            raise ValueError("Некорректный диапазон баллов")
        if self.issue_date and self.due_date and self.issue_date > self.due_date:
            raise ValueError("Срок предшествует плановой выдаче")


@dataclass(frozen=True, kw_only=True)
class PlanHistory(StudiumEntity):
    semester_plan_id: EntityId
    plan_revision: int
    snapshot_json: str
    reason: str
    provenance: str = "explicit"


@dataclass(frozen=True, kw_only=True)
class PlanContentSource(StudiumEntity):
    semester_plan_id: EntityId
    plan_module_id: EntityId | None = None
    planned_work_id: EntityId | None = None
    program_version_id: EntityId | None = None
    course_semester: int | None = None
    snapshot_json: str = "{}"
    provenance: str = "explicit"

    def __post_init__(self):
        if (self.plan_module_id is None) == (self.planned_work_id is None):
            raise ValueError("Укажите одну конкретную привязку содержания")
        if self.course_semester is not None and self.course_semester < 1:
            raise ValueError("Некорректный номер семестра содержания")
        if not isinstance(json.loads(self.snapshot_json), dict):
            raise ValueError("Ожидается снимок содержания назначения")


@dataclass(frozen=True, kw_only=True)
class LateWorkAuthorization(StudiumEntity):
    student_work_id: EntityId
    enrollment_id: EntityId
    student_id: EntityId
    assessment_id: EntityId


@dataclass(frozen=True, kw_only=True)
class IssuedWork(StudiumEntity):
    planned_work_id: EntityId
    assessment_id: EntityId
    actual_issued_at: UtcInstant | None = None
    provenance: str = "explicit"


@dataclass(frozen=True, kw_only=True)
class ScoringRule(StudiumEntity):
    assessment_id: EntityId
    sequence: int
    min_cents: int
    max_cents: int

    def __post_init__(self):
        check_cents(self.min_cents)
        check_cents(self.max_cents)
        if not self.min_cents <= self.max_cents or self.max_cents == 0 or self.sequence < 1:
            raise ValueError("Некорректное правило оценивания")


@dataclass(frozen=True, kw_only=True)
class Submission(StudiumEntity):
    attempt_id: EntityId
    received_at: UtcInstant
    rule_id: EntityId | None = None
    utc_offset_minutes: int = 180
    provenance: str = "explicit"


@dataclass(frozen=True, kw_only=True)
class Review(StudiumEntity):
    submission_id: EntityId
    review_seq: int
    result: AttemptResult
    reviewed_at: UtcInstant
    rule_id: EntityId | None = None
    score_cents: int | None = None
    min_cents: int | None = None
    max_cents: int | None = None
    comment: str = ""

    def __post_init__(self):
        if self.result == AttemptResult.PRESENTED or self.review_seq < 1:
            raise ValueError("Проверка не является новой сдачей")
        for value in (self.score_cents, self.min_cents, self.max_cents):
            check_cents(value, optional=True)
        if self.score_cents is not None:
            if self.rule_id is None or self.min_cents is None or self.max_cents is None:
                raise ValueError("Числовая проверка требует полное правило")
            if not self.min_cents <= self.score_cents <= self.max_cents:
                raise ValueError("Балл вне выбранных границ")
            if self.result not in {AttemptResult.SCORED, AttemptResult.ACCEPTED}:
                raise ValueError("Доработка не начисляет баллы")
        if self.result == AttemptResult.SCORED and self.score_cents is None:
            raise ValueError("SCORED требует балл")


@dataclass(frozen=True, kw_only=True)
class ReviewGrade(StudiumEntity):
    review_id: EntityId
    kind: GradeKind
    score_cents: int | None = None
    max_cents: int | None = None
    passed: bool | None = None
    label: str | None = None


@dataclass(frozen=True, kw_only=True)
class ReviewFile(StudiumEntity):
    review_id: EntityId
    file_asset_id: EntityId
    caption: str = ""
    sort_order: int = 0


@dataclass(frozen=True, kw_only=True)
class ReviewReturn(StudiumEntity):
    review_id: EntityId
    returned_at: UtcInstant
    comment: str = ""


@dataclass(frozen=True, kw_only=True)
class RequiredWorkSet(StudiumEntity):
    module_id: EntityId
    student_id: EntityId
    sequence: int
    reason: str


@dataclass(frozen=True, kw_only=True)
class RequiredWorkBinding(StudiumEntity):
    required_set_id: EntityId
    student_work_id: EntityId


@dataclass(frozen=True, kw_only=True)
class DebtRestoration(StudiumEntity):
    student_work_id: EntityId
    before_json: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class AnswerTemplate(StudiumEntity):
    title: str
    schema_json: str

    def __post_init__(self):
        require_text(self.title, "title")
        validate_answers(self.schema_json)


def validate_answers(document):
    values = json.loads(document) if isinstance(document, str) else document
    if not isinstance(values, list):
        raise ValueError("Ожидается список параметров ответа")
    for value in values:
        if not isinstance(value, dict) or value.get("kind") not in {"numeric", "symbolic"}:
            raise ValueError("Укажите числовой или символьный ответ")
        for field in ("name", "symbol", "value"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise ValueError("Укажите название, обозначение и значение")
        if value["kind"] == "numeric":
            try:
                number = Decimal(value["value"].replace(",", "."))
            except InvalidOperation:
                raise ValueError("Некорректная физическая величина") from None
            if not number.is_finite():
                raise ValueError("Физическая величина должна быть конечной")
        for field in ("units", "formula", "comment"):
            if field in value and not isinstance(value[field], str):
                raise ValueError("Ожидается текст без выполнения")
    return tuple(values)


@dataclass(frozen=True)
class WorkResult:
    status: StudentWorkStatus
    score: object = None
    maximum: object = None
    exact: bool = False
    source_id: EntityId | None = None


def review_result(prior, review):
    if review.result == AttemptResult.SCORED:
        if prior.status not in {StudentWorkStatus.SUBMITTED, StudentWorkStatus.ACCEPTED}:
            raise ValueError("После доработки требуется явный зачёт")
        return WorkResult(prior.status, review.score_cents, review.max_cents, True, review.id)
    if review.result in {AttemptResult.ACCEPTED, AttemptResult.NEEDS_REVISION}:
        return WorkResult(
            StudentWorkStatus.ACCEPTED
            if review.result == AttemptResult.ACCEPTED
            else StudentWorkStatus.REVISION_REQUIRED,
            review.score_cents,
            review.max_cents,
            True,
            review.id,
        )
    return prior


def result_from_events(attempts, submissions, reviews, *, target_attempt=None):
    by_attempt = {s.attempt_id: s for s in submissions}
    by_submission = defaultdict(list)
    for review in reviews:
        if review.deleted_at is None:
            by_submission[review.submission_id].append(review)
    result = WorkResult(StudentWorkStatus.NOT_STARTED)
    for attempt in sorted(attempts, key=lambda a: a.attempt_no):
        if attempt.deleted_at is not None:
            continue
        if target_attempt is not None and attempt.id != target_attempt:
            continue
        if attempt.result in {
            AttemptResult.PRESENTED,
            AttemptResult.NEEDS_REVISION,
            AttemptResult.ACCEPTED,
        }:
            status = {
                AttemptResult.PRESENTED: StudentWorkStatus.SUBMITTED,
                AttemptResult.NEEDS_REVISION: StudentWorkStatus.REVISION_REQUIRED,
                AttemptResult.ACCEPTED: StudentWorkStatus.ACCEPTED,
            }[attempt.result]
            result = WorkResult(status, attempt.score, attempt.max_score, False, attempt.id)
        elif attempt.result == AttemptResult.SCORED:
            result = WorkResult(
                StudentWorkStatus.SUBMITTED
                if result.status == StudentWorkStatus.NOT_STARTED
                else result.status,
                attempt.score,
                attempt.max_score,
                False,
                attempt.id,
            )
        submission = by_attempt.get(attempt.id)
        if submission:
            for review in sorted(by_submission[submission.id], key=lambda r: r.review_seq):
                result = review_result(result, review)
    return result
