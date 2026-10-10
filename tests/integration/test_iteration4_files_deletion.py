"""Safety regressions exercise saved facts, independent sources and UI reopening."""

import pytest
from PySide6.QtCore import QThreadPool
from sqlalchemy import event

from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult, LessonType
from studium.presentation.desktop.library import ContentEditor
from tests.integration.test_application import runtime as runtime
from tests.integration.test_content_workflow import content as content
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


@pytest.mark.parametrize(
    "kind",
    [
        "literature",
        "homework",
        "packs",
        "methodical",
        "seminars",
        "lectures",
        "problems",
        "variant",
        "attempt",
        "message",
    ],
)
def test_managed_file_survives_source_removal_and_runtime_reopen(content, runtime, tmp_path, kind):
    s, _, course, offering, students = content
    source = tmp_path / "Исходник с пробелами.txt"
    source.write_text("Synthetic immutable bytes", encoding="utf-8")
    if kind == "attempt":
        assessment = s.create_assessment(offering.id, "Homework", AssessmentType.HOMEWORK)
        work = s.get_or_create_work(students[0].id, assessment.id)
        attempt = s.add_attempt(work.id, s._clock(), AttemptResult.PRESENTED)
        link = s.import_file_for_attempt(attempt.id, source)
    elif kind == "message":
        case = s.create_question_case(students[0].id, "Synthetic", s._clock())
        message = next(m for m in s._r.messages.list() if m.question_case_id == case.id)
        link = s.import_file_for_message(message.id, source)
    else:
        library_kind = (
            "seminars" if kind == "lectures" else "problems" if kind == "variant" else kind
        )
        values = dict(course_id=course.id, title="Synthetic material")
        if kind == "lectures":
            values["type"] = LessonType.LECTURE
        if kind == "variant":
            family = s.create_material("problems", **values, is_family=True)
            values.update(family_id=family.id, variant_code="A")
        material = s.create_material(library_kind, **values)
        link = s.import_file_for_material(library_kind, material.id, source)
    asset = s.get_file_asset(link.file_asset_id)
    internal = s.accessible_file_path(asset.id)
    assert internal.is_absolute() and internal != source
    assert internal.is_relative_to(tmp_path / "files")
    source.unlink()
    runtime.close()
    reopened = create_runtime(tmp_path)
    try:
        seen = []

        class Opener:
            def open(self, path):
                seen.append(path)

        reopened.service._file_opener = Opener()
        reopened.service.open_file_asset(asset.id)
        assert seen == [internal]
        assert internal.read_text("utf-8") == "Synthetic immutable bytes"
        assert reopened.service.get_file_asset(asset.id) == asset
    finally:
        reopened.close()


@pytest.mark.parametrize("kind", ["course", "group", "term", "student", "work_program"])
def test_safe_delete_keeps_library_files_and_attempt_history(content, runtime, tmp_path, kind):
    s, term, course, offering, students = content
    materials = [
        s.create_material(k, course_id=course.id, title=k)
        for k in ("homework", "problems", "seminars", "literature", "methodical", "packs")
    ]
    source = tmp_path / "material.txt"
    source.write_text("Synthetic", encoding="utf-8")
    link = s.import_file_for_material("problems", materials[1].id, source)
    assessment = s.create_assessment(offering.id, "History", AssessmentType.HOMEWORK)
    work = s.get_or_create_work(students[0].id, assessment.id)
    attempt = s.add_attempt(work.id, s._clock(), AttemptResult.ACCEPTED)
    program = s.program_for_offering(offering.id)
    original = {
        "course": course,
        "group": s._r.groups.find_by_id(offering.group_id),
        "term": term,
        "student": students[0],
        "work_program": program,
    }[kind]
    sql = []

    def record(_c, _cursor, statement, *_):
        sql.append(statement.lstrip().upper())

    event.listen(runtime._engine, "before_cursor_execute", record)
    try:
        s.safe_delete(kind, original)
    finally:
        event.remove(runtime._engine, "before_cursor_execute", record)
    assert not any(statement.startswith("DELETE") for statement in sql)
    assert s._r.attempts.find_by_id(attempt.id, include_deleted=True) == attempt
    assert s._r.works.find_by_id(work.id, include_deleted=True) == work
    for material_kind, value in zip(
        ("homework", "problems", "seminars", "literature", "methodical", "packs"), materials
    ):
        assert s.list_materials(material_kind) == (value,)
    assert s.accessible_file_path(link.file_asset_id).read_text("utf-8") == "Synthetic"


@pytest.mark.parametrize(
    "kind", ["literature", "homework", "packs", "methodical", "seminars", "problems"]
)
def test_open_saved_material_uses_its_actual_model(desktop, kind):
    window, runtime, _, offering, *_ = desktop
    material = runtime.service.create_material(kind, course_id=offering.course_id, title="Saved")
    editor = ContentEditor(window, kind, material)
    assert editor.title.text() == material.title
    editor.close()
    QThreadPool.globalInstance().waitForDone()


def test_material_from_deleted_discipline_remains_openable(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    material = s.create_material("literature", course_id=offering.course_id, title="Retained")
    course = s.get_course(offering.course_id)
    s.hide("course", course)
    editor = ContentEditor(window, "literature", material)
    assert editor.course.currentData() == course.id
    assert "удалена" in editor.course.currentText()
    editor.close()
