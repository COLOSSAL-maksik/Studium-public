"""Read-only analytics over one bulk-loaded transaction, with no persisted metrics.

An ``as_of`` is an event-time cutoff over current facts, not an audit snapshot.
Attempt ordering and final status continue to belong to StudentWorkProgress.
"""

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date, timedelta, timezone, tzinfo
from itertools import groupby
from statistics import mean, median

from studium.application.analytics_models import (
    AnalyticsTimePoint,
    AssessmentAnalytics,
    AssessmentItemAnalytics,
    AttendanceSummary,
    CompletionDistribution,
    GroupAnalyticsSummary,
    QuestionAnalyticsSummary,
    SkillEvidenceSummary,
    StudentProgressSummary,
    StudentWorkFacts,
    TopicEvidenceSummary,
)
from studium.application.errors import ApplicationError
from studium.domain.communication import (
    AuthorRole,
    CommunicationState,
    communication_state,
    message_order,
)
from studium.domain.enums import AttemptResult, AttendanceStatus, ItemOutcome, StudentWorkStatus
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import UtcInstant

# COMMENT_ONLY is an annotation. REJECTED is a recorded unsuccessful presentation,
# even though it is status-neutral in the existing StudentWorkProgress projection.
PRESENTATIONS = frozenset(
    {
        AttemptResult.PRESENTED,
        AttemptResult.NEEDS_REVISION,
        AttemptResult.ACCEPTED,
        AttemptResult.SCORED,
        AttemptResult.REJECTED,
    }
)
SCORE_EVENTS = PRESENTATIONS - {AttemptResult.REJECTED}


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _mean(values):
    return mean(values) if values else None


def normalized_score(score, maximum):
    """Missing maximum cannot be inferred from a mutable assessment definition."""
    return score / maximum if score is not None and maximum is not None else None


def calendar_days_late(presented_at: UtcInstant, due_at: UtcInstant, timezone: tzinfo) -> int:
    """Explicit reporting timezone; a UTC day is never assumed to be a lesson day."""
    if not isinstance(timezone, tzinfo):
        raise ValueError("An explicit reporting timezone is required")
    return max(
        0,
        (
            presented_at.value.astimezone(timezone).date()
            - due_at.value.astimezone(timezone).date()
        ).days,
    )


class _Snapshot:
    """Domain objects only; one SELECT per table, independent of matrix dimensions."""

    NAMES = (
        "terms",
        "offerings",
        "students",
        "enrollments",
        "assessments",
        "works",
        "attempts",
        "topics",
        "skills",
        "lessons",
        "attendance",
        "items",
        "assessment_topics",
        "assessment_skills",
        "item_topics",
        "item_skills",
        "lesson_topics",
        "item_results",
        "question_cases",
        "messages",
        "question_case_assessments",
        "question_case_topics",
        "question_case_skills",
        "work_programs",
    )

    def __init__(self, repositories, *, historical=False):
        for name in self.NAMES:
            # Archived taxonomy labels and explicit Enrollment remain evidence context.
            include_deleted = name in {"topics", "skills", "enrollments", "students"} or (
                historical
                and name
                in {
                    "terms",
                    "courses",
                    "groups",
                    "offerings",
                    "assessments",
                    "works",
                    "items",
                    "work_programs",
                }
            )
            setattr(
                self, name, tuple(getattr(repositories, name).list(include_deleted=include_deleted))
            )


class _View:
    def __init__(self, snapshot, as_of):
        self.data, self.as_of = snapshot, as_of
        self.offerings = {o.id: o for o in snapshot.offerings}
        self.terms = {t.id: t for t in snapshot.terms}
        self.programs = {p.id: p for p in snapshot.work_programs}
        self.students = {s.id: s for s in snapshot.students}
        self.enrollments = {e.id: e for e in snapshot.enrollments}
        self.assessments = {
            a.id: a
            for a in snapshot.assessments
            if a.issued_at <= as_of
            and (
                a.planned_issue_week is None
                or self.week_at(a.offering_id, as_of) >= a.planned_issue_week.value
            )
        }
        self.works = {w.id: w for w in snapshot.works if w.assessment_id in self.assessments}
        self.by_pair = {(w.student_id, w.assessment_id): w for w in self.works.values()}
        self.attempts = {
            a.id: a
            for a in snapshot.attempts
            if a.student_work_id in self.works and a.occurred_at <= as_of
        }
        self.histories = defaultdict(list)
        for attempt in self.attempts.values():
            self.histories[attempt.student_work_id].append(attempt)
        for history in self.histories.values():
            history.sort(key=lambda a: a.attempt_no)
        self.items = {i.id: i for i in snapshot.items if i.assessment_id in self.assessments}
        self.results = tuple(
            result
            for result in snapshot.item_results
            if result.attempt_id in self.attempts
            and result.assessment_item_id in self.items
            and result.created_at <= as_of
        )
        # Lesson is a LocalDate fact, with no exact lesson instant or teaching timezone.
        # Its recording time supplies an explicit cutoff; no membership-day inference.
        self.lessons = {
            entry.id: entry
            for entry in snapshot.lessons
            if entry.created_at <= as_of and not entry.cancelled
        }
        self.attendance = tuple(
            a for a in snapshot.attendance if a.lesson_id in self.lessons and a.created_at <= as_of
        )
        self.cases = {q.id: q for q in snapshot.question_cases if q.opened_at <= as_of}
        self.messages = defaultdict(list)
        for message in snapshot.messages:
            if message.question_case_id in self.cases and message.sent_at <= as_of:
                self.messages[message.question_case_id].append(message)
        for messages in self.messages.values():
            messages.sort(key=message_order)

    def offering(self, id):
        if id not in self.offerings:
            raise ApplicationError("not_found")
        return self.offerings[id]

    def roster(self, offering_id):
        self.offering(offering_id)
        return {
            e.student_id
            for e in self.enrollments.values()
            if e.offering_id == offering_id
            and e.deleted_at is None
            and e.enrolled_at <= self.as_of
            and (e.ended_at is None or e.ended_at > self.as_of)
            and e.student_id in self.students
            and self.students[e.student_id].deleted_at is None
            and self.students[e.student_id].active
        }

    def assessments_for(self, offering_id):
        return tuple(a for a in self.assessments.values() if a.offering_id == offering_id)

    def work_facts(self, student_id, assessment):
        work = self.by_pair.get((student_id, assessment.id))
        history = self.histories[work.id] if work else []
        progress = StudentWorkProgress.from_history(work.id, history) if work else None
        presentations = [a for a in history if a.result in PRESENTATIONS]
        # Earliest source timestamp controls timeliness; attempt_no controls progress.
        first_presented_at = min((a.occurred_at for a in presentations), default=None)
        deadline = assessment.due_at
        on_time = (
            deadline is not None
            and first_presented_at is not None
            and first_presented_at <= deadline
        )
        late = (
            deadline is not None
            and first_presented_at is not None
            and first_presented_at > deadline
        )
        overdue = deadline is not None and deadline < self.as_of and first_presented_at is None
        if deadline is None and assessment.planned_due_week is not None:
            due_week = assessment.planned_due_week.value
            actual_week = (
                self.week_at(assessment.offering_id, first_presented_at)
                if first_presented_at
                else None
            )
            on_time = actual_week is not None and actual_week <= due_week
            late = actual_week is not None and actual_week > due_week
            overdue = (
                first_presented_at is None
                and self.week_at(assessment.offering_id, self.as_of) > due_week
            )
        final_source = next((a for a in reversed(history) if a.result in SCORE_EVENTS), None)
        final_score = (
            normalized_score(progress.final_score, final_source.max_score)
            if progress is not None and final_source is not None
            else None
        )
        return {
            "started": bool(presentations),
            "completed": progress is not None and progress.status == StudentWorkStatus.ACCEPTED,
            "status": progress.status if progress else StudentWorkStatus.NOT_STARTED,
            "attempts": progress.attempt_count if progress else 0,
            "first_pass": bool(presentations) and presentations[0].result == AttemptResult.ACCEPTED,
            "on_time": on_time,
            "late": late,
            "overdue": overdue,
            "score": final_score,
        }

    def week_at(self, offering_id, at):
        term = self.terms[self.offerings[offering_id].term_id]
        program = self.programs.get(self.offerings[offering_id].work_program_id)
        calendar_date = at.value.astimezone(
            timezone(
                timedelta(
                    minutes=program.week_utc_offset_minutes
                    if program
                    else term.week_utc_offset_minutes
                )
            )
        ).date()
        first = program.first_week_start if program else term.starts_on
        starts = date(first.year, first.month, first.day)
        return (calendar_date - starts).days // 7 + 1

    def attendance_summary(self, lessons, student_ids, *, expected_pairs=None):
        lessons, student_ids = set(lessons), set(student_ids)
        entries = {
            (a.lesson_id, self.enrollments[a.enrollment_id].student_id): a
            for a in self.attendance
            if a.lesson_id in lessons
            and a.enrollment_id in self.enrollments
            and self.enrollments[a.enrollment_id].student_id in student_ids
        }
        counts = Counter(a.status for a in entries.values())
        if expected_pairs is None:
            expected_pairs = {
                (lesson_id, student_id) for lesson_id in lessons for student_id in student_ids
            }
        present, absent, late = (
            counts[s]
            for s in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LATE)
        )
        return AttendanceSummary(
            len(lessons),
            present,
            absent,
            late,
            counts[AttendanceStatus.EXCUSED],
            counts[AttendanceStatus.UNKNOWN],
            len(expected_pairs - entries.keys()),
            _ratio(present + late, present + absent + late),
        )

    def cases_for(self, *, offering_id=None, student_id=None):
        return tuple(
            q
            for q in self.cases.values()
            if (offering_id is None or q.course_offering_id == offering_id)
            and (student_id is None or q.student_id == student_id)
        )

    def state(self, case):
        # A currently closed case is not closed before its recorded close instant.
        value = (
            replace(case, closed_at=None)
            if case.closed_at and case.closed_at > self.as_of
            else case
        )
        return communication_state(value, self.messages[case.id])

    def question_summary(self, cases):
        cases = tuple(cases)
        ids = {q.id for q in cases}
        states = Counter(self.state(q) for q in cases)
        messages = [m for q in cases for m in self.messages[q.id]]
        durations, unanswered, ambiguous = [], 0, 0
        for case in cases:
            pending = []
            # One response episode starts at the first consecutive student message.
            # A teacher message ends the episode, even if its timestamp is ambiguous.
            for _, batch in groupby(self.messages[case.id], key=lambda message: message.sent_at):
                batch = tuple(batch)
                roles = {message.author_role for message in batch}
                if roles == {AuthorRole.STUDENT, AuthorRole.TEACHER}:
                    # Equal sent_at has no real ordering; metadata/UUID cannot resolve it.
                    ambiguous += 1
                    pending = []
                elif roles == {AuthorRole.STUDENT}:
                    pending.extend(batch)
                elif pending:
                    durations.append(
                        (batch[0].sent_at.value - pending[0].sent_at.value).total_seconds()
                    )
                    pending = []
            unanswered += bool(pending)
        return QuestionAnalyticsSummary(
            len(cases),
            len(cases) - states[CommunicationState.CLOSED],
            states[CommunicationState.WAITING],
            sum(m.author_role == AuthorRole.STUDENT for m in messages),
            sum(m.author_role == AuthorRole.TEACHER for m in messages),
            len(durations),
            unanswered,
            ambiguous,
            _mean(durations),
            median(durations) if durations else None,
            len(
                {
                    link.question_case_id
                    for link in self.data.question_case_assessments
                    if link.question_case_id in ids
                }
            ),
            len(
                {
                    link.question_case_id
                    for link in self.data.question_case_topics
                    if link.question_case_id in ids
                }
            ),
            len(
                {
                    link.question_case_id
                    for link in self.data.question_case_skills
                    if link.question_case_id in ids
                }
            ),
        )

    def evidence(
        self, id, *, skill=False, offering_id=None, student_id=None, include_descendants=True
    ):
        catalogue = self.data.skills if skill else self.data.topics
        value = next((t for t in catalogue if t.id == id), None)
        if value is None:
            raise ApplicationError("not_found")
        targets = {id}
        if not skill and include_descendants:
            while True:
                children = {t.id for t in catalogue if t.parent_topic_id in targets}
                if children <= targets:
                    break
                targets |= children
        offering_ids = {
            o.id
            for o in self.offerings.values()
            if o.course_id == value.course_id and (offering_id is None or o.id == offering_id)
        }
        if offering_id is not None and self.offering(offering_id).course_id != value.course_id:
            raise ApplicationError("learning_course_mismatch")
        assessments = {a.id for a in self.assessments.values() if a.offering_id in offering_ids}
        assessment_links = self.data.assessment_skills if skill else self.data.assessment_topics
        item_links = self.data.item_skills if skill else self.data.item_topics
        case_links = self.data.question_case_skills if skill else self.data.question_case_topics
        field = "skill_id" if skill else "topic_id"
        direct_assessments = {
            link.assessment_id
            for link in assessment_links
            if getattr(link, field) in targets and link.assessment_id in assessments
        }
        items = {
            link.assessment_item_id
            for link in item_links
            if getattr(link, field) in targets
            and link.assessment_item_id in self.items
            and self.items[link.assessment_item_id].assessment_id in assessments
        }
        covering_assessments = direct_assessments | {self.items[id].assessment_id for id in items}
        attempts = {
            a.id: a
            for a in self.attempts.values()
            if self.works[a.student_work_id].assessment_id in direct_assessments
            and (student_id is None or self.works[a.student_work_id].student_id == student_id)
        }
        results = {
            r.id: r
            for r in self.results
            if r.assessment_item_id in items
            and (
                student_id is None
                or self.works[self.attempts[r.attempt_id].student_work_id].student_id == student_id
            )
        }
        case_ids = {link.question_case_id for link in case_links if getattr(link, field) in targets}
        cases = {
            q.id: q
            for q in self.cases.values()
            if q.id in case_ids
            and q.course_offering_id in offering_ids
            and (student_id is None or q.student_id == student_id)
        }
        # Skill exposure is not inferred from TopicSkill (OPEN-004).
        lessons = (
            set()
            if skill
            else {
                link.lesson_id
                for link in self.data.lesson_topics
                if link.topic_id in targets
                and link.lesson_id in self.lessons
                and self.lessons[link.lesson_id].course_offering_id in offering_ids
            }
        )
        attendance = {
            a.id: a
            for a in self.attendance
            if a.lesson_id in lessons
            and a.enrollment_id in self.enrollments
            and (student_id is None or self.enrollments[a.enrollment_id].student_id == student_id)
        }
        students = {self.works[a.student_work_id].student_id for a in attempts.values()}
        students |= {
            self.works[self.attempts[r.attempt_id].student_work_id].student_id
            for r in results.values()
        }
        students |= {q.student_id for q in cases.values()}
        students |= {self.enrollments[a.enrollment_id].student_id for a in attendance.values()}
        evidence = {
            (kind, id)
            for kind, values in (
                ("attempt", attempts),
                ("item_result", results),
                ("question_case", cases),
                ("lesson", lessons),
                ("attendance", attendance),
            )
            for id in values
        }
        outcome = Counter(r.outcome for r in results.values())
        scored = [normalized_score(r.score, r.max_score) for r in results.values()]
        scored = [s for s in scored if s is not None]
        evaluated = sum(
            r.score is not None
            or r.outcome in {ItemOutcome.CORRECT, ItemOutcome.PARTIAL, ItemOutcome.INCORRECT}
            for r in results.values()
        )
        attendance_students = (
            {student_id}
            if student_id is not None
            else {self.enrollments[a.enrollment_id].student_id for a in attendance.values()}
        )
        expected_pairs = None
        if student_id is None:
            expected_pairs = {
                (lesson_id, id)
                for lesson_id in lessons
                for id in self.roster(self.lessons[lesson_id].course_offering_id)
            }
            attendance_students |= {id for _, id in expected_pairs}
        common = dict(
            id=value.id,
            title=value.title,
            course_id=value.course_id,
            as_of=self.as_of,
            evidence_count=len(evidence),
            assessment_attempt_count=len(attempts),
            students_with_evidence=len(students),
            item_result_count=len(results),
            correct=outcome[ItemOutcome.CORRECT],
            partial=outcome[ItemOutcome.PARTIAL],
            incorrect=outcome[ItemOutcome.INCORRECT],
            evaluated=evaluated,
            not_evaluated=len(results) - evaluated,
            average_normalized_item_score=_mean(scored),
            question_cases_linked=len(cases),
            questions_by_students_count=len({q.student_id for q in cases.values()}),
            student_message_count=sum(
                message.author_role == AuthorRole.STUDENT
                for id in cases
                for message in self.messages[id]
            ),
            lesson_exposure_count=len(lessons),
            attendance=self.attendance_summary(
                lessons, attendance_students, expected_pairs=expected_pairs
            ),
            evidence_ids=tuple(sorted(evidence)),
        )
        if skill:
            return SkillEvidenceSummary(
                **common,
                assessments_covering_skill=len(covering_assessments),
                assessment_items_covering_skill=len(items),
            )
        return TopicEvidenceSummary(
            **common,
            assessments_covering_topic=len(covering_assessments),
            assessment_items_covering_topic=len(items),
            includes_descendants=include_descendants,
        )

    def student_summary(self, student_id, offering_id, *, evidence=True):
        offering = self.offering(offering_id)
        if student_id not in self.students:
            raise ApplicationError("not_found")
        # Preserve former participation, but never invent assignments outside the
        # context or before the earliest recorded enrollment instant.
        participated = any(
            enrollment.student_id == student_id
            and enrollment.offering_id == offering_id
            and enrollment.enrolled_at <= self.as_of
            for enrollment in self.enrollments.values()
        )
        assessments = self.assessments_for(offering_id) if participated else ()
        facts = [self.work_facts(student_id, a) for a in assessments]
        started = sum(f["started"] for f in facts)
        completed = sum(f["completed"] for f in facts)
        first_pass = sum(f["first_pass"] for f in facts)
        on_time, late = (sum(f[k] for f in facts) for k in ("on_time", "late"))
        scores = [f["score"] for f in facts if f["score"] is not None]
        lessons = {
            lesson.id
            for lesson in self.lessons.values()
            if participated and lesson.course_offering_id == offering_id
        }
        topics = (
            tuple(
                self.evidence(t.id, offering_id=offering_id, student_id=student_id)
                for t in self.data.topics
                if t.course_id == offering.course_id and t.deleted_at is None
            )
            if evidence
            else ()
        )
        skills = (
            tuple(
                self.evidence(t.id, skill=True, offering_id=offering_id, student_id=student_id)
                for t in self.data.skills
                if t.course_id == offering.course_id and t.deleted_at is None
            )
            if evidence
            else ()
        )
        return StudentProgressSummary(
            student_id,
            offering_id,
            self.as_of,
            len(assessments),
            sum(
                (assessment.due_at is not None or assessment.planned_due_week is not None)
                for assessment in assessments
            ),
            started,
            completed,
            _ratio(completed, len(assessments)),
            sum(f["attempts"] for f in facts),
            _ratio(sum(f["attempts"] for f in facts if f["started"]), started),
            first_pass,
            _ratio(first_pass, started),
            completed,
            sum(f["overdue"] for f in facts),
            on_time,
            late,
            _ratio(on_time, on_time + late),
            _mean(scores),
            self.attendance_summary(lessons, {student_id}),
            self.question_summary(self.cases_for(offering_id=offering_id, student_id=student_id)),
            topics,
            skills,
        )

    def group_summary(self, offering_id):
        students = self.roster(offering_id)
        summaries = [self.student_summary(id, offering_id, evidence=False) for id in students]
        distribution = Counter(s.assessments_completed for s in summaries)
        started = sum(s.assessments_started for s in summaries)
        first_pass = sum(s.first_pass_count for s in summaries)
        on_time, late = (
            sum(getattr(s, k) for s in summaries) for k in ("on_time_count", "late_count")
        )
        lessons = {
            lesson.id
            for lesson in self.lessons.values()
            if lesson.course_offering_id == offering_id
        }
        cases = tuple(
            case for case in self.cases_for(offering_id=offering_id) if case.student_id in students
        )
        return GroupAnalyticsSummary(
            offering_id,
            self.as_of,
            len(students),
            len(self.assessments_for(offering_id)),
            sum(
                (assessment.due_at is not None or assessment.planned_due_week is not None)
                for assessment in self.assessments_for(offering_id)
            ),
            started,
            sum(s.assessments_completed for s in summaries),
            tuple(CompletionDistribution(k, v) for k, v in sorted(distribution.items())),
            _mean([s.completion_rate for s in summaries if s.completion_rate is not None]),
            first_pass,
            _ratio(first_pass, started),
            sum(s.attempts_total for s in summaries),
            _ratio(
                sum(
                    (s.average_attempts_per_started_work or 0) * s.assessments_started
                    for s in summaries
                ),
                started,
            ),
            on_time,
            late,
            sum(s.overdue_count for s in summaries),
            _ratio(on_time, on_time + late),
            self.attendance_summary(lessons, students),
            self.question_summary(cases),
            len({q.student_id for q in cases if self.state(q) != CommunicationState.CLOSED}),
            len({q.student_id for q in cases if self.state(q) == CommunicationState.WAITING}),
        )

    def assessment_summary(self, assessment_id):
        assessment = self.assessments.get(assessment_id)
        if assessment is None:
            raise ApplicationError("not_found")
        students = self.roster(assessment.offering_id)
        facts = [self.work_facts(id, assessment) for id in students]
        started = sum(f["started"] for f in facts)
        on_time, late = (sum(f[k] for f in facts) for k in ("on_time", "late"))
        scores = [f["score"] for f in facts if f["score"] is not None]
        items = []
        for item in sorted(
            (i for i in self.items.values() if i.assessment_id == assessment_id),
            key=lambda i: (i.sort_order, i.id),
        ):
            results = [
                r
                for r in self.results
                if r.assessment_item_id == item.id
                and self.works[self.attempts[r.attempt_id].student_work_id].student_id in students
            ]
            outcomes = Counter(r.outcome for r in results)
            evaluated = sum(
                r.score is not None
                or r.outcome in {ItemOutcome.CORRECT, ItemOutcome.PARTIAL, ItemOutcome.INCORRECT}
                for r in results
            )
            item_scores = [normalized_score(r.score, r.max_score) for r in results]
            items.append(
                AssessmentItemAnalytics(
                    item.id,
                    item.title,
                    len(results),
                    outcomes[ItemOutcome.CORRECT],
                    outcomes[ItemOutcome.PARTIAL],
                    outcomes[ItemOutcome.INCORRECT],
                    evaluated,
                    len(results) - evaluated,
                    _mean([s for s in item_scores if s is not None]),
                )
            )
        first_pass = sum(f["first_pass"] for f in facts)
        return AssessmentAnalytics(
            assessment_id,
            assessment.offering_id,
            self.as_of,
            int(assessment.due_at is not None or assessment.planned_due_week is not None),
            len(students),
            started,
            len(students) - started,
            sum(
                f["started"]
                and f["status"]
                not in {StudentWorkStatus.ACCEPTED, StudentWorkStatus.REVISION_REQUIRED}
                for f in facts
            ),
            sum(f["completed"] for f in facts),
            sum(f["status"] == StudentWorkStatus.REVISION_REQUIRED for f in facts),
            sum(f["attempts"] for f in facts),
            _ratio(sum(f["attempts"] for f in facts if f["started"]), started),
            first_pass,
            _ratio(first_pass, started),
            on_time,
            _ratio(on_time, on_time + late),
            late,
            sum(f["overdue"] for f in facts),
            _mean(scores),
            median(scores) if scores else None,
            tuple(items),
        )


class AnalyticsService:
    def student_work_facts(self, student_id, offering_id, *, as_of=None, module_id=None):
        view = self._module_view(offering_id, as_of, module_id)
        self._require(self._r.students, student_id, historical=True)
        facts = []
        for assessment in view.assessments_for(offering_id):
            work = view.by_pair.get((student_id, assessment.id))
            history = view.histories[work.id] if work else ()
            presentations = [a for a in history if a.result in PRESENTATIONS]
            summary = view.work_facts(student_id, assessment)
            relation = (
                "В срок"
                if summary["on_time"]
                else "После срока"
                if summary["late"]
                else "Не сдано в срок"
                if summary["overdue"]
                else "Без срока"
                if assessment.due_at is None and assessment.planned_due_week is None
                else "Ожидается сдача"
            )
            facts.append(
                StudentWorkFacts(
                    assessment,
                    work.id if work else None,
                    summary["status"],
                    summary["attempts"],
                    min((a.occurred_at for a in presentations), default=None),
                    max((a.occurred_at for a in presentations), default=None),
                    max(
                        (a.occurred_at for a in history if a.result == AttemptResult.ACCEPTED),
                        default=None,
                    ),
                    relation,
                )
            )
        return tuple(
            sorted(
                facts,
                key=lambda f: (
                    f.assessment.type.value,
                    f.assessment.number or "",
                    f.assessment.created_at,
                    f.assessment.id,
                ),
            )
        )

    """Mixin using StudiumService's transaction and clock, never writing source facts."""

    def _analytics_snapshot(self):
        with self._transaction() as repositories:
            return _Snapshot(repositories)

    def _analytics_view(self, as_of):
        cutoff = self._clock() if as_of is None else as_of
        if not isinstance(cutoff, UtcInstant):
            raise ValueError("as_of must be an explicit UTC instant")
        return _View(self._analytics_snapshot(), cutoff)

    def _module_view(self, offering_id, as_of, module_id):
        if module_id is None:
            return self._analytics_view(as_of)
        snapshot = self._analytics_snapshot()
        module = self._require(self._r.program_modules, module_id)
        offering = next((o for o in snapshot.offerings if o.id == offering_id), None)
        if offering is None or module.work_program_id != offering.work_program_id:
            raise ApplicationError("learning_course_mismatch")
        links = {
            w.id
            for w in self._r.program_works.for_owner(module.work_program_id)
            if w.module_id == module.id
        }
        snapshot.assessments = tuple(
            a
            for a in snapshot.assessments
            if a.program_work_id in links
            or (
                a.program_work_id is None
                and a.planned_due_week is not None
                and module.start_week <= a.planned_due_week.value <= module.end_week
            )
        )
        snapshot.lessons = tuple(
            lesson
            for lesson in snapshot.lessons
            if lesson.module_id == module.id
            or (
                lesson.planned_week is not None
                and module.start_week <= lesson.planned_week.value <= module.end_week
            )
        )
        calendar = _View(snapshot, as_of or self._clock())
        assessment_ids = {a.id for a in snapshot.assessments}
        linked_cases = {
            link.question_case_id
            for link in snapshot.question_case_assessments
            if link.assessment_id in assessment_ids
        }
        snapshot.question_cases = tuple(
            case
            for case in snapshot.question_cases
            if case.id in linked_cases
            or (
                case.course_offering_id == offering_id
                and module.start_week
                <= calendar.week_at(offering_id, case.opened_at)
                <= module.end_week
            )
        )
        return _View(snapshot, as_of or self._clock())

    def student_progress(self, student_id, offering_id, *, as_of=None, module_id=None):
        return self._module_view(offering_id, as_of, module_id).student_summary(
            student_id, offering_id
        )

    def group_analytics(self, offering_id, *, as_of=None, module_id=None):
        return self._module_view(offering_id, as_of, module_id).group_summary(offering_id)

    def context_evidence(self, offering_id, *, student_id=None, module_id=None, as_of=None):
        view = self._module_view(offering_id, as_of, module_id)
        course_id = view.offering(offering_id).course_id
        return tuple(
            view.evidence(value.id, skill=skill, offering_id=offering_id, student_id=student_id)
            for skill, values in ((False, view.data.topics), (True, view.data.skills))
            for value in values
            if value.course_id == course_id and value.deleted_at is None
        )

    def assessment_analytics(self, assessment_id, *, as_of=None):
        return self._analytics_view(as_of).assessment_summary(assessment_id)

    def topic_evidence(
        self,
        topic_id,
        *,
        offering_id=None,
        student_id=None,
        include_descendants=True,
        as_of=None,
        module_id=None,
    ):
        return self._module_view(offering_id, as_of, module_id).evidence(
            topic_id,
            offering_id=offering_id,
            student_id=student_id,
            include_descendants=include_descendants,
        )

    def skill_evidence(
        self, skill_id, *, offering_id=None, student_id=None, as_of=None, module_id=None
    ):
        return self._module_view(offering_id, as_of, module_id).evidence(
            skill_id, skill=True, offering_id=offering_id, student_id=student_id
        )

    def question_analytics(self, *, offering_id=None, student_id=None, as_of=None):
        view = self._analytics_view(as_of)
        if offering_id is not None:
            view.offering(offering_id)
        return view.question_summary(view.cases_for(offering_id=offering_id, student_id=student_id))

    def analytics_timeline(self, offering_id, cutoffs, *, student_id=None):
        """Load once for multiple cutoffs; current mutable facts are not audit versions."""
        cutoffs = tuple(cutoffs)
        if any(not isinstance(at, UtcInstant) for at in cutoffs):
            raise ValueError("cutoffs must contain explicit UTC instants")
        snapshot = self._analytics_snapshot()
        points = []
        for cutoff in sorted(set(cutoffs)):
            view = _View(snapshot, cutoff)
            summary = (
                view.group_summary(offering_id)
                if student_id is None
                else view.student_summary(student_id, offering_id, evidence=False)
            )
            points.append(
                AnalyticsTimePoint(
                    cutoff,
                    summary.assessments_total,
                    summary.assessments_started,
                    summary.assessments_completed,
                    summary.average_completion_rate
                    if student_id is None
                    else summary.completion_rate,
                    summary.attempts_total,
                    summary.first_pass_rate,
                    summary.on_time_rate,
                    summary.attendance.attendance_rate,
                    summary.questions.question_cases_count,
                )
            )
        return tuple(points)
