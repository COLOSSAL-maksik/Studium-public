"""Synthetic contract tests for the integrated QA package, including real persistence."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import text

from studium.domain import qa as q
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind, StudentWorkStatus
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import LocalDate, UtcInstant
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow


@pytest.fixture
def planned(workflow):
    s, _, _, _, offering, student, _, _ = workflow
    s.create_semester_plan(offering.id, weeks=17)
    module = s.add_plan_module(offering.id, "M1", 1, 6)
    work = s.add_planned_work(
        offering.id,
        "H1",
        AssessmentType.HOMEWORK,
        module_id=module.id,
        due_date=LocalDate(2026, 10, 10),
        minimum="18",
        maximum="30",
    )
    assessment = s.issue_planned_work(work.id)
    student_work = s.get_or_create_work(student.id, assessment.id)
    return s, offering, student, module, work, assessment, student_work


def test_new_review_revision_reject_atomic_accept_and_original_attempt(planned):
    s, _, _, _, _, _, work = planned
    submission = s.register_submission(
        work.id, UtcInstant(UtcInstant.now().value - timedelta(days=2))
    )
    first = s.review_submission(submission.id, AttemptResult.NEEDS_REVISION)
    with pytest.raises(ValueError, match="ACCEPTED"):
        s.review_submission(
            submission.id, AttemptResult.SCORED, score="24", grade_kind=GradeKind.NUMERIC
        )
    assert s._r.reviews.for_owner(submission.id) == [first]
    assert not s._r.review_grades.list()
    second = s.review_submission(
        submission.id, AttemptResult.ACCEPTED, score="24", grade_kind=GradeKind.NUMERIC
    )
    assert second.review_seq == 2
    assert len(s._r.attempts.history(work.id)) == 1
    assert s.work_result(work.id) == q.WorkResult(
        StudentWorkStatus.ACCEPTED, 2400, 3000, True, second.id
    )


def test_fractional_bounds_snapshot_allowed_off_but_new_fractional_score_rejected(planned):
    s, _, _, _, _, assessment, work = planned
    s.set_fractional_scores_enabled(True)
    rule = s.change_scoring_rule(assessment.id, "18,25", "30")
    s.set_fractional_scores_enabled(False)
    submission = s.register_submission(
        work.id, UtcInstant(UtcInstant.now().value - timedelta(days=1))
    )
    review = s.review_submission(
        submission.id, AttemptResult.SCORED, score="24", grade_kind=GradeKind.NUMERIC
    )
    assert (review.rule_id, review.min_cents, review.max_cents, review.score_cents) == (
        rule.id,
        1825,
        3000,
        2400,
    )
    assert s.work_result(work.id).status == StudentWorkStatus.SUBMITTED
    with pytest.raises(ValueError, match="выключен"):
        s.review_submission(submission.id, AttemptResult.SCORED, score="24,75")
    with pytest.raises(ValueError, match="выключен"):
        s.change_scoring_rule(assessment.id, "18,25", "30")
    assert len(s._r.reviews.for_owner(submission.id)) == 1


def test_target_submission_state_and_newer_submission_keeps_precedence(planned):
    s, _, _, _, _, _, work = planned
    at = UtcInstant(UtcInstant.now().value - timedelta(days=1))
    s1 = s.register_submission(work.id, at)
    s.review_submission(s1.id, AttemptResult.NEEDS_REVISION)
    s2 = s.register_submission(work.id, at)
    with pytest.raises(ValueError, match="ACCEPTED"):
        s.review_submission(s1.id, AttemptResult.SCORED, score="24")
    s.review_submission(s1.id, AttemptResult.ACCEPTED, score="24")
    assert s.work_result(work.id).status == StudentWorkStatus.SUBMITTED
    s.review_submission(s2.id, AttemptResult.SCORED, score="24")
    assert s.work_result(work.id).status == StudentWorkStatus.SUBMITTED
    assert [a.attempt_no for a in s._r.attempts.history(work.id)] == [1, 2]


def test_rule_change_requires_explicit_choice_and_preserves_snapshots(planned):
    s, _, _, _, _, assessment, work = planned
    old = s.current_rule(assessment.id)
    submission = s.register_submission(
        work.id, UtcInstant(UtcInstant.now().value - timedelta(days=1))
    )
    new = s.change_scoring_rule(assessment.id, "20", "40")
    with pytest.raises(ValueError, match="явно"):
        s.review_submission(submission.id, AttemptResult.ACCEPTED, score="24")
    first = s.review_submission(submission.id, AttemptResult.ACCEPTED, score="24", rule_id=old.id)
    second = s.review_submission(submission.id, AttemptResult.ACCEPTED, score="32", rule_id=new.id)
    assert (first.max_cents, second.max_cents) == (3000, 4000)
    assert s._r.reviews.find_by_id(first.id) == first


def test_preview_cancel_confirm_and_stale_plan_are_atomic(planned):
    s, offering, _, module, work, _, _ = planned
    snapshot = s.semester_plan(offering.id)
    preview = s.preview_plan_change(
        offering.id,
        module_changes=((module.id, module.revision, {"end_week": 7}),),
        work_changes=((work.id, work.revision, {"due_date": LocalDate(2027, 2, 10)}),),
        reason="Хвост после семестра",
    )
    assert preview.warnings and not preview.conflicts
    assert s.semester_plan(offering.id) == snapshot
    with pytest.raises(ValueError, match="Подтвердите"):
        s.apply_plan_change(preview)
    s.apply_plan_change(preview, confirmed=True)
    changed = s.semester_plan(offering.id)
    assert changed.modules[0].end_week == 7
    assert changed.works[0].due_date == LocalDate(2027, 2, 10)
    assert changed.issued == snapshot.issued
    with pytest.raises(RepositoryError):
        s.apply_plan_change(preview, confirmed=True)
    assert s.semester_plan(offering.id) == changed


def test_overlapping_modules_proposal_does_not_write_and_batch_is_valid(planned):
    s, offering, _, module, _, _, _ = planned
    neighbor = s.add_plan_module(offering.id, "M2", 7, 12)
    preview = s.preview_plan_change(
        offering.id, module_changes=((module.id, module.revision, {"end_week": 7}),)
    )
    assert preview.conflicts and preview.suggestions
    with pytest.raises(ValueError):
        s.apply_plan_change(preview)
    preview = s.preview_plan_change(
        offering.id,
        module_changes=(
            (module.id, module.revision, {"end_week": 7}),
            (neighbor.id, neighbor.revision, {"start_week": 8}),
        ),
    )
    s.apply_plan_change(preview)
    assert [(m.start_week, m.end_week) for m in s.semester_plan(offering.id).modules] == [
        (1, 7),
        (8, 12),
    ]


def test_debt_after_calendar_end_and_ended_enrollment_preserves_original_context(planned):
    s, offering, student, module, _, assessment, work = planned
    assert (
        next(v for v in s.student_module_results(student.id) if v.module.id == module.id).state
        == "unknown"
    )
    s.set_required_works(module.id, student.id, [work.id], reason="Обязательная H1")
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    future = UtcInstant(UtcInstant.now().value + timedelta(days=400))
    s._clock = lambda: future
    submission = s.register_submission(work.id, UtcInstant(future.value - timedelta(days=1)))
    assert s.work_is_late(assessment.id, submission.received_at)
    assert s._r.enrollments.find_by_id(enrollment.id).ended_at is not None
    result = next(v for v in s.student_module_results(student.id) if v.module.id == module.id)
    assert result.state == "open" and result.debt_works == (work.id,)
    s.review_submission(submission.id, AttemptResult.SCORED, score="24")
    assert (
        next(v for v in s.student_module_results(student.id) if v.module.id == module.id).state
        == "open"
    )
    s.review_submission(submission.id, AttemptResult.ACCEPTED, score="24")
    assert (
        next(v for v in s.student_module_results(student.id) if v.module.id == module.id).state
        == "closed"
    )
    assert s._r.assessments.find_by_id(assessment.id).offering_id == offering.id


def test_multiple_required_works_and_students_close_independently(planned):
    s, offering, student, module, _, _, work = planned
    other = s.add_planned_work(
        offering.id, "H2", AssessmentType.HOMEWORK, module_id=module.id, minimum="0", maximum="20"
    )
    assessment = s.issue_planned_work(other.id)
    w2 = s.get_or_create_work(student.id, assessment.id)
    student_b = s.create_student(offering.id, "Synthetic B")
    s.set_required_works(module.id, student.id, [work.id, w2.id], reason="Две работы")
    s.set_required_works(module.id, student_b.id, [], reason="Индивидуальный набор явно пуст")
    sub = s.register_submission(work.id, UtcInstant(UtcInstant.now().value - timedelta(days=1)))
    s.review_submission(sub.id, AttemptResult.ACCEPTED, score="24")
    assert next(
        v for v in s.student_module_results(student.id) if v.module.id == module.id
    ).debt_works == (w2.id,)
    assert (
        next(v for v in s.student_module_results(student_b.id) if v.module.id == module.id).state
        == "closed"
    )


def test_atomic_submission_multiple_files_late_db_failure_cleans_all(
    planned, tmp_path, monkeypatch
):
    s, _, _, _, _, _, work = planned
    paths = [tmp_path / "a.docx", tmp_path / "b.pdf"]
    for path in paths:
        path.write_bytes(b"synthetic immutable original")
    original = s._transaction
    from contextlib import contextmanager

    @contextmanager
    def late_failure():
        with original() as r:
            yield r
            raise ValueError("synthetic late failure after inserts")

    monkeypatch.setattr(s, "_transaction", late_failure)
    # Avoid the preliminary read failure so this exercises actual file/DB writes.
    calls = 0

    @contextmanager
    def after_first():
        nonlocal calls
        calls += 1
        with original() as r:
            yield r
            if calls > 1:
                raise ValueError("synthetic late failure after inserts")

    monkeypatch.setattr(s, "_transaction", after_first)
    with pytest.raises(ValueError, match="late failure"):
        s.register_submission(
            work.id, UtcInstant(UtcInstant.now().value - timedelta(days=1)), paths=paths
        )
    assert not s._r.attempts.history(work.id)
    assert not s._r.file_assets.list()
    assert not list(s._file_storage.paths.files_dir.glob("*/*.docx"))
    assert not list(s._file_storage.paths.files_dir.glob("*/*.pdf"))
    assert all(p.read_bytes() == b"synthetic immutable original" for p in paths)
    assert not list((s._file_storage.paths.files_dir / ".imports").glob("*.json"))


def test_course_versions_two_calendars_direction_identity_and_freeze(workflow):
    s, _, course, _, offering, _, _, _ = workflow
    direction = s.create_direction(" 15.15.03 ", "Synthetic")
    with pytest.raises(RepositoryError):
        s.create_direction("15.15.03")
    content = {
        "modules": [
            {"key": "m1", "title": "M1", "course_semester": 1, "start_week": 1, "end_week": 6}
        ],
        "works": [],
    }
    v1 = s.create_course_program(
        course.id, "Course-wide program", direction_ids=[direction.id], content=content
    )
    p1 = s.create_semester_plan(offering.id, version_id=v1.id, course_semester=1, weeks=17)
    term2 = s.create_term("T2", LocalDate(2027, 2, 1), LocalDate(2027, 6, 30))
    group2 = s.create_group("Synthetic 02")
    o2 = s.create_offering(term2.id, course.id, group2.id)
    p2 = s.create_semester_plan(o2.id, version_id=v1.id, course_semester=2, weeks=18)
    v2 = s.new_program_version(
        v1, content={"modules": [], "works": []}, direction_ids=[direction.id]
    )
    assert (p1.program_version_id, p2.program_version_id) == (v1.id, v1.id)
    assert p1.first_week_start != p2.first_week_start
    assert "15.15.03" in s.program_display_names(course.id)[v1.id]
    with pytest.raises(RepositoryError):
        s._r.program_versions.update(
            replace(v1, metadata=v1.metadata.touch(UtcInstant.now()), content_json="{}"),
            expected_revision=1,
        )
    assert s._r.program_versions.find_by_id(v2.id).version_no == 2


def test_version_freezes_definition_membership_and_requires_explicit_ordinal(workflow):
    s, _, course, _, offering, *_ = workflow
    first = s.create_topic(course.id, "Original topic")
    second = s.create_topic(course.id, "Changed topic")
    definition = s.create_work_definition(course.id, "Frozen work", AssessmentType.HOMEWORK)
    s.set_content_links("definition_topics", definition.id, [first.id])
    version = s.create_course_program(
        course.id,
        "Frozen course",
        content={"works": [{"definition_id": str(definition.id), "course_semester": 1}]},
    )
    s.set_content_links("definition_topics", definition.id, [second.id])
    with pytest.raises(ValueError, match="номер"):
        s.create_semester_plan(offering.id, version_id=version.id)
    assert s.semester_plan(offering.id) is None
    s.create_semester_plan(offering.id, version_id=version.id, course_semester=1)
    work = s.semester_plan(offering.id).works[0]
    assessment = s.issue_planned_work(work.id)
    assert [link.topic_id for link in s._r.assessment_topics.for_owner(assessment.id)] == [first.id]


def test_review_sql_guard_cannot_bypass_revision_contract(planned, runtime):
    s, _, _, _, _, _, work = planned
    submission = s.register_submission(
        work.id, UtcInstant(UtcInstant.now().value - timedelta(days=1))
    )
    prior = s.review_submission(submission.id, AttemptResult.NEEDS_REVISION)
    rule = s.scoring_rule(submission.rule_id)
    # Bypass the application command deliberately: production SQL must enforce
    # the target submission transition as well.
    raw = q.Review(
        metadata=s._meta(),
        submission_id=submission.id,
        review_seq=2,
        result=AttemptResult.SCORED,
        reviewed_at=s._clock(),
        rule_id=rule.id,
        min_cents=rule.min_cents,
        max_cents=rule.max_cents,
        score_cents=2400,
    )
    with pytest.raises(RepositoryError):
        s._r.reviews.insert(raw)
    assert s._r.reviews.for_owner(submission.id) == [prior]
    assert s._r.review_grades.list() == []
    with runtime._engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert connection.execute(text("PRAGMA integrity_check")).scalar() == "ok"


def test_material_metadata_links_and_multiple_files_rollback_after_real_insert(
    workflow, runtime, tmp_path
):
    from sqlalchemy import event

    from studium.domain.content import MaterialFileRole

    s, _, course, *_ = workflow
    paths = [tmp_path / "first.docx", tmp_path / "second.pdf"]
    for path in paths:
        path.write_bytes(b"Synthetic original")
    before = s._r.homework_definitions.list()
    writes = 0

    def fail(connection, cursor, statement, params, context, many):
        nonlocal writes
        if statement.startswith("INSERT INTO homework_attachments"):
            writes += 1
            if writes == 2:
                raise RuntimeError("Synthetic late attachment failure")

    event.listen(runtime._engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="late attachment"):
            s.save_content_package(
                "homework",
                None,
                {"course_id": course.id, "title": "Must roll back"},
                files=tuple((path, MaterialFileRole.STATEMENT) for path in paths),
            )
    finally:
        event.remove(runtime._engine, "after_cursor_execute", fail)
    assert writes == 2
    assert s._r.homework_definitions.list() == before
    assert not s._r.file_assets.list()
    assert not [
        path
        for path in s._file_storage.paths.files_dir.glob("*/*")
        if path.parent.name != ".imports"
    ]
    assert not list((s._file_storage.paths.files_dir / ".imports").glob("*.json"))


def test_external_working_copy_changes_do_not_mutate_original_and_teacher_snapshot(
    planned, tmp_path
):
    from hashlib import sha256

    s, _, _, _, _, _, work = planned
    path = tmp_path / "original.docx"
    path.write_bytes(b"Synthetic student original")
    sub = s.register_submission(work.id, UtcInstant.now(), paths=[path])
    asset = s._r.file_assets.list()[0]
    working = s._file_storage.working_copy(asset)
    working.write_bytes(b"Synthetic teacher correction")
    review = s.review_submission(sub.id, AttemptResult.NEEDS_REVISION, paths=[working])
    checked = s._r.file_assets.find_by_id(s._r.review_files.for_owner(review.id)[0].file_asset_id)
    assert (
        s._file_storage.path(asset).read_bytes()
        == path.read_bytes()
        == b"Synthetic student original"
    )
    assert s._file_storage.path(checked).read_bytes() == b"Synthetic teacher correction"
    working.write_bytes(b"Further unsaved correction")
    assert sha256(s._file_storage.path(checked).read_bytes()).hexdigest() == checked.sha256


def test_cancelled_active_denominator_and_archived_debt_restore_are_explicit(planned):
    s, offering, student, module, plan_work, assessment, work = planned
    s.set_required_works(module.id, student.id, [work.id], reason="Required")
    original = s.semester_plan(offering.id)
    preview = s.preview_plan_change(
        offering.id, work_changes=((plan_work.id, plan_work.revision, {"cancelled": True}),)
    )
    s.apply_plan_change(preview)
    rows, _ = s.student_package_summary(student.id)
    homework = next(row for row in rows if row[2] == AssessmentType.HOMEWORK)
    # An unrelated legacy work is active; cancellation adds no active denominator.
    assert homework[5] == 1 and homework[7] == 1
    assert s.semester_plan(offering.id).issued == original.issued
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(enrollment)
    ended = s._r.enrollments.find_by_id(enrollment.id)
    s._r.works.soft_delete(work.id, expected_revision=work.revision, at=UtcInstant.now())
    with pytest.raises(ValueError):
        s.restore_debt_context(work.id, reason="No confirmation")
    s.restore_debt_context(work.id, confirmed=True, reason="Original period debt")
    assert s._r.works.find_by_id(work.id).deleted_at is None
    assert s._r.enrollments.find_by_id(enrollment.id) == ended
    assert len(s._r.debt_restorations.for_owner(work.id)) == 1
