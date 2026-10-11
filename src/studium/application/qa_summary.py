"""First-screen summary of distinct works and factual attendance."""

from collections import defaultdict
from typing import NamedTuple

from studium.domain import qa as q
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, StudentWorkStatus

SUBSTANTIVE = {
    AttemptResult.PRESENTED,
    AttemptResult.NEEDS_REVISION,
    AttemptResult.ACCEPTED,
    AttemptResult.SCORED,
    AttemptResult.REJECTED,
}


class PackageWorkSummary(NamedTuple):
    offering_id: object
    caption: str
    kind: AssessmentType
    completed: int
    accepted: int
    total: int
    not_issued: int
    cancelled: int
    revision_required: int
    awaiting_review: int
    not_submitted_in_time: int
    scores: tuple


class PackageAttendance(NamedTuple):
    attended: int
    denominator: int
    lessons: int
    present: int
    absent: int
    late: int
    excused: int
    unknown: int
    unmarked: int

    @property
    def rate(self):
        return self.attended / self.denominator if self.denominator else None


class QASummary:
    def student_package_summary(self, student_id):
        with self._transaction() as r:
            memberships = [
                en for en in r.enrollments.list(include_deleted=True) if en.student_id == student_id
            ]
            offering_ids = {en.offering_id for en in memberships}
            offerings = [o for o in r.offerings.list(include_deleted=True) if o.id in offering_ids]
            courses = {c.id: c for c in r.courses.list(include_deleted=True)}
            groups = {g.id: g for g in r.groups.list(include_deleted=True)}
            terms = {t.id: t for t in r.terms.list(include_deleted=True)}
            plans = {
                p.id: p
                for p in r.semester_plans.list(include_deleted=True)
                if p.offering_id in offering_ids
            }
            planned = {
                w.id: w
                for w in r.planned_works.list(include_deleted=True)
                if w.semester_plan_id in plans
            }
            issued = {
                i.assessment_id: planned[i.planned_work_id]
                for i in r.issued_works.list(include_deleted=True)
                if i.planned_work_id in planned
            }
            issued_ids = {w.id for w in issued.values()}
            works = {
                w.assessment_id: w
                for w in r.works.list(include_deleted=True)
                if w.student_id == student_id
            }
            histories = defaultdict(list)
            for attempt in r.attempts.list():
                histories[attempt.student_work_id].append(attempt)
            submissions = r.submissions.list()
            reviews = r.reviews.list()
            by_attempt = {s.attempt_id: s for s in submissions}
            substantive_reviews = {
                v.submission_id for v in reviews if v.result != AttemptResult.COMMENT_ONLY
            }
            all_assessments = r.assessments.list(include_deleted=True)
            rows = []
            now = self._clock()
            for offering in offerings:
                caption = f"{terms[offering.term_id].name} · {groups[offering.group_id].number} · {courses[offering.course_id].name}"
                for kind in (
                    AssessmentType.HOMEWORK,
                    AssessmentType.CONTROL_WORK,
                    AssessmentType.EXAM,
                ):
                    assessments = [
                        a
                        for a in all_assessments
                        if a.offering_id == offering.id and a.type == kind
                    ]
                    active = [
                        a for a in assessments if not (issued.get(a.id) and issued[a.id].cancelled)
                    ]
                    completed = accepted = revision_required = awaiting = overdue = 0
                    scores = []
                    for assessment in active:
                        work = works.get(assessment.id)
                        history = histories[work.id] if work else []
                        actual = [a for a in history if a.result in SUBSTANTIVE]
                        completed += bool(actual)
                        result = q.result_from_events(history, submissions, reviews)
                        accepted += result.status == StudentWorkStatus.ACCEPTED
                        revision_required += result.status == StudentWorkStatus.REVISION_REQUIRED
                        latest = max(actual, key=lambda a: a.attempt_no, default=None)
                        if latest:
                            submission = by_attempt.get(latest.id)
                            awaiting += (
                                submission.id not in substantive_reviews
                                if submission
                                else latest.result == AttemptResult.PRESENTED
                            )
                        planned_work = issued.get(assessment.id)
                        deadline, exclusive = (
                            q.planned_deadline(planned_work, plans[planned_work.semester_plan_id])
                            if planned_work
                            else (assessment.due_at, False)
                        )
                        if deadline and (now >= deadline if exclusive else now > deadline):
                            first = min((a.occurred_at for a in actual), default=None)
                            overdue += first is None or (
                                first >= deadline if exclusive else first > deadline
                            )
                        if result.score is not None:
                            scores.append(
                                (
                                    assessment.id,
                                    assessment.title,
                                    q.score_text(result.score)
                                    if result.exact
                                    else repr(result.score),
                                )
                            )
                    not_issued = sum(
                        w.type == kind
                        and plans[w.semester_plan_id].offering_id == offering.id
                        and w.id not in issued_ids
                        and not w.cancelled
                        and w.deleted_at is None
                        for w in planned.values()
                    )
                    cancelled = sum(
                        w.type == kind
                        and plans[w.semester_plan_id].offering_id == offering.id
                        and w.cancelled
                        for w in planned.values()
                    )
                    rows.append(
                        PackageWorkSummary(
                            offering.id,
                            caption,
                            kind,
                            completed,
                            accepted,
                            len(active),
                            not_issued,
                            cancelled,
                            revision_required,
                            awaiting,
                            overdue,
                            tuple(scores),
                        )
                    )
            lesson_ids = {
                v.id
                for v in r.lessons.list()
                if v.course_offering_id in offering_ids and not v.cancelled
            }
            enrollment_ids = {en.id for en in memberships}
            attendance = [
                v
                for v in r.attendance.list()
                if v.enrollment_id in enrollment_ids and v.lesson_id in lesson_ids
            ]
            counts = {
                status: sum(v.status == status for v in attendance) for status in AttendanceStatus
            }
            denominator = sum(
                counts[v]
                for v in (AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.ABSENT)
            )
            return tuple(rows), PackageAttendance(
                counts[AttendanceStatus.PRESENT] + counts[AttendanceStatus.LATE],
                denominator,
                len(lesson_ids),
                counts[AttendanceStatus.PRESENT],
                counts[AttendanceStatus.ABSENT],
                counts[AttendanceStatus.LATE],
                counts[AttendanceStatus.EXCUSED],
                counts[AttendanceStatus.UNKNOWN],
                len(lesson_ids - {v.lesson_id for v in attendance}),
            )
