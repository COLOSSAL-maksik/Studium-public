"""PR #3 regressions use real synthetic persistence and original UUIDs."""

import json
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta

import pytest

from studium.application.errors import ApplicationError
from studium.domain.content import MaterialFileRole
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, EnrollmentStatus
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import LocalDate, UtcInstant
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow


def content(definition, *, start=1, semester=1):
    return {
        "modules": [
            {
                "key": "m",
                "title": "Module",
                "course_semester": semester,
                "start_week": start,
                "end_week": start + 2,
            }
        ],
        "works": [
            {"definition_id": str(definition.id), "module_key": "m", "course_semester": semester}
        ],
    }


def versioned(workflow):
    s, _, course, _, offering, student, _, _ = workflow
    problem = s.create_material(
        "problems", course_id=course.id, title="Original", statement="Original statement"
    )
    topic = s.create_topic(course.id, "Original topic")
    s.set_content_links("problem_topics", problem.id, [topic.id])
    definition = s.create_work_definition(course.id, "H", AssessmentType.HOMEWORK)
    s.set_content_links("definition_problems", definition.id, [problem.id])
    version = s.create_course_program(course.id, "Program", content=content(definition))
    s.create_semester_plan(offering.id, version_id=version.id, course_semester=1)
    return s, offering, student, problem, topic, definition, version


def test_first_late_submission_without_precreated_work(workflow):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    ended = s._r.enrollments.find_by_id(enrollment.id)
    submission = s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    work = s.find_student_work(student.id, assessment.id)
    assert s._r.attempts.history(work.id)[0].id == submission.attempt_id
    assert s._r.enrollments.find_by_id(enrollment.id) == ended


def test_pinned_problem_text_and_classification_are_frozen(workflow):
    s, offering, _, problem, topic, _, _ = versioned(workflow)
    changed_topic = s.create_topic(problem.course_id, "Changed topic")
    s.update_material("problems", problem, title="Changed", statement="Changed statement")
    s.set_content_links("problem_topics", problem.id, [changed_topic.id])
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    item = s._r.items.for_assessment(assessment.id)[0]
    assert (item.title, item.description) == ("Original", "Original statement")
    assert [v.topic_id for v in s._r.item_topics.for_owner(item.id)] == [topic.id]


def test_nonempty_plan_reassignment_previews_real_conflict(workflow):
    s, offering, _, _, _, definition, version = versioned(workflow)
    s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    second = s.new_program_version(
        version, content=content(definition, semester=2), direction_ids=[]
    )
    before = s.semester_plan(offering.id)
    preview = s.preview_plan_content(
        offering.id, second.id, 2, expected_revision=before.plan.revision
    )
    assert preview.conflicts
    assert s.semester_plan(offering.id) == before
    with pytest.raises(ValueError):
        s.apply_plan_content(preview, confirmed=True)
    assert s.semester_plan(offering.id) == before


def test_summary_does_not_call_scored_submission_waiting(workflow):
    s, offering, student, *_ = versioned(workflow)
    work = s.semester_plan(offering.id).works[0]
    assessment = s.issue_planned_work(work.id)
    s.change_scoring_rule(assessment.id, "0", "30")
    submission = s.register_student_submission(
        student.id, assessment.id, UtcInstant(UtcInstant.now().value - timedelta(days=1))
    )
    s.review_submission(submission.id, AttemptResult.SCORED, score="24")
    rows, _ = s.student_package_summary(student.id)
    row = next(r for r in rows if r[0] == offering.id and r[2] == AssessmentType.HOMEWORK)
    assert row.awaiting_review == 0
    assert row.accepted == 0 and row.completed == 1


@pytest.mark.parametrize("status", [EnrollmentStatus.WITHDRAWN, EnrollmentStatus.COMPLETED])
@pytest.mark.parametrize("precreated", [False, True])
def test_late_submission_in_t2_keeps_original_membership(workflow, status, precreated):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    work = s.get_or_create_work(student.id, assessment.id) if precreated else None
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s._update(s._r.enrollments, enrollment, status=status, ended_at=UtcInstant.now())
    ended = s._r.enrollments.find_by_id(enrollment.id)
    t2 = s.create_term("Synthetic T2", LocalDate(2027, 2, 1), LocalDate(2027, 6, 30))
    second = s.create_offering(t2.id, offering.course_id, offering.group_id)
    s.enroll_student(second.id, student.id)
    s.select_term(t2.id)
    s._clock = lambda: UtcInstant(ended.ended_at.value + timedelta(days=400))
    first = s.register_student_submission(student.id, assessment.id, s._clock())
    again = s.register_student_submission(student.id, assessment.id, s._clock())
    saved = s.find_student_work(student.id, assessment.id)
    assert saved.student_id == student.id and saved.assessment_id == assessment.id
    if work:
        assert saved == work
    assert [a.attempt_no for a in s._r.attempts.history(saved.id)] == [1, 2]
    assert first.attempt_id != again.attempt_id
    assert s._r.enrollments.find_by_id(enrollment.id) == ended
    assert s._r.assessments.find_by_id(assessment.id) == assessment


@pytest.mark.parametrize("deleted", ["assessment", "offering", "enrollment", "student", "term"])
def test_first_late_submission_requires_live_original_context(workflow, deleted):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    targets = {
        "assessment": (s._r.assessments, assessment),
        "offering": (s._r.offerings, offering),
        "enrollment": (s._r.enrollments, s._r.enrollments.find_by_id(enrollment.id)),
        "student": (s._r.students, student),
        "term": (s._r.terms, s._r.terms.find_by_id(offering.term_id)),
    }
    repo, value = targets[deleted]
    repo.soft_delete(value.id, expected_revision=value.revision, at=UtcInstant.now())
    with pytest.raises((RepositoryError, ApplicationError)):
        s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    assert s.find_student_work(student.id, assessment.id) is None
    assert not s._r.late_work_authorizations.list()


def test_first_late_archived_term_allowed_but_foreign_offering_rejected(workflow):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    s.withdraw_student(s.list_students_for_offering(offering.id)[0].enrollment)
    term = s._r.terms.find_by_id(offering.term_id)
    s._update(s._r.terms, term, archived=True)
    foreign = s.create_offering(offering.term_id, offering.course_id, s.create_group("Foreign").id)
    wrong = s.create_assessment(foreign.id, "Foreign", AssessmentType.HOMEWORK)
    with pytest.raises(ApplicationError):
        s.register_student_submission(student.id, wrong.id, UtcInstant.now())
    s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    assert s.find_student_work(student.id, wrong.id) is None


def fail_transaction(service, monkeypatch):
    original = service._transaction

    @contextmanager
    def failure():
        with original() as repositories:
            yield repositories
            raise RuntimeError("synthetic late failure")

    monkeypatch.setattr(service, "_transaction", failure)


def test_first_late_files_and_authorization_roll_back_together(workflow, tmp_path, monkeypatch):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    s.withdraw_student(s.list_students_for_offering(offering.id)[0].enrollment)
    source = tmp_path / "synthetic.pdf"
    source.write_bytes(b"late synthetic bytes")
    original = s._transaction
    calls = 0

    @contextmanager
    def failure():
        nonlocal calls
        calls += 1
        with original() as r:
            yield r
            if calls == 2:
                raise RuntimeError("synthetic late failure")

    monkeypatch.setattr(s, "_transaction", failure)
    with pytest.raises(RuntimeError):
        s.register_student_submission(student.id, assessment.id, UtcInstant.now(), paths=[source])
    assert s.find_student_work(student.id, assessment.id) is None
    assert not s._r.late_work_authorizations.list() and not s._r.file_assets.list()
    assert not [
        p
        for p in s._file_storage.paths.files_dir.rglob("*")
        if p.is_file() and p != s._file_storage.paths.files_dir / ".imports" / "lock"
    ]
    assert not s._r.attempt_attachments.list()


def test_family_parameters_source_revisions_archived_source_and_v2(workflow):
    s, _, course, _, offering, student, _, _ = workflow
    family = s.create_material(
        "problems", course_id=course.id, title="Family", statement="Shared A", is_family=True
    )
    variant = s.create_material(
        "problems",
        course_id=course.id,
        title="Variant",
        family_id=family.id,
        variant_code="7",
        parameters="x=1",
        correct_answer="secret A",
    )
    definition = s.create_work_definition(course.id, "Control", AssessmentType.CONTROL_WORK)
    s.set_content_links("definition_problems", definition.id, [variant.id])
    v1 = s.create_course_program(course.id, "Program", content=content(definition))
    s.create_semester_plan(offering.id, version_id=v1.id, course_semester=1)
    s.update_material("problems", family, title="New family", statement="Shared B")
    variant = s.update_material("problems", variant, parameters="x=2", correct_answer="secret B")
    v2 = s.new_program_version(v1, content=content(definition), direction_ids=[])
    s.archive_material("problems", variant)
    a1 = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    item = s._r.items.for_assessment(a1.id)[0]
    assignment = s.assign_student_problem(student.id, item.id, variant.id)
    assert (item.title, item.description, assignment.source_revision) == (
        "Family · вариант 7",
        "Shared A\nПараметры: x=1",
        1,
    )
    assert json.loads(assignment.teacher_snapshot_json)["answer"] == "secret A"
    assert json.loads(assignment.teacher_snapshot_json)["family_snapshot"]["revision"] == 1
    second = s.create_offering(
        offering.term_id,
        course.id,
        s.create_group("V2").id,
        course_version_id=v2.id,
        course_semester=1,
    )
    a2 = s.issue_planned_work(s.semester_plan(second.id).works[0].id)
    assert s._r.items.for_assessment(a2.id)[0].description == "Shared B\nПараметры: x=2"


def test_program_files_and_teacher_content_stay_frozen(workflow, tmp_path):
    s, _, course, _, offering, student, _, _ = workflow
    problem = s.create_material(
        "problems", course_id=course.id, title="P", statement="Public", correct_answer="private"
    )
    files = []
    for role in (MaterialFileRole.STATEMENT, MaterialFileRole.SOLUTION):
        path = tmp_path / (role.value + ".txt")
        path.write_text("synthetic " + role.value)
        files.append(s.import_file_for_material("problems", problem.id, path, role=role))
    definition = s.create_work_definition(course.id, "H", AssessmentType.HOMEWORK)
    attachment = s.import_file_for_material("homework", definition.id, tmp_path / "STATEMENT.txt")
    s.set_content_links("definition_problems", definition.id, [problem.id])
    version = s.create_course_program(course.id, "Program", content=content(definition))
    s.create_semester_plan(offering.id, version_id=version.id, course_semester=1)
    s._r.homework_attachments.soft_delete(
        attachment.id, expected_revision=attachment.revision, at=UtcInstant.now()
    )
    for link in files:
        s._r.problem_attachments.soft_delete(
            link.id, expected_revision=link.revision, at=UtcInstant.now()
        )
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    assert [v.asset.id for v in s.assessment_shared_files(assessment)] == [attachment.file_asset_id]
    item = s._r.items.for_assessment(assessment.id)[0]
    assignment = s.assign_student_problem(student.id, item.id, problem.id)
    assert {v.file_asset_id for v in s._r.student_problem_files.for_owner(assignment.id)} == {
        v.file_asset_id for v in files
    }
    # The public DTO is a whitelist; teacher snapshots/files cannot be exported by it.
    public = s.student_assignment_content(assignment.id)
    assert "private" not in repr(public) and files[1].file_asset_id not in public.file_asset_ids


def test_reassignment_retains_issued_bindings_and_pins_unissued(workflow):
    s, offering, student, problem, _, definition, v1 = versioned(workflow)
    snapshot = s.semester_plan(offering.id)
    issued = s.issue_planned_work(snapshot.works[0].id)
    sub = s.register_student_submission(student.id, issued.id, UtcInstant.now())
    s.review_submission(sub.id, AttemptResult.ACCEPTED)
    saved_work = s.find_student_work(student.id, issued.id)
    s.set_required_works(
        snapshot.modules[0].id, student.id, [saved_work.id], reason="Original requirement"
    )
    pending = s.add_planned_work(
        offering.id, "Pinned pending", AssessmentType.HOMEWORK, definition_id=definition.id
    )
    s.update_material("problems", problem, title="V2", statement="New content")
    v2 = s.new_program_version(v1, content=content(definition, start=5), direction_ids=[])
    before = s.semester_plan(offering.id)
    preview = s.preview_plan_content(offering.id, v2.id, 1, expected_revision=before.plan.revision)
    assert not preview.conflicts and preview.facts == (1, 1, 1, 1, 1)
    assert s.semester_plan(offering.id) == before
    with pytest.raises(ValueError, match="Подтвердите"):
        s.apply_plan_content(preview)
    s.apply_plan_content(preview, confirmed=True)
    sources = s.plan_content_bindings(offering.id)
    assert (
        next(v for v in sources if v.planned_work_id == before.works[0].id).program_version_id
        == v1.id
    )
    assert len(s.semester_plan(offering.id).works) == 3
    pending_assessment = s.issue_planned_work(pending.id)
    assert s._r.items.for_assessment(pending_assessment.id)[0].description == "Original statement"
    assert s.student_module_results(student.id)[0].state == "closed"
    assert s._r.reviews.for_owner(sub.id)[0].result == AttemptResult.ACCEPTED


def test_replace_unissued_can_change_semester_and_other_group_is_independent(workflow):
    s, offering, _, _, _, definition, v1 = versioned(workflow)
    second = s.create_offering(
        offering.term_id,
        offering.course_id,
        s.create_group("Independent").id,
        course_version_id=v1.id,
        course_semester=1,
    )
    other_before = s.semester_plan(second.id)
    before = s.semester_plan(offering.id)
    v2 = s.new_program_version(v1, content=content(definition, semester=2), direction_ids=[])
    preview = s.preview_plan_content(
        offering.id, v2.id, 2, expected_revision=before.plan.revision, mode="replace_unissued"
    )
    assert not preview.conflicts and preview.retired_works == before.works
    s.apply_plan_content(preview, confirmed=True)
    current = s.semester_plan(offering.id)
    assert current.plan.course_semester == 2 and len(current.works) == 1
    assert s._r.planned_works.find_by_id(before.works[0].id, include_deleted=True).deleted_at
    assert s.semester_plan(second.id) == other_before
    assert (
        next(
            v
            for v in s.plan_content_bindings(offering.id)
            if v.planned_work_id == before.works[0].id
        ).program_version_id
        == v1.id
    )


def test_reassignment_new_fact_stale_and_late_failure_leave_plan_unchanged(workflow, monkeypatch):
    s, offering, student, _, _, definition, v1 = versioned(workflow)
    issued = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    v2 = s.new_program_version(v1, content=content(definition, start=5), direction_ids=[])
    before = s.semester_plan(offering.id)
    preview = s.preview_plan_content(offering.id, v2.id, 1, expected_revision=before.plan.revision)
    s.register_student_submission(student.id, issued.id, UtcInstant.now())
    with pytest.raises(RepositoryError):
        s.apply_plan_content(preview, confirmed=True)
    assert s.semester_plan(offering.id) == before
    preview = s.preview_plan_content(offering.id, v2.id, 1, expected_revision=before.plan.revision)
    original = s._transaction
    fail_transaction(s, monkeypatch)
    with pytest.raises(RuntimeError, match="late failure"):
        s.apply_plan_content(preview, confirmed=True)
    monkeypatch.setattr(s, "_transaction", original)
    assert s.semester_plan(offering.id) == before


@pytest.mark.parametrize(
    "kind,exclusive", [("DATE_EXCLUSIVE", True), ("EXACT_INCLUSIVE", False), ("WEEK_ONLY", True)]
)
def test_summary_current_deadline_boundary_and_distinct_reviews(workflow, kind, exclusive):
    s, offering, student, *_ = versioned(workflow)
    snapshot = s.semester_plan(offering.id)
    work = snapshot.works[0]
    now = UtcInstant.now()
    if kind == "DATE_EXCLUSIVE":
        from studium.domain.qa import day_boundary

        values = {"deadline_kind": kind, "due_date": LocalDate(2026, 10, 1)}
        boundary = day_boundary(values["due_date"], snapshot.plan.week_utc_offset_minutes)
    elif kind == "WEEK_ONLY":
        from studium.domain.qa import planned_deadline

        values = {"deadline_kind": kind, "due_week": 1, "due_date": LocalDate(2099, 1, 1)}
        boundary, _ = planned_deadline(replace(work, **values), snapshot.plan)
    else:
        values = {"deadline_kind": kind, "exact_due_at": now}
        boundary = now
    s.apply_plan_change(
        s.preview_plan_change(offering.id, work_changes=((work.id, work.revision, values),)),
        confirmed=True,
    )
    assessment = s.issue_planned_work(work.id)
    s._clock = lambda: boundary
    rows, _ = s.student_package_summary(student.id)
    row = next(r for r in rows if r.kind == AssessmentType.HOMEWORK)
    assert row.not_submitted_in_time == int(exclusive)
    s._clock = lambda: UtcInstant(boundary.value + timedelta(seconds=1))
    sub = s.register_student_submission(student.id, assessment.id, boundary)
    s.review_submission(sub.id, AttemptResult.COMMENT_ONLY)
    assert (
        next(
            r for r in s.student_package_summary(student.id)[0] if r.kind == AssessmentType.HOMEWORK
        ).awaiting_review
        == 1
    )
    s.review_submission(sub.id, AttemptResult.NEEDS_REVISION)
    s.review_submission(sub.id, AttemptResult.ACCEPTED)
    row = next(
        r for r in s.student_package_summary(student.id)[0] if r.kind == AssessmentType.HOMEWORK
    )
    assert (row.completed, row.accepted, row.awaiting_review, row.revision_required) == (1, 1, 0, 0)
    assert row.not_submitted_in_time == int(exclusive)


def test_summary_attendance_cancelled_unknown_and_exact_scores(workflow):
    s, offering, student, *_ = versioned(workflow)
    en = s.list_students_for_offering(offering.id)[0].enrollment
    for index, status in enumerate(AttendanceStatus):
        lesson = s.create_lesson(offering.id, LocalDate(2026, 10, index + 1), title=status.value)
        s.mark_attendance(lesson.id, en.id, status)
    cancelled = s.create_lesson(offering.id, LocalDate(2026, 10, 6), title="Cancelled")
    s.mark_attendance(cancelled.id, en.id, AttendanceStatus.ABSENT)
    s.update_lesson(cancelled, cancelled=True)
    s.create_lesson(offering.id, LocalDate(2026, 10, 7), title="Unmarked")
    work = s.semester_plan(offering.id).works[0]
    assessment = s.issue_planned_work(work.id)
    s.set_fractional_scores_enabled(True)
    s.change_scoring_rule(assessment.id, "0", "30")
    sub = s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    s.review_submission(sub.id, AttemptResult.SCORED, score="24,75")
    rows, attendance = s.student_package_summary(student.id)
    row = next(r for r in rows if r.kind == AssessmentType.HOMEWORK)
    assert row.scores == ((assessment.id, assessment.title, "24,75"),)
    assert attendance == (2, 3, 6, 1, 1, 1, 1, 1, 1)
    assert attendance.rate == 2 / 3


def test_sources_and_issued_assignments_survive_backup_restore(workflow, tmp_path):
    from studium.application.backup import BackupControl
    from studium.composition import create_runtime
    from studium.infrastructure.backup import LocalBackup
    from studium.infrastructure.user_data import AppPaths

    s, offering, student, problem, _, _, _ = versioned(workflow)
    before = s.plan_content_bindings(offering.id)
    s.update_material("problems", problem, title="Mutable", statement="Changed")
    backend = LocalBackup(AppPaths(s._file_storage.root))
    archive = tmp_path.parent / (tmp_path.name + ".zip")
    backend.create(archive, BackupControl())
    destination = tmp_path.parent / (tmp_path.name + "-restored")
    backend.restore(archive, destination, backend.verify(archive, BackupControl()), BackupControl())
    restored = create_runtime(destination)
    try:
        rs = restored.service
        assert rs.plan_content_bindings(offering.id) == before
        assessment = rs.issue_planned_work(rs.semester_plan(offering.id).works[0].id)
        item = rs._r.items.for_assessment(assessment.id)[0]
        assignment = rs.assign_student_problem(student.id, item.id, problem.id)
        assert assignment.statement_snapshot == "Original statement"
    finally:
        restored.close()
    reopened = create_runtime(destination)
    try:
        assert (
            reopened.service.student_assignment_content(assignment.id).statement
            == "Original statement"
        )
        assert reopened.service.plan_content_bindings(offering.id) == before
    finally:
        reopened.close()


def test_late_repository_write_cannot_bypass_membership_or_issue_date(workflow):
    from studium.domain.entities import StudentWork

    s, offering, student, *_ = versioned(workflow)
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    # A newly issued work after participation ended does not belong to this student.
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    with pytest.raises(RepositoryError):
        s._r.works.insert(
            StudentWork(metadata=s._meta(), student_id=student.id, assessment_id=assessment.id)
        )
    with pytest.raises(RepositoryError):
        s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    assert not s._r.late_work_authorizations.list()


def test_unknown_legacy_dates_and_real_score_remain_visible(workflow):
    s, _, _, _, offering, student, assessment, work = workflow
    s.add_attempt(
        work.id, UtcInstant.now(), AttemptResult.SCORED, score=24.123456789, max_score=30.987654321
    )
    rows, _ = s.student_package_summary(student.id)
    row = next(
        r for r in rows if r.offering_id == offering.id and r.kind == AssessmentType.HOMEWORK
    )
    assert row.scores == ((assessment.id, assessment.title, "24.123456789"),)
    assert row.awaiting_review == row.accepted == row.not_submitted_in_time == 0


def test_first_late_deleted_context_requires_explicit_restore_without_reenrollment(workflow):
    s, offering, student, *_ = versioned(workflow)
    assessment = s.issue_planned_work(s.semester_plan(offering.id).works[0].id)
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    ended = s._r.enrollments.find_by_id(enrollment.id)
    s._r.assessments.soft_delete(
        assessment.id, expected_revision=assessment.revision, at=UtcInstant.now()
    )
    with pytest.raises(ValueError):
        s.restore_student_submission_context(
            student.id, assessment.id, reason="Missing confirmation"
        )
    assert s.find_student_work(student.id, assessment.id) is None
    work = s.restore_student_submission_context(
        student.id, assessment.id, confirmed=True, reason="Original debt"
    )
    assert not s._r.attempts.history(work.id)
    assert json.loads(s._r.debt_restorations.for_owner(work.id)[0].before_json)["work_absent"]
    s.register_student_submission(student.id, assessment.id, UtcInstant.now())
    assert s._r.enrollments.find_by_id(enrollment.id) == ended
    assert s._r.assessments.find_by_id(assessment.id).offering_id == offering.id


def test_late_capture_of_original_actual_issue_uses_event_time(workflow):
    s, offering, student, *_ = versioned(workflow)
    original_issue = UtcInstant.now()
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    ended = s._r.enrollments.find_by_id(enrollment.id)
    s._clock = lambda: UtcInstant(ended.ended_at.value + timedelta(days=30))
    assessment = s.issue_planned_work(
        s.semester_plan(offering.id).works[0].id, actual_issued_at=original_issue
    )
    assert assessment.created_at > ended.ended_at
    s.register_student_submission(student.id, assessment.id, s._clock())
    assert s._r.enrollments.find_by_id(enrollment.id) == ended
