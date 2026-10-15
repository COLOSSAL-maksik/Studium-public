"""Real synthetic annual workflow, revision isolation and portable graph exchange."""

import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from studium.composition import create_runtime
from studium.domain import annual_program as a
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import EntityId, LocalDate
from tests.integration.test_application import runtime as runtime


def filled(service):
    course = service.create_course("Synthetic annual discipline")
    parent = service.create_topic(course.id, "Mechanics")
    topic = service.create_topic(course.id, "Dynamics", parent_topic_id=parent.id)
    skill = service.create_skill(course.id, "Use Newton laws")
    draft = service.create_program_draft(course.id, "Synthetic annual program")
    data = json.loads(draft.content_json)
    annual = data["annual"]
    annual["passport"]["directions"] = [
        {"code": "01.03.01", "name": "Mathematics"},
        {"code": "03.03.01", "name": ""},
    ]
    for index, semester in enumerate(annual["semesters"]):
        semester["modules"] = [
            dict(
                key=a.key(),
                title=f"Module {index}",
                start_week=1,
                end_week=8,
                lessons=[
                    dict(
                        key=a.key(),
                        kind="LECTURE",
                        title="Laws",
                        hours="1.25",
                        topic_ids=[str(parent.id), str(topic.id)],
                        week=1,
                        notes="",
                    ),
                    dict(
                        key=a.key(),
                        kind="LAB",
                        title="Experiment",
                        hours="3",
                        topic_ids=[str(topic.id)],
                        week=2,
                        notes="",
                    ),
                ],
                works=[
                    dict(
                        key=a.key(),
                        title="Homework",
                        category="HOMEWORK",
                        min_cents=0,
                        max_cents=3000,
                        rules="Criteria",
                    )
                ],
            )
        ]
    module = annual["semesters"][0]["modules"][0]
    annual["outcomes"] = [
        dict(
            key=a.key(),
            category=kind,
            code="",
            text=kind,
            topic_ids=[str(topic.id)],
            skill_ids=[str(skill.id)],
            module_keys=[module["key"]],
            work_keys=[module["works"][0]["key"]],
        )
        for kind in a.OUTCOME_KINDS
    ]
    annual["prerequisites"] = [
        dict(key=a.key(), discipline="Calculus", content="Derivatives and integrals")
    ]
    annual["loads"] = [
        dict(
            key=a.key(),
            semester_key=annual["semesters"][0]["key"],
            kind="SELF_STUDY",
            hours="10.25",
        )
    ]
    annual["norms"] = [
        dict(key=a.key(), semester_key=annual["semesters"][0]["key"], kind="LECTURE", hours="2")
    ]
    annual["budgets"] = [dict(key=a.key(), module_key=module["key"], category="*", max_cents=15000)]
    draft = service.save_program_draft(draft, data)
    return course, draft


def test_draft_restart_stale_and_atomic_publication(runtime):
    s = runtime.service
    course, draft = filled(s)
    assert not s.list_terms() and not s.list_students() and not s.list_offerings()
    data = json.loads(draft.content_json)
    assert not s.check_program_draft(draft)
    before = draft
    draft = s.save_program_draft(draft, data)
    with pytest.raises(RepositoryError):
        s.save_program_draft(before, data)
    version = s.publish_program_draft(draft)
    assert not s.list_program_drafts(course.id)
    snapshot = version.content_json
    next_draft = s.create_program_draft(course.id, previous=version)
    content = json.loads(next_draft.content_json)
    content["annual"]["passport"]["label"] = "Next edition"
    next_draft = s.save_program_draft(next_draft, content)
    second = s.publish_program_draft(next_draft)
    assert second.version_no == 2
    assert s.get_program_version(version.id).content_json == snapshot
    assert len(s._r.homework_definitions.list()) == 2
    assert a.volume(data["annual"])[0].hours == a.hours("1.25")
    assert a.score_totals(data["annual"])[1].maximum == 15000


def test_incomplete_draft_reopen_and_integrity(runtime):
    s = runtime.service
    course = s.create_course("Empty profile")
    draft = s.create_program_draft(course.id)
    with pytest.raises(ValueError):
        s.publish_program_draft(draft)
    data = json.loads(draft.content_json)
    data["annual"]["passport"]["notes"] = "Continue later"
    draft = s.save_program_draft(draft, data)
    root = Path(runtime.diagnostics.database_path).parent
    runtime.close()
    reopened = create_runtime(root)
    try:
        s = reopened.service
        assert s.get_program_draft(draft.id) == draft
        assert (
            json.loads(s.get_program_draft(draft.id).content_json)["annual"]["passport"]["notes"]
            == "Continue later"
        )
        broken = deepcopy(data)
        broken["annual"]["semesters"][0]["weeks"] = -1
        with pytest.raises(ValueError):
            s.save_program_draft(draft, broken)
        assert s.get_program_draft(draft.id) == draft
    finally:
        reopened.close()


def test_two_groups_independent_planned_lessons_and_no_facts(runtime):
    s = runtime.service
    course, draft = filled(s)
    version = s.publish_program_draft(draft)
    term = s.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    offerings = [
        s.create_offering(
            term.id,
            course.id,
            s.create_group(f"G-{i}").id,
            course_version_id=version.id,
            course_semester=1,
        )
        for i in range(2)
    ]
    first = s.planned_program_lessons(offerings[0].id)
    second = s.planned_program_lessons(offerings[1].id)
    assert len(first) == len(second) == 2
    changed = s.update_program_plan_lesson(first[0], week=4, topic_ids=[], reason="Later")
    assert (
        changed.baseline_json == first[0].baseline_json
        and changed.current_json != first[0].current_json
    )
    assert s.planned_program_lessons(offerings[1].id) == second
    assert not s._r.lessons.list() and not s._r.assessments.list() and not s._r.attempts.list()
    assert s.semester_plan(offerings[0].id).works[0].max_cents == 3000


def test_portable_roundtrip_empty_other_profile_and_duplicate(runtime, tmp_path):
    s = runtime.service
    _, draft = filled(s)
    version = s.publish_program_draft(draft)
    path = tmp_path / "synthetic.studium-program"
    package = s.export_program(version.id, path)
    with create_profile(tmp_path / "other") as target:
        preview = target.preview_program_import(path)
        assert not target.list_courses()
        imported = target.commit_program_import(preview)
        original = json.loads(version.content_json)
        new = json.loads(imported.content_json)
        assert new["annual"]["passport"] == original["annual"]["passport"]
        assert a.volume(new["annual"])[0].hours == a.volume(original["annual"])[0].hours
        assert (
            a.score_totals(new["annual"])[-1].maximum
            == a.score_totals(original["annual"])[-1].maximum
        )
        assert set(new["topic_ids"]).isdisjoint(original["topic_ids"])
        again = target.preview_program_import(path)
        assert again.matches
        with pytest.raises(ValueError, match="уже импортирована"):
            target.commit_program_import(again)
        copy = target.commit_program_import(again, independent_copy=True)
        assert copy.course_program_id != imported.course_program_id
        assert package.origin == preview.package.origin
        relayed = target.export_program(imported.id, tmp_path / "relayed.studium-program")
        assert relayed.origin == package.origin and relayed.content_hash == package.content_hash
        assert target.preview_program_import(tmp_path / "relayed.studium-program").matches


@contextmanager
def create_profile(path):
    runtime = create_runtime(path)
    try:
        yield runtime.service
    finally:
        runtime.close()


def test_template_family_dependencies_and_files_roundtrip(runtime, tmp_path):
    from studium.domain.enums import AssessmentType

    s = runtime.service
    course, draft = filled(s)
    topic_id = json.loads(draft.content_json)["topic_ids"][0]
    family = s.create_material(
        "problems",
        course_id=course.id,
        title="Family",
        statement="Shared statement",
        is_family=True,
    )
    variant = s.create_material(
        "problems",
        course_id=course.id,
        title="Variant",
        family_id=family.id,
        variant_code="A",
        correct_answer="42",
        parameters="a=2",
        details_json=json.dumps(
            {
                "structured_answers": [
                    dict(
                        name="Force",
                        symbol="F",
                        kind="numeric",
                        value="42.12345",
                        units="N",
                        formula="m*a",
                        comment="",
                    )
                ],
                "private_source_path": "DO-NOT-EXPORT",
            }
        ),
    )
    definition = s.create_work_definition(course.id, "Library homework", AssessmentType.HOMEWORK)
    s.set_content_links("definition_problems", definition.id, [variant.id])
    s.set_content_links("problem_topics", family.id, [EntityId(topic_id)])
    source = tmp_path / "synthetic.txt"
    source.write_bytes(b"Synthetic exact immutable file bytes")
    s.import_file_for_material("homework", definition.id, source)
    data = json.loads(draft.content_json)
    data["annual"]["semesters"][0]["modules"][0]["works"][0]["definition_id"] = str(definition.id)
    draft = s.save_program_draft(draft, data)
    draft = s.attach_program_documents(draft, [source])
    version = s.publish_program_draft(draft)
    archive = tmp_path / "files.studium-program"
    s.export_program(version.id, archive, include_files=True)
    with create_profile(tmp_path / "receiver-files") as target:
        preview = target.preview_program_import(archive)
        assert "DO-NOT-EXPORT" not in preview.package.payload_json
        imported = target.commit_program_import(preview)
        incoming = json.loads(imported.content_json)
        assert len(incoming["file_asset_ids"]) == 2
        for id in incoming["file_asset_ids"]:
            assert target.accessible_file_path(EntityId(id)).read_bytes() == source.read_bytes()
        assert (
            incoming["problem_snapshots"][0]["statement"]
            == json.loads(version.content_json)["problem_snapshots"][0]["statement"]
        )
        assert (
            json.loads(incoming["problem_snapshots"][0]["details_json"])["structured_answers"][0][
                "value"
            ]
            == "42.12345"
        )
        assert target._r.definition_problems.list()
        assert not target._r.lessons.list() and not target._r.assessments.list()
        relayed = target.export_program(
            imported.id, tmp_path / "reexport.studium-program", include_files=True
        )
        assert relayed.content_hash == preview.package.content_hash
        assert relayed.files == preview.package.files
    empty = tmp_path / "without-files.studium-program"
    s.export_program(version.id, empty, include_files=False)
    preview = s.preview_program_import(empty)
    assert preview.package.excluded_files == 2 and not preview.package.files
    assert not json.loads(preview.package.payload_json)["content"]["file_asset_ids"]


def test_import_late_database_failure_rolls_back_files_and_rows(runtime, tmp_path, monkeypatch):
    from sqlalchemy import event

    from tests.integration.test_file_migrations import snapshot

    s = runtime.service
    _, draft = filled(s)
    source = tmp_path / "document.txt"
    source.write_text("Synthetic document")
    draft = s.attach_program_documents(draft, [source])
    version = s.publish_program_draft(draft)
    path = tmp_path / "rollback.studium-program"
    s.export_program(version.id, path, include_files=True)
    other = create_runtime(tmp_path / "failure-target")
    try:
        preview = other.service.preview_program_import(path)
        with other._engine.connect() as conn:
            before = snapshot(conn)

        def fail(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO program_imports"):
                raise RuntimeError("Synthetic late import failure")

        event.listen(other._engine, "after_cursor_execute", fail)
        with pytest.raises(RuntimeError, match="late import"):
            other.service.commit_program_import(preview)
        with other._engine.connect() as conn:
            assert snapshot(conn) == before
        root = tmp_path / "failure-target" / "files"
        assert not [p for p in root.rglob("*") if p.is_file() and p.name != "lock"]
    finally:
        other.close()


def test_repeat_code_conflict_same_name_and_distinct_editions(runtime, tmp_path):
    s = runtime.service
    course, draft = filled(s)
    first = s.publish_program_draft(draft)
    path = tmp_path / "edition1.studium-program"
    s.export_program(first.id, path)
    with create_profile(tmp_path / "conflicts") as target:
        local = target.create_course(course.name)
        direction = target.create_direction("01.03.01", "Different local name")
        target.create_topic(local.id, "Mechanics")
        preview = target.preview_program_import(path)
        assert any("Different local name" in w for w in preview.warnings)
        imported = target.commit_program_import(preview, course_id=local.id)
        assert target.list_directions()[0].name == "Different local name"
        assert target._r.directions.find_by_id(direction.id).name == "Different local name"
        assert len([t for t in target.list_course_topics(local.id) if t.title == "Mechanics"]) == 2
        draft2 = s.create_program_draft(course.id, previous=first)
        data = json.loads(draft2.content_json)
        data["annual"]["passport"]["label"] = "Second"
        second = s.publish_program_draft(s.save_program_draft(draft2, data))
        s.export_program(second.id, tmp_path / "edition2.studium-program")
        preview2 = target.preview_program_import(tmp_path / "edition2.studium-program")
        assert not preview2.matches
        target.commit_program_import(preview2, course_id=local.id)
        assert target.get_program_version(imported.id).content_json == imported.content_json


def test_fractional_mode_and_late_publication_failure(runtime, monkeypatch):
    from sqlalchemy import event

    s = runtime.service
    _, draft = filled(s)
    data = json.loads(draft.content_json)
    data["annual"]["semesters"][0]["modules"][0]["works"][0]["max_cents"] = 3025
    with pytest.raises(ValueError, match="Дробный ввод выключен"):
        s.save_program_draft(draft, data)
    s.set_fractional_scores_enabled(True)
    draft = s.save_program_draft(draft, data)
    s.set_fractional_scores_enabled(False)
    draft = s.save_program_draft(draft, data)

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO program_directions"):
            raise RuntimeError("Synthetic late publication failure")

    event.listen(runtime._engine, "after_cursor_execute", fail)
    with pytest.raises(RuntimeError, match="late publication"):
        s.publish_program_draft(draft)
    assert s.get_program_draft(draft.id) == draft
    assert not s._r.program_versions.list() and not s._r.homework_definitions.list()
    event.remove(runtime._engine, "after_cursor_execute", fail)
    assert s.publish_program_draft(draft).version_no == 1


def test_actual_binding_topics_deviations_and_sql_baseline_guards(runtime):
    from sqlalchemy import text

    s = runtime.service
    course, draft = filled(s)
    version = s.publish_program_draft(draft)
    term = s.create_term("Synthetic actual", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    group = s.create_group("ACTUAL")
    offering = s.create_offering(
        term.id, course.id, group.id, course_version_id=version.id, course_semester=1
    )
    planned = s.planned_program_lessons(offering.id)[0]
    actual = s.create_lesson(offering.id, LocalDate(2026, 9, 29), title="Actual late")
    topic = s.create_topic(course.id, "Additional actual topic")
    s.attach_lesson_topic(actual.id, topic.id)
    linked = s.bind_actual_program_lesson(planned, actual.id)
    lesson, topics = s.actual_program_lesson_content(linked)
    assert lesson == actual and topics == (topic,)
    assert json.loads(linked.baseline_json)["week"] == 1
    assert not s._r.attendance.list()
    assert s.get_program_version(version.id) == version
    for change in ("baseline_json='{}'", "lesson_id=NULL"):
        with pytest.raises(Exception):
            with runtime._engine.begin() as connection:
                connection.execute(
                    text(f"UPDATE plan_lessons SET {change},revision=revision+1 WHERE id=:id"),
                    {"id": str(linked.id)},
                )


def test_semantic_roundtrip_complete_graph_with_normalized_ids(runtime, tmp_path):
    from studium.application.program_exchange import content_allowlist, remap_tree

    s = runtime.service
    _, draft = filled(s)
    first = s.publish_program_draft(draft)
    path = tmp_path / "semantic.studium-program"
    s.export_program(first.id, path)
    with create_profile(tmp_path / "semantic-receiver") as target:
        second = target.commit_program_import(target.preview_program_import(path))
        original = content_allowlist(json.loads(first.content_json), include_files=False)
        copied = content_allowlist(json.loads(second.content_json), include_files=False)
        mapping = {}

        def pair(left, right):
            if isinstance(left, dict):
                for name in ("key", "id"):
                    if name in left:
                        mapping[left[name]] = right[name]
                for k in left.keys() & right.keys():
                    if isinstance(left[k], (dict, list)):
                        pair(left[k], right[k])
            elif isinstance(left, list):
                assert len(left) == len(right)
                for lvalue, rvalue in zip(left, right, strict=True):
                    pair(lvalue, rvalue)

        pair(original, copied)

        def normalize_refs(value):
            if isinstance(value, dict):
                return {
                    name: sorted(item)
                    if name.endswith("_ids") or name in {"module_keys", "work_keys"}
                    else normalize_refs(item)
                    for name, item in value.items()
                }
            if isinstance(value, list):
                return [normalize_refs(item) for item in value]
            return value

        assert normalize_refs(remap_tree(original, mapping)) == normalize_refs(copied)
