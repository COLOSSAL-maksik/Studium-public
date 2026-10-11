"""Frozen classification dependencies: real synthetic persistence regressions."""

import json

import pytest
from alembic import command
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton, QTreeWidgetItemIterator
from sqlalchemy import event

from studium.application.errors import ApplicationError, FrozenTaxonomyDependencyError
from studium.application.services import StudiumService
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import (
    SCHEMA_REVISION,
    migration_config,
    upgrade_database,
)
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.database.unit_of_work import repository_set, transaction_factory
from studium.infrastructure.user_data import JsonPreferences
from studium.presentation.desktop.learning import LearningCatalogueDialog
from studium.presentation.desktop.messages import TEXT, error_message
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_file_migrations import snapshot
from tests.integration.test_pr3_review import content


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_frozen_problem_taxonomy_archive_preserves_issuability(workflow, kind):
    s, _, course, _, offering, _, _, _ = workflow
    topic = s.create_topic(course.id, "Frozen topic")
    skill = s.create_skill(course.id, "Frozen skill")
    problem = s.create_material(
        "problems", course_id=course.id, title="Frozen problem", statement="Saved statement"
    )
    s.set_content_links("problem_topics", problem.id, [topic.id])
    s.set_content_links("problem_skills", problem.id, [skill.id])
    definition = s.create_work_definition(course.id, "Frozen homework", AssessmentType.HOMEWORK)
    s.set_content_links("definition_problems", definition.id, [problem.id])
    version = s.create_course_program(course.id, "Frozen program", content=content(definition))
    s.create_semester_plan(offering.id, version_id=version.id, course_semester=1)
    work = s.semester_plan(offering.id).works[0]
    target = topic if kind == "topic" else skill
    try:
        getattr(s, "archive_" + kind)(target)
    except ApplicationError as error:
        assert str(error) == "frozen_taxonomy_dependency"
    else:
        # On the reported HEAD archive succeeds, then the actual SQL link guard fails.
        s.issue_planned_work(work.id)
        pytest.fail("Archive must reject a frozen dependency before it breaks issuance")
    assert getattr(s._r, kind + "s").find_by_id(target.id) == target
    assessment = s.issue_planned_work(work.id)
    item = s._r.items.for_assessment(assessment.id)[0]
    assert [v.topic_id for v in s._r.item_topics.for_owner(item.id)] == [topic.id]
    assert [v.skill_id for v in s._r.item_skills.for_owner(item.id)] == [skill.id]


def saved_context(workflow, scope):
    s, _, course, _, offering, student, _, _ = workflow
    topic = s.create_topic(course.id, "Saved topic")
    skill = s.create_skill(course.id, "Saved skill")
    source = s.create_material(
        "problems",
        course_id=course.id,
        title="Saved source",
        statement="Saved text",
        is_family=scope == "family",
    )
    problem = (
        s.create_material(
            "problems",
            course_id=course.id,
            title="Variant",
            family_id=source.id,
            variant_code="A",
            parameters="x=1",
        )
        if scope == "family"
        else source
    )
    definition = s.create_work_definition(course.id, "Saved homework", AssessmentType.HOMEWORK)
    s.set_content_links("definition_problems", definition.id, [problem.id])
    prefix, owner = ("definition", definition) if "definition" in scope else ("problem", source)
    s.set_content_links(prefix + "_topics", owner.id, [topic.id])
    s.set_content_links(prefix + "_skills", owner.id, [skill.id])
    if scope.startswith("manual"):
        s.create_semester_plan(offering.id)
        work = s.add_planned_work(
            offering.id,
            "Independent saved work",
            AssessmentType.HOMEWORK,
            definition_id=definition.id,
        )
        version = None
    else:
        version = s.create_course_program(course.id, "Saved program", content=content(definition))
        if scope == "unassigned":
            work = None
        else:
            s.create_semester_plan(offering.id, version_id=version.id, course_semester=1)
            work = s.semester_plan(offering.id).works[0]
    # The dependency comes from recorded content, even when all mutable links change.
    s.set_content_links(prefix + "_topics", owner.id, [])
    s.set_content_links(prefix + "_skills", owner.id, [])
    return s, offering, student, topic, skill, problem, definition, version, work


def state(runtime):
    with runtime._engine.connect() as db:
        return snapshot(db)


@pytest.mark.parametrize("kind", ["topic", "skill"])
@pytest.mark.parametrize(
    "scope", ["definition", "family", "manual", "manual_definition", "unassigned"]
)
def test_saved_dependencies_after_live_links_change(workflow, runtime, kind, scope):
    s, _, student, topic, skill, problem, _, version, work = saved_context(workflow, scope)
    target = topic if kind == "topic" else skill
    before = state(runtime)
    with pytest.raises(FrozenTaxonomyDependencyError) as caught:
        getattr(s, "archive_" + kind)(target)
    assert state(runtime) == before
    dependencies = caught.value.dependencies
    assert {v.kind for v in dependencies} == (
        {"planned_work"}
        if scope.startswith("manual")
        else {"version"}
        if scope == "unassigned"
        else {"version", "planned_work"}
    )
    message = error_message(caught.value)
    assert "Архивирование отменено" in message
    assert all(str(v.id) in message and v.title in message for v in dependencies)
    if work:
        assert "ТЕСТ-01" in message
    with pytest.raises(RepositoryError):
        getattr(s._r, kind + "s").soft_delete(
            target.id, expected_revision=target.revision, at=UtcInstant.now()
        )
    assert state(runtime) == before
    if not work:
        s.create_semester_plan(workflow[4].id, version_id=version.id, course_semester=1)
        work = s.semester_plan(workflow[4].id).works[0]
    assessment = s.issue_planned_work(work.id)
    if "definition" in scope:
        assert [v.topic_id for v in s._r.assessment_topics.for_owner(assessment.id)] == [topic.id]
        assert [v.skill_id for v in s._r.assessment_skills.for_owner(assessment.id)] == [skill.id]
    else:
        item = s._r.items.for_assessment(assessment.id)[0]
        assert [v.topic_id for v in s._r.item_topics.for_owner(item.id)] == [topic.id]
        assert [v.skill_id for v in s._r.item_skills.for_owner(item.id)] == [skill.id]
        assignment = s.assign_student_problem(student.id, item.id, problem.id)
        saved = json.loads(assignment.teacher_snapshot_json)
        assert saved["topic_ids"] == [str(topic.id)] and saved["skill_ids"] == [str(skill.id)]


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_individual_assignment_without_program_freezes_classification(workflow, runtime, kind):
    s, _, course, _, _, student, assessment, _ = workflow
    topic = s.create_topic(course.id, "Individual topic")
    skill = s.create_skill(course.id, "Individual skill")
    family = s.create_material("problems", course_id=course.id, title="Family", is_family=True)
    problem = s.create_material(
        "problems",
        course_id=course.id,
        title="Variant",
        family_id=family.id,
        variant_code="1",
        parameters="x=7",
    )
    s.set_content_links("problem_topics", family.id, [topic.id])
    s.set_content_links("problem_skills", family.id, [skill.id])
    item = s.create_assessment_item(assessment.id, "Independent slot")
    assignment = s.assign_student_problem(student.id, item.id, problem.id)
    s.set_content_links("problem_topics", family.id, [])
    s.set_content_links("problem_skills", family.id, [])
    target = topic if kind == "topic" else skill
    before = state(runtime)
    with pytest.raises(FrozenTaxonomyDependencyError) as caught:
        getattr(s, "archive_" + kind)(target)
    assert [(v.kind, v.id) for v in caught.value.dependencies] == [
        ("student_assignment", assignment.id)
    ]
    assert state(runtime) == before
    with pytest.raises(RepositoryError):
        getattr(s._r, kind + "s").soft_delete(target.id, expected_revision=1, at=UtcInstant.now())
    assert state(runtime) == before
    assert s.assign_student_problem(student.id, item.id, problem.id) == assignment
    assert str(assignment.id) in error_message(caught.value)


def test_subtree_refusal_is_atomic_and_unbound_taxonomy_can_archive(workflow, runtime):
    s, _, _, topic, _, _, _, _, _ = saved_context(workflow, "family")
    parent = s.create_topic(topic.course_id, "Parent")
    topic = s.update_topic(topic, parent_topic_id=parent.id)
    sibling = s.create_topic(topic.course_id, "Free sibling", parent_topic_id=parent.id)
    before = state(runtime)
    with pytest.raises(FrozenTaxonomyDependencyError):
        s.archive_topic(parent)
    assert state(runtime) == before
    s.archive_topic(sibling)
    assert s._r.topics.find_by_id(sibling.id, include_deleted=True).deleted_at is not None
    free = s.create_skill(topic.course_id, "Free skill")
    s.archive_skill(free)
    assert s._r.skills.find_by_id(free.id, include_deleted=True).deleted_at is not None


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_direct_version_reference_is_protected(workflow, runtime, kind):
    s, _, course, *_ = workflow
    target = getattr(s, "create_" + kind)(course.id, "Selected taxonomy")
    version = s.create_course_program(
        course.id, "Selected program", content={kind + "_ids": [str(target.id)]}
    )
    before = state(runtime)
    with pytest.raises(FrozenTaxonomyDependencyError) as caught:
        getattr(s, "archive_" + kind)(target)
    assert [(v.kind, v.id) for v in caught.value.dependencies] == [("version", version.id)]
    with pytest.raises(RepositoryError):
        getattr(s._r, kind + "s").soft_delete(target.id, expected_revision=1, at=UtcInstant.now())
    assert state(runtime) == before


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_new_snapshot_refuses_already_archived_classification_atomically(workflow, runtime, kind):
    s, _, course, *_ = workflow
    target = getattr(s, "create_" + kind)(course.id, "Previously archived")
    problem = s.create_material("problems", course_id=course.id, title="P")
    s.set_content_links("problem_" + kind + "s", problem.id, [target.id])
    definition = s.create_work_definition(course.id, "D", AssessmentType.HOMEWORK)
    s.set_content_links("definition_problems", definition.id, [problem.id])
    getattr(s, "archive_" + kind)(target)
    before = state(runtime)
    with pytest.raises(ApplicationError, match="frozen_taxonomy_archived"):
        s.create_course_program(course.id, "Invalid saved content", content=content(definition))
    assert state(runtime) == before


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_individual_capture_refusal_does_not_create_student_work(workflow, runtime, kind):
    s, _, course, _, offering, _, assessment, _ = workflow
    student = s.create_student(offering.id, "Synthetic unassigned student")
    target = getattr(s, "create_" + kind)(course.id, "Archived classification")
    problem = s.create_material("problems", course_id=course.id, title="Independent P")
    s.set_content_links("problem_" + kind + "s", problem.id, [target.id])
    item = s.create_assessment_item(assessment.id, "Independent slot")
    getattr(s, "archive_" + kind)(target)
    before = state(runtime)
    with pytest.raises(ApplicationError, match="frozen_taxonomy_archived"):
        s.assign_student_problem(student.id, item.id, problem.id)
    assert state(runtime) == before
    assert s.find_student_work(student.id, assessment.id) is None


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_gui_archive_shows_dependent_assignments(qt_app, workflow, runtime, monkeypatch, kind):
    s, _, _, topic, _, _, _, version, work = saved_context(workflow, "family")
    course = s._r.courses.find_by_id(topic.course_id)
    dialog = LearningCatalogueDialog(s, course)
    warnings = []
    monkeypatch.setattr("studium.presentation.desktop.learning.confirm", lambda *a, **k: True)
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: warnings.append(text))
    index = 0 if kind == "topic" else 1
    dialog.tabs.setCurrentIndex(index)
    if kind == "topic":
        iterator = QTreeWidgetItemIterator(dialog.tree)
        while iterator.value():
            item = iterator.value()
            if getattr(item.data(0, Qt.ItemDataRole.UserRole), "id", None) == topic.id:
                dialog.tree.setCurrentItem(item)
                break
            iterator += 1
        assert dialog.topic().id == topic.id
    else:
        dialog.skill_view.selectRow(0)
    dialog.show()
    qt_app.processEvents()
    before = state(runtime)
    archive = next(
        b
        for b in dialog.tabs.widget(index).findChildren(QPushButton)
        if b.text() == TEXT["archive"]
    )
    QTest.mouseClick(archive, Qt.MouseButton.LeftButton)
    assert len(warnings) == 1
    assert str(version.id) in warnings[0] and str(work.id) in warnings[0]
    assert work.title in warnings[0] and "ТЕСТ-01" in warnings[0]
    assert state(runtime) == before
    dialog.close()
    dialog.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize("kind", ["topic", "skill"])
def test_frozen_dependencies_and_facts_survive_reopen_and_backup(workflow, runtime, tmp_path, kind):
    from studium.application.backup import BackupControl
    from studium.infrastructure.backup import LocalBackup
    from studium.infrastructure.user_data import AppPaths

    s, offering, student, topic, skill, _, _, _, work = saved_context(workflow, "family")
    submission = s.register_student_submission(student.id, workflow[6].id, UtcInstant.now())
    s.review_submission(submission.id, AttemptResult.ACCEPTED)
    file = tmp_path / "synthetic.txt"
    file.write_bytes(b"synthetic immutable original")
    asset = s.import_file_for_attempt(submission.attempt_id, file)
    before = state(runtime)
    target = topic if kind == "topic" else skill
    backend = LocalBackup(AppPaths(s._file_storage.root))
    archive = tmp_path.parent / (tmp_path.name + ".zip")
    backend.create(archive, BackupControl())
    destination = tmp_path.parent / (tmp_path.name + "-restored")
    backend.restore(archive, destination, backend.verify(archive, BackupControl()), BackupControl())
    for profile in (s._file_storage.root, destination):
        reopened = create_runtime(profile)
        try:
            rs = reopened.service
            assert state(reopened) == before
            with pytest.raises(FrozenTaxonomyDependencyError):
                getattr(rs, "archive_" + kind)(target)
            assert state(reopened) == before
            assert (
                rs._r.file_assets.find_by_id(asset.file_asset_id).sha256
                == s._r.file_assets.find_by_id(asset.file_asset_id).sha256
            )
            issued = rs.issue_planned_work(work.id)
            item = rs._r.items.for_assessment(issued.id)[0]
            assert [v.topic_id for v in rs._r.item_topics.for_owner(item.id)] == [topic.id]
            assert [v.skill_id for v in rs._r.item_skills.for_owner(item.id)] == [skill.id]
            assert rs._r.reviews.for_owner(submission.id)[0].result == AttemptResult.ACCEPTED
            assert rs.plan_content_bindings(offering.id) == s.plan_content_bindings(offering.id)
        finally:
            reopened.close()


@pytest.mark.parametrize("fail", [False, True])
def test_populated_v11_additive_guards_preserve_rows_and_rollback(tmp_path, fail):
    engine = create_database_engine(tmp_path / "v11.sqlite", wal=False)
    with engine.begin() as db:
        config = migration_config()
        config.attributes["connection"] = db
        command.upgrade(config, "0011_qa_review_fixes")
    sessions = create_session_factory(engine)
    s = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(tmp_path / "preferences.json"),
    )
    term = s.create_term("Synthetic v11", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic")
    group = s.create_group("Synthetic")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student")
    assessment = s.create_assessment(offering.id, "Synthetic", AssessmentType.HOMEWORK)
    work = s.get_or_create_work(student.id, assessment.id)
    synthetic = (s, term, course, group, offering, student, assessment, work)
    _, _, _, topic, skill, _, _, _, planned = saved_context(synthetic, "family")
    # Actual v11 permits this raw archive. v12 must not invent a historical repair.
    s._r.topics.soft_delete(topic.id, expected_revision=1, at=UtcInstant.now())
    with engine.connect() as db:
        before, objects = snapshot(db)

    def late_failure(connection, cursor, statement, parameters, context, executemany):
        if "CREATE TRIGGER skills_frozen_content_archive" in statement:
            raise RuntimeError("synthetic late v12 failure")

    if fail:
        event.listen(engine, "after_cursor_execute", late_failure)
        with pytest.raises(RuntimeError, match="late v12 failure"):
            upgrade_database(engine)
        event.remove(engine, "after_cursor_execute", late_failure)
        with engine.connect() as db:
            assert snapshot(db) == (before, objects)
            assert (
                db.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0011_qa_review_fixes"
            )
    upgrade_database(engine)
    with engine.connect() as db:
        after, new_objects = snapshot(db)
        assert after == before
        assert set(objects).issubset(set(new_objects))
        assert len(new_objects) == len(objects) + 2
        assert (
            db.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == SCHEMA_REVISION
        )
    upgrade_database(engine)
    with engine.connect() as db:
        assert snapshot(db) == (after, new_objects)
    with pytest.raises(RepositoryError):
        s._r.skills.soft_delete(skill.id, expected_revision=1, at=UtcInstant.now())
    with pytest.raises(ApplicationError, match="frozen_taxonomy_archived"):
        s.issue_planned_work(planned.id)
    with engine.connect() as db:
        assert snapshot(db) == (after, new_objects)
    engine.dispose()
