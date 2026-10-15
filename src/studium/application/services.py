"""Local desktop use cases. No Qt, SQL or ORM dependencies."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from types import MappingProxyType

from studium.application.analytics import AnalyticsService
from studium.application.annual_programs import AnnualProgramService
from studium.application.backup import BackupService
from studium.application.communication_services import CommunicationService
from studium.application.content_services import ContentService
from studium.application.deletion_services import DeletionService
from studium.application.errors import ApplicationError
from studium.application.file_ports import FileOpener, FileStorage, ThumbnailCache
from studium.application.file_services import AttachmentService
from studium.application.item_result_services import ItemResultService
from studium.application.journal import JournalService
from studium.application.learning_services import LearningService
from studium.application.ports import Preferences, Repositories, Transaction
from studium.application.program_exchange import ProgramExchangeService
from studium.application.program_services import ProgramService
from studium.application.progress_charts import ProgressChartsService
from studium.application.qa_services import QAPackageService
from studium.application.reporting import ReportingService
from studium.application.view_models import (
    ActivityEntry,
    GroupSummary,
    HistoryEntry,
    OfferingContext,
    ProgressMatrix,
    RosterEntry,
    WorkCell,
    WorkHistory,
)
from studium.application.workflow_analytics import WorkflowAnalyticsService
from studium.domain import entities as e
from studium.domain.enums import AssessmentType, AttemptResult, EnrollmentStatus, GradeKind
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, EntityMetadata, LocalDate, UtcInstant


@dataclass(frozen=True)
class GradeInput:
    kind: GradeKind
    passed: bool | None = None
    label: str | None = None


class StudiumService(
    AnnualProgramService,
    ProgramExchangeService,
    QAPackageService,
    ReportingService,
    DeletionService,
    ProgressChartsService,
    JournalService,
    ProgramService,
    LearningService,
    AttachmentService,
    CommunicationService,
    ItemResultService,
    AnalyticsService,
    ContentService,
    WorkflowAnalyticsService,
):
    def __init__(
        self,
        repositories: Repositories,
        transaction: Transaction,
        preferences: Preferences,
        *,
        clock: Callable[[], UtcInstant] = UtcInstant.now,
        file_storage: FileStorage | None = None,
        file_opener: FileOpener | None = None,
        thumbnails: ThumbnailCache | None = None,
        backups: BackupService | None = None,
        program_exchange=None,
    ):
        self._r = repositories
        self._transaction = transaction
        self._preferences = preferences
        self._clock = clock
        self._file_storage = file_storage
        self._file_opener = file_opener
        self._thumbnails = thumbnails
        self.backups = backups
        self._program_exchange = program_exchange

    def _meta(self):
        return EntityMetadata.create(self._clock())

    @staticmethod
    def _require(repository, id, *, historical=False):
        value = repository.find_by_id(id, include_deleted=historical)
        if value is None:
            raise RepositoryError(RepositoryFailure.NOT_FOUND, "Object not found")
        return value

    def _update(self, repository, original, **values):
        updated = replace(original, metadata=original.metadata.touch(self._clock()), **values)
        repository.update(updated, expected_revision=original.revision)
        return updated

    def list_terms(self):
        return sorted(self._r.terms.list(), key=lambda t: (t.starts_on, t.name), reverse=True)

    def table_widths(self, key):
        return getattr(self._preferences, "table_widths", lambda key: ())(key)

    def save_table_widths(self, key, widths):
        getattr(self._preferences, "save_table_widths", lambda key, widths: None)(key, widths)

    def active_term(self):
        terms = self.list_terms()
        selected = self._preferences.active_term()
        return next(
            (t for t in terms if t.id == selected), next((t for t in terms if not t.archived), None)
        )

    def select_term(self, id: EntityId):
        self._require(self._r.terms, id)
        self._preferences.select_term(id)

    def create_term(
        self, name: str, starts_on: LocalDate, ends_on: LocalDate, *, week_utc_offset_minutes=180
    ):
        term = e.AcademicTerm(
            metadata=self._meta(),
            name=name.strip(),
            starts_on=starts_on,
            ends_on=ends_on,
            week_utc_offset_minutes=week_utc_offset_minutes,
        )
        self._r.terms.insert(term)
        self.select_term(term.id)
        return term

    def update_term(self, original: e.AcademicTerm, **values):
        return self._update(self._r.terms, original, **values)

    def list_courses(self):
        return sorted(self._r.courses.list(), key=lambda c: c.name.casefold())

    def create_course(self, name: str, short_name: str = "", description: str = ""):
        value = e.Course(
            metadata=self._meta(),
            name=name.strip(),
            short_name=short_name.strip(),
            description=description.strip(),
        )
        self._r.courses.insert(value)
        return value

    def update_course(self, original: e.Course, **values):
        return self._update(self._r.courses, original, **values)

    def create_group(
        self,
        number: str,
        department: str = "",
        notes: str = "",
        faculty: str = "",
        faculty_short: str = "",
    ):
        value = e.StudentGroup(
            metadata=self._meta(),
            number=number.strip(),
            department=department.strip(),
            faculty=faculty.strip(),
            faculty_short=faculty_short.strip(),
            notes=notes.strip(),
        )
        self._r.groups.insert(value)
        return value

    def update_group(self, original: e.StudentGroup, **values):
        return self._update(self._r.groups, original, **values)

    def hide(self, kind: str, original):
        self.safe_delete(kind, original)

    @staticmethod
    def _contexts(r: Repositories):
        terms = {t.id: t for t in r.terms.list()}
        courses = {c.id: c for c in r.courses.list()}
        groups = {g.id: g for g in r.groups.list()}
        return [
            OfferingContext(o, terms[o.term_id], courses[o.course_id], groups[o.group_id])
            for o in r.offerings.list()
            if o.term_id in terms and o.course_id in courses and o.group_id in groups
        ]

    def list_offerings(self, *, group_id=None, term_id=None):
        with self._transaction() as r:
            return sorted(
                (
                    c
                    for c in self._contexts(r)
                    if (group_id is None or c.group.id == group_id)
                    and (term_id is None or c.term.id == term_id)
                ),
                key=lambda c: (
                    c.group.number.casefold(),
                    c.course.name.casefold(),
                    c.offering.created_at,
                    c.offering.id,
                ),
            )

    def create_offering(
        self,
        term_id: EntityId,
        course_id: EntityId,
        group_id: EntityId,
        work_program_id=None,
        *,
        course_version_id=None,
        course_semester=None,
    ):
        with self._transaction() as r:
            self._require(r.terms, term_id)
            self._require(r.courses, course_id)
            self._require(r.groups, group_id)
            # Desktop command is idempotent; schema allows other future teaching contexts.
            existing = next(
                (
                    o
                    for o in r.offerings.for_group(group_id)
                    if o.term_id == term_id and o.course_id == course_id
                ),
                None,
            )
            if existing:
                if work_program_id and existing.work_program_id != work_program_id:
                    raise ApplicationError("program_context_has_facts")
                if course_version_id:
                    plans = r.semester_plans.for_owner(existing.id)
                    if plans and (
                        plans[0].program_version_id != course_version_id
                        or plans[0].course_semester != course_semester
                    ):
                        raise ApplicationError("program_context_has_facts")
                    if not plans:
                        self._assign_initial_plan(r, existing, course_version_id, course_semester)
                return existing
            if work_program_id:
                program = self._require(r.work_programs, work_program_id)
                if program.course_id != course_id or program.term_id != term_id:
                    raise ApplicationError("learning_course_mismatch")
            else:
                program = self._default_program(
                    r,
                    self._require(r.terms, term_id),
                    self._require(r.courses, course_id),
                    self._require(r.groups, group_id),
                )
            offering = e.CourseOffering(
                metadata=self._meta(),
                term_id=term_id,
                course_id=course_id,
                group_id=group_id,
                work_program_id=program.id,
            )
            r.offerings.insert(offering)
            if course_version_id:
                if course_semester is None:
                    raise ValueError("Сопоставьте номер семестра курса явно")
                self._assign_initial_plan(r, offering, course_version_id, course_semester)
            return offering

    def groups(self, term_id: EntityId | None = None):
        with self._transaction() as r:
            groups = sorted(r.groups.list(), key=lambda g: g.number.casefold())
            contexts = self._contexts(r)
            offering_group = {
                c.offering.id: c.group.id
                for c in contexts
                if term_id is None or c.term.id == term_id
            }
            students = {s.id for s in r.students.list() if s.active}
            members = defaultdict(set)
            for enrollment in r.enrollments.list():
                if (
                    enrollment.status == EnrollmentStatus.ACTIVE
                    and enrollment.student_id in students
                    and enrollment.offering_id in offering_group
                ):
                    members[offering_group[enrollment.offering_id]].add(enrollment.student_id)
            return [GroupSummary(g, len(members[g.id])) for g in groups]

    def _context(self, r, offering_id, *, historical=False):
        o = self._require(r.offerings, offering_id, historical=historical)
        return OfferingContext(
            o,
            self._require(r.terms, o.term_id, historical=historical),
            self._require(r.courses, o.course_id, historical=historical),
            self._require(r.groups, o.group_id, historical=historical),
        )

    def list_students(self):
        return sorted(
            (s for s in self._r.students.list() if s.active), key=lambda s: s.full_name.casefold()
        )

    @staticmethod
    def _roster(r, offering_id, include_ended=False):
        enrollments = r.enrollments.for_offering(offering_id)
        students = {
            s.id: s for s in r.students.find_by_ids(x.student_id for x in enrollments) if s.active
        }
        # Re-enrollment retains history but each student appears once, latest membership wins.
        latest = {}
        for en in sorted(enrollments, key=lambda x: (x.enrolled_at, x.created_at, x.id)):
            latest[en.student_id] = en
        return sorted(
            (
                RosterEntry(students[id], en)
                for id, en in latest.items()
                if id in students and (include_ended or en.status == EnrollmentStatus.ACTIVE)
            ),
            key=lambda x: x.student.full_name.casefold(),
        )

    def list_students_for_offering(self, offering_id, *, include_ended=False):
        with self._transaction() as r:
            self._context(r, offering_id)
            return self._roster(r, offering_id, include_ended)

    def enroll_student(self, offering_id: EntityId, student_id: EntityId):
        with self._transaction() as r:
            self._context(r, offering_id)
            student = self._require(r.students, student_id)
            if not student.active:
                raise ApplicationError("inactive_student")
            value = e.Enrollment(
                metadata=self._meta(),
                student_id=student_id,
                offering_id=offering_id,
                enrolled_at=self._clock(),
            )
            r.enrollments.insert(value)
            return value

    def create_student(
        self,
        offering_id: EntityId,
        full_name: str,
        notes: str = "",
        preferred_name: str | None = None,
    ):
        with self._transaction() as r:
            self._context(r, offering_id)
            student = e.Student(
                metadata=self._meta(),
                full_name=full_name.strip(),
                preferred_name=preferred_name,
                notes=notes.strip(),
            )
            r.students.insert(student)
            r.enrollments.insert(
                e.Enrollment(
                    metadata=self._meta(),
                    student_id=student.id,
                    offering_id=offering_id,
                    enrolled_at=self._clock(),
                )
            )
            return student

    def update_student(self, original: e.Student, **values):
        return self._update(self._r.students, original, **values)

    def withdraw_student(self, original: e.Enrollment):
        if original.status != EnrollmentStatus.ACTIVE:
            raise ApplicationError("already_withdrawn")
        now = self._clock()
        value = replace(
            original,
            metadata=original.metadata.touch(now),
            status=EnrollmentStatus.WITHDRAWN,
            ended_at=now,
        )
        self._r.enrollments.update(value, expected_revision=original.revision)

    def list_assessments(self, offering_id: EntityId):
        return self._r.assessments.for_offering(offering_id)

    def create_assessment(
        self,
        offering_id: EntityId,
        title: str,
        type: AssessmentType,
        *,
        number=None,
        description="",
        issued_at=None,
        due_at=None,
        max_score=None,
        planned_issue_week=None,
        planned_due_week=None,
        homework_definition_id=None,
        program_work_id=None,
    ):
        with self._transaction() as r:
            self._context(r, offering_id)
            offering = self._require(r.offerings, offering_id)
            if offering.work_program_id:
                program = self._require(r.work_programs, offering.work_program_id)
                for week in (planned_issue_week, planned_due_week):
                    if week is not None:
                        program.week_dates(week)
            if homework_definition_id:
                definition = self._require(r.homework_definitions, homework_definition_id)
                if definition.course_id != self._context(r, offering_id).course.id:
                    raise ApplicationError("learning_course_mismatch")
            value = e.Assessment(
                metadata=self._meta(),
                offering_id=offering_id,
                title=title.strip(),
                type=type,
                number=number,
                description=description,
                issued_at=issued_at or self._clock(),
                due_at=due_at,
                planned_issue_week=planned_issue_week,
                planned_due_week=planned_due_week,
                homework_definition_id=homework_definition_id,
                program_work_id=program_work_id,
                max_score=max_score,
            )
            r.assessments.insert(value)
            return value

    def update_assessment(self, original: e.Assessment, **values):
        # An unchecked optional issue date preserves its original absolute timestamp.
        if values.get("issued_at") is None:
            values["issued_at"] = original.issued_at
        with self._transaction() as r:
            self._assert_assessment_content_edit(r, original, values)
            offering = self._require(r.offerings, original.offering_id, historical=True)
            if offering.work_program_id:
                program = self._require(r.work_programs, offering.work_program_id, historical=True)
                for field in ("planned_issue_week", "planned_due_week"):
                    if field in values and values[field] is not None:
                        program.week_dates(values[field])
            return self._update(r.assessments, original, **values)

    def get_or_create_work(self, student_id: EntityId, assessment_id: EntityId):
        work = self._r.works.find_for_student(student_id, assessment_id, include_deleted=True)
        if work:
            if work.deleted_at is not None:
                raise ApplicationError("hidden_work")
            return work
        with self._transaction() as r:
            assessment = self._require(r.assessments, assessment_id)
            self._context(r, assessment.offering_id)
            student = self._require(r.students, student_id)
            if not student.active:
                raise ApplicationError("inactive_student")
        work = e.StudentWork(
            metadata=self._meta(), student_id=student_id, assessment_id=assessment_id
        )
        try:
            self._r.works.insert(work)
        except RepositoryError as error:
            if error.failure != RepositoryFailure.DUPLICATE:
                raise
            existing = self._r.works.find_for_student(student_id, assessment_id)
            if existing is None:
                raise
            return existing
        return work

    @staticmethod
    def _grade(attempt, specification, metadata):
        if specification is None:
            return None
        common = {"metadata": metadata, "attempt_id": attempt.id}
        match specification.kind:
            case GradeKind.PASS_FAIL:
                if (specification.passed is True and attempt.result != AttemptResult.ACCEPTED) or (
                    specification.passed is False
                    and attempt.result not in {AttemptResult.NEEDS_REVISION, AttemptResult.REJECTED}
                ):
                    raise ApplicationError("grade_result_mismatch")
                return e.Grade.pass_fail(**common, passed=specification.passed)
            case GradeKind.NUMERIC:
                if attempt.score is None:
                    raise ApplicationError("numeric_grade_requires_score")
                return e.Grade.numeric(**common, score=attempt.score, max_score=attempt.max_score)
            case GradeKind.TRADITIONAL:
                return e.Grade.traditional(**common, label=specification.label)
        raise ApplicationError("invalid_grade")

    def record_attempt(self, student_id, assessment_id, **values):
        """Quick entry: identity/numbering/validation remain in application use cases."""
        work = self.get_or_create_work(student_id, assessment_id)
        return self.add_attempt(work.id, **values)

    def student_recent_activity(self, student_id, offering_id, *, limit=5):
        """Bulk facts for the card; no file access, UI strings or new metrics."""
        with self._transaction() as r:
            self._context(r, offering_id)
            assessments = {a.id: a for a in r.assessments.for_offering(offering_id)}
            works = {
                w.id
                for w in r.works.list()
                if w.student_id == student_id and w.assessment_id in assessments
            }
            work_assessments = {w.id: w.assessment_id for w in r.works.list() if w.id in works}
            activity = [
                ActivityEntry(
                    "attempt",
                    a.occurred_at,
                    assessments[work_assessments[a.student_work_id]].title,
                    a.result,
                )
                for a in r.attempts.list()
                if a.student_work_id in works
            ]
            cases = {
                c.id: c
                for c in r.question_cases.list()
                if c.student_id == student_id and c.course_offering_id == offering_id
            }
            activity.extend(
                ActivityEntry("question", m.sent_at, cases[m.question_case_id].title or "")
                for m in r.messages.list()
                if m.question_case_id in cases
            )
            return tuple(sorted(activity, key=lambda a: a.occurred_at, reverse=True)[:limit])

    def add_attempt(
        self,
        work_id: EntityId,
        occurred_at: UtcInstant,
        result: AttemptResult,
        *,
        comment="",
        score=None,
        max_score=None,
        grade: GradeInput | None = None,
    ):
        with self._transaction() as r:
            work = self._require(r.works, work_id)
            student = self._require(r.students, work.student_id)
            assessment = self._require(r.assessments, work.assessment_id)
            if assessment.type == AssessmentType.HOMEWORK and result == AttemptResult.REJECTED:
                raise ApplicationError("homework_requires_revision")
            self._context(r, assessment.offering_id)
            if not student.active:
                raise ApplicationError("inactive_student")
            if not any(
                en.student_id == student.id and en.status == EnrollmentStatus.ACTIVE
                for en in r.enrollments.for_offering(assessment.offering_id)
            ):
                raise ApplicationError("active_enrollment_required")
        # Release the read transaction before writing. UNIQUE + monotonic-number trigger
        # arbitrate concurrent writers; a losing writer retries with a fresh snapshot.
        for _ in range(5):
            history = self._r.attempts.history(work_id, include_deleted=True)
            number = max((a.attempt_no for a in history), default=0) + 1
            attempt = e.Attempt(
                metadata=self._meta(),
                student_work_id=work_id,
                attempt_no=number,
                occurred_at=occurred_at,
                result=result,
                comment=comment,
                score=score,
                max_score=max_score,
            )
            evaluation = self._grade(attempt, grade, self._meta())
            try:
                self._r.attempts.append(attempt, grade=evaluation)
                return attempt
            except RepositoryError as error:
                if error.failure != RepositoryFailure.DUPLICATE:
                    raise
        raise ApplicationError("concurrent_attempt")

    def history(self, work_id: EntityId):
        with self._transaction() as r:
            work = self._require(r.works, work_id, historical=True)
            assessment = self._require(r.assessments, work.assessment_id, historical=True)
            attempts = r.attempts.history(work_id)
            return WorkHistory(
                work,
                self._require(r.students, work.student_id, historical=True),
                assessment,
                self._context(r, assessment.offering_id, historical=True),
                tuple(HistoryEntry(a, r.grades.for_attempt(a.id)) for a in attempts),
                self._progress(
                    work_id,
                    attempts,
                    r.submissions.list() if r.submissions else (),
                    r.reviews.list() if r.reviews else (),
                ),
            )

    def matrix(self, offering_id: EntityId, *, include_ended=False):
        with self._transaction() as r:
            context = self._context(r, offering_id)
            roster = self._roster(r, offering_id, include_ended)
            assessments = r.assessments.for_offering(offering_id)
            works = r.works.for_assessments(a.id for a in assessments)
            histories = defaultdict(list)
            for attempt in r.attempts.for_works(w.id for w in works):
                histories[attempt.student_work_id].append(attempt)
            submissions = r.submissions.list() if r.submissions else ()
            reviews = r.reviews.list() if r.reviews else ()
            by_pair = {(w.student_id, w.assessment_id): w for w in works}
            cells = {}
            for entry in roster:
                for assessment in assessments:
                    pair = entry.student.id, assessment.id
                    work = by_pair.get(pair)
                    cells[pair] = WorkCell(
                        *pair,
                        work,
                        self._progress(work.id, histories[work.id], submissions, reviews)
                        if work
                        else None,
                    )
            return ProgressMatrix(
                context, tuple(roster), tuple(assessments), MappingProxyType(cells)
            )
