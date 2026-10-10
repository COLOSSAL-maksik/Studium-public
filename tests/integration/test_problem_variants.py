"""Shared conditions, purpose semantics and preservation of issued snapshots."""

import base64
import json

import pytest
from sqlalchemy.exc import IntegrityError

from studium.application.errors import ApplicationError
from studium.domain.content import GenerationCriteria, ProblemPurpose
from studium.domain.enums import AssessmentType
from studium.domain.repositories import RepositoryError
from tests.integration.test_application import runtime as runtime
from tests.integration.test_content_workflow import content as content


def family_with_variants(s, course, count=3):
    family = s.create_material(
        "problems",
        course_id=course.id,
        title="Балка",
        identifier="B-01",
        statement="Определить реакции опор",
        is_family=True,
        tags=("балка",),
        purposes=(ProblemPurpose.SEMINAR, ProblemPurpose.CONTROL),
    )
    variants = [
        s.create_material(
            "problems",
            course_id=course.id,
            family_id=family.id,
            title=f"Вариант {i}",
            variant_code=str(i),
            parameters=f"L={i} м",
            correct_answer=f"R={i}",
        )
        for i in range(1, count + 1)
    ]
    return family, variants


def test_multi_purpose_and_standalone_compatibility(content):
    s, _, course, *_ = content
    original = s.create_material(
        "problems", course_id=course.id, title="Original", statement="Unchanged"
    )
    family, variants = family_with_variants(s, course)
    assert s.list_materials("problems", purpose=ProblemPurpose.CONTROL) == (family,)
    assert s.list_materials("problems", purpose=ProblemPurpose.SEMINAR) == (family,)
    assert not s.list_materials("problems", purpose=ProblemPurpose.EXAM)
    pool = s.problem_pool(GenerationCriteria(course.id, 1))
    assert {p.id for p in pool} == {original.id, *(v.id for v in variants)}
    assert s.get_material("problems", original.id) == original
    assert all(v.statement == "" and v.purposes == () for v in variants)
    assert all(p.statement.startswith(family.statement) for p in pool if p.id != original.id)


def test_family_taxonomy_and_scheme_snapshots_survive_edits(content, tmp_path):
    s, _, course, offering, students = content
    family, variants = family_with_variants(s, course)
    skill = s.create_skill(course.id, "Равновесие")
    s.set_content_links("problem_skills", family.id, (skill.id,))
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
    )
    links = []
    for i, variant in enumerate(variants):
        path = tmp_path / f"scheme-{i}.png"
        path.write_bytes(png)
        links.append(s.import_file_for_material("problems", variant.id, path))
    criteria = GenerationCriteria(
        course.id, 3, purpose=ProblemPurpose.CONTROL, problem_ids=(family.id,)
    )
    draft = s.generate_ticket_draft(criteria)
    control = s.create_assessment(offering.id, "Рубежный контроль", AssessmentType.CONTROL_WORK)
    saved = s.save_ticket_set(offering.id, draft, assessment_id=control.id)
    before = s.ticket_set_details(saved.id)
    assert len(before) == 3
    for view in before:
        fact = view.problems[0]
        assert family.statement in fact.statement_snapshot
        assert json.loads(fact.teacher_snapshot_json)["skill_ids"] == [str(skill.id)]
        assert len(s.list_ticket_files(view.ticket.id)) == 1
    item = s.add_control_problem(control.id, variants[0].id)
    assignment = s.assign_student_problem(students[0].id, item.id, variants[0].id)
    assert family.statement in assignment.statement_snapshot
    assert s.assignment_skills(assignment) == (skill,)
    assert s.assigned_task_files(assignment.id)[0].asset.id == links[0].file_asset_id
    s.update_material("problems", family, statement="Изменённое общее условие")
    s.update_material("problems", variants[0], correct_answer="New answer")
    assert s.ticket_set_details(saved.id) == before
    assert s._r.student_problem_assignments.find_by_id(assignment.id) == assignment


def test_family_change_after_review_rejected_atomically(content):
    s, _, course, offering, *_ = content
    family, _ = family_with_variants(s, course)
    draft = s.generate_ticket_draft(GenerationCriteria(course.id, 2))
    s.update_material("problems", family, statement="New condition")
    with pytest.raises(RepositoryError):
        s.save_ticket_set(offering.id, draft)
    assert s.list_ticket_sets(offering.id) == ()


def test_variant_scope_and_unique_code_and_classification(content):
    s, _, course, offering, *_ = content
    family, variants = family_with_variants(s, course)
    other = s.create_course("Other")
    with pytest.raises(ApplicationError):
        s.create_material(
            "problems", course_id=other.id, family_id=family.id, title="Bad", variant_code="x"
        )
    with pytest.raises(RepositoryError):
        s.create_material(
            "problems",
            course_id=course.id,
            family_id=family.id,
            title="Duplicate",
            variant_code="1",
        )
    with pytest.raises(ValueError):
        s.create_material(
            "problems",
            course_id=course.id,
            family_id=family.id,
            title="Duplicated text",
            variant_code="x",
            statement="Duplicate",
        )
    skill = s.create_skill(course.id, "Skill")
    with pytest.raises(ApplicationError):
        s.set_content_links("problem_skills", variants[0].id, (skill.id,))
    control = s.create_assessment(offering.id, "RK", AssessmentType.CONTROL_WORK)
    with pytest.raises(ApplicationError):
        s.add_control_problem(control.id, family.id)


def test_db_rejects_invalid_purpose(content):
    s, _, course, *_ = content
    problem = s.create_material("problems", course_id=course.id, title="Synthetic")
    bind = s._r.problems._sessions.kw["bind"]
    with pytest.raises(IntegrityError), bind.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE problems SET purposes_json='[\"FREE_TAG\"]',revision=revision+1 WHERE id=?",
            (str(problem.id),),
        )
    family, _ = family_with_variants(s, course)
    with pytest.raises(IntegrityError), bind.begin() as connection:
        connection.exec_driver_sql("DELETE FROM problems WHERE id=?", (str(family.id),))
    assert s.get_material("problems", family.id) == family
