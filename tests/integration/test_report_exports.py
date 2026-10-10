"""CSV round trips, actual Qt PDF text/pages and read-only guarantees."""

import csv
from dataclasses import replace
from enum import StrEnum
from io import StringIO

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from sqlalchemy import event

from studium.application.report_models import Report, ReportKind, ReportTable
from studium.application.services import GradeInput
from studium.composition import create_runtime
from studium.domain import entities as e
from studium.domain.enums import AttemptResult, AttendanceStatus, GradeKind, StudentWorkStatus
from studium.domain.value_objects import EntityId, EntityMetadata, LocalDate
from studium.presentation.desktop.messages import (
    ASSESSMENT_LABELS,
    ATTEMPT_LABELS,
    ATTENDANCE_LABELS,
    ITEM_OUTCOME_LABELS,
    STATUS_LABELS,
)
from studium.presentation.desktop.report_export import (
    column_title,
    export_csv,
    export_pdf,
    report_html,
)
from studium.presentation.desktop.theme import apply_theme
from tests.integration.test_analytics import analytics_workflow as analytics_workflow
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_reporting import database_facts, section
from tests.unit.test_domain import instant


@pytest.fixture
def runtime(tmp_path):
    value = create_runtime(tmp_path / "app")
    yield value
    value.close()


def test_csv_unicode_quotes_newlines_stable_headers_and_rows(analytics_workflow, tmp_path):
    w = analytics_workflow
    title = 'Синтетическая "работа", часть\nΩ'
    w.s.update_assessment(w.assessment, title=title)
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    first, second = tmp_path / "отчёт Ω.csv", tmp_path / "повтор.csv"
    export_csv(report, "works", first)
    export_csv(report, "works", second)
    assert first.read_bytes() == second.read_bytes()
    rows = list(csv.reader(StringIO(first.read_text(encoding="utf-8-sig"), newline="")))
    assert rows[0] == [
        "Работа",
        "Тип",
        "Срок",
        "Неделя срока",
        "Текущий статус",
        "Попыток",
        "Последняя попытка",
        "Последняя оценка",
        "Попытка оценки",
        "Текущий балл",
    ]
    assert rows[1][0] == title
    assert rows[1][2] == w.assessment.due_at.value.isoformat()
    assert rows[1][5:] == ["0", "", "", "", ""]
    assert b'""' in first.read_bytes()
    assert w.s._r.file_assets.list() == []


def test_csv_keeps_recorded_numeric_precision(analytics_workflow, tmp_path):
    w = analytics_workflow
    score = 0.123456789012345
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.SCORED, score=score, max_score=10)
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    path = tmp_path / "precise.csv"
    export_csv(report, "works", path)
    rows = list(csv.reader(StringIO(path.read_text(encoding="utf-8-sig"))))
    assert float(rows[1][-1]) == score


def test_csv_empty_table_is_valid_headers_only(analytics_workflow, tmp_path):
    w = analytics_workflow
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    path = tmp_path / "empty.csv"
    export_csv(report, "attempts", path)
    rows = list(csv.reader(StringIO(path.read_text(encoding="utf-8-sig"))))
    assert rows == [["Работа", "№", "Дата", "Результат", "Оценка", "Балл", "Максимум"]]
    with pytest.raises(ValueError):
        export_csv(report, "unknown", path)


@pytest.mark.windows
def test_pdf_printed_text_keeps_contrast_when_application_theme_changes(
    qt_app, analytics_workflow, tmp_path
):
    w = analytics_workflow
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    rasters = []
    original_theme = qt_app.property("studiumTheme") or "light"
    try:
        for theme in ("light", "dark"):
            apply_theme(theme)
            path = tmp_path / f"print-{theme}.pdf"
            export_pdf(report, path)
            pdf = QPdfDocument()
            try:
                assert pdf.load(str(path)) == QPdfDocument.Error.None_
                raster = pdf.render(0, QSize(800, 600))
                # QtPdf renders transparent paper. Composite on white, as printed.
                page = QImage(raster.size(), QImage.Format.Format_RGB32)
                page.fill(0xFFFFFFFF)
                painter = QPainter(page)
                painter.drawImage(0, 0, raster)
                painter.end()
                white = QImage(page.size(), page.format())
                white.fill(0xFFFFFFFF)
                assert page != white, "Printed PDF page must contain visible text"
                rasters.append(page)
            finally:
                pdf.close()
    finally:
        apply_theme(original_theme)
    assert not rasters[0].isNull() and rasters[0] == rasters[1]


def test_pdf_unicode_path_long_strings_many_pages_and_last_row(
    qt_app, analytics_workflow, tmp_path
):
    w = analytics_workflow
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    works = section(report, "works")
    rows = tuple(
        (f"Синтетика {i:03} " + "Длинное название " * 8, *works.rows[0][1:]) for i in range(90)
    )
    report = replace(report, tables=(replace(works, rows=rows),))
    path = tmp_path / "многостраничный отчёт Ω.pdf"
    pages = export_pdf(report, path)
    assert path.read_bytes().startswith(b"%PDF-") and path.stat().st_size > 1000
    pdf = QPdfDocument()
    try:
        assert pdf.load(str(path)) == QPdfDocument.Error.None_
        assert pdf.status() == QPdfDocument.Status.Ready
        assert pdf.pageCount() == pages and pages > 1
        contents = " ".join(pdf.getAllText(i).text() for i in range(pages))
        first = pdf.getAllText(0)
        data = path.read_bytes()
        # Only structural counts are diagnostic; never log report contents.
        diagnostics = {
            "to_unicode_maps": data.count(b"/ToUnicode"),
            "embedded_fonts": data.count(b"/FontFile2"),
            "selection_valid": first.isValid(),
            "selection_bounds": len(first.bounds()),
        }
        assert "Отчёт" in contents and "Synthetic course" in contents, diagnostics
        assert "089" in contents
        assert f"{pages} / {pages}" in pdf.getAllText(pages - 1).text()
    finally:
        pdf.close()


@pytest.mark.parametrize("kind", list(ReportKind))
def test_generation_preview_csv_pdf_leave_every_record_revision_and_schema_unchanged(
    qt_app,
    runtime,
    analytics_workflow,
    tmp_path,
    caplog,
    kind,
):
    w = analytics_workflow
    attempt = w.s.add_attempt(
        w.work.id,
        instant(3),
        AttemptResult.ACCEPTED,
        score=8,
        max_score=10,
        grade=GradeInput(GradeKind.NUMERIC),
    )
    lesson = w.s.create_lesson(w.offering.id, LocalDate(2026, 9, 1), title="Synthetic lesson")
    enrollment = w.s._r.enrollments.for_offering(w.offering.id)[0]
    with w.s._transaction() as r:
        r.attendance.insert(
            e.Attendance(
                metadata=EntityMetadata.create(instant()),
                lesson_id=lesson.id,
                enrollment_id=enrollment.id,
                status=AttendanceStatus.PRESENT,
            )
        )
    source = tmp_path / "synthetic-original.txt"
    source.write_text("Synthetic attachment content must not appear in reports", encoding="utf-8")
    w.s.import_file_for_attempt(attempt.id, source)
    before = database_facts(runtime._engine)
    queries = []

    def capture(_conn, _cursor, statement, *_):
        queries.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", capture)
    try:
        report = w.s.build_report(
            kind, w.offering.id, student_id=w.student.id, assessment_id=w.assessment.id
        )
        html = report_html(report)
        assert w.student.full_name in html
        assert source.read_text(encoding="utf-8") not in html
        for table in report.tables:
            export_csv(report, table.key, tmp_path / f"{table.key}.csv")
        export_pdf(report, tmp_path / "report.pdf")
    finally:
        event.remove(runtime._engine, "before_cursor_execute", capture)
    assert queries and all(q.lstrip().upper().startswith("SELECT") for q in queries)
    assert database_facts(runtime._engine) == before
    assert w.student.full_name not in caplog.text


def test_export_io_failure_does_not_mutate_or_write_partial_file(
    qt_app, analytics_workflow, tmp_path
):
    w = analytics_workflow
    report = w.s.build_report(ReportKind.GROUP, w.offering.id)
    destination = tmp_path / "nonexistent" / "report.csv"
    with pytest.raises(OSError):
        export_csv(report, "students", destination)
    with pytest.raises(OSError):
        export_pdf(report, destination.with_suffix(".pdf"))
    assert not destination.exists()


@pytest.fixture
def synthetic_report():
    return Report(
        kind=ReportKind.GROUP,
        title="Synthetic export regression",
        offering_id=EntityId.generate(),
        generated_at=instant(),
        metadata=(),
        tables=(ReportTable("values", "Synthetic values", (("value", "Значение"),), ()),),
    )


def report_values(report, values):
    return replace(report, tables=(replace(report.tables[0], rows=tuple((v,) for v in values)),))


def csv_values(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream))


@pytest.mark.parametrize(
    ("kind", "key", "prefix", "labels", "suffix"),
    [
        (ReportKind.STUDENT, "attendance", ("ФИО", "Занятий"), ATTENDANCE_LABELS, ("Не отмечено",)),
        (ReportKind.STUDENT, "attendance_total", ("Занятий",), ATTENDANCE_LABELS, ("Не отмечено",)),
        (ReportKind.GROUP, "attendance", ("ФИО", "Занятий"), ATTENDANCE_LABELS, ("Не отмечено",)),
        (ReportKind.GROUP, "attendance_total", ("Занятий",), ATTENDANCE_LABELS, ("Не отмечено",)),
        (ReportKind.GROUP, "students", ("ФИО", "Работ", "Зачтено", "Попыток"), STATUS_LABELS, ()),
    ],
    ids=[
        "student-attendance",
        "student-total",
        "group-attendance",
        "group-total",
        "group-statuses",
    ],
)
def test_generated_enum_headers_are_localized_in_csv_html_and_pdf(
    analytics_workflow, qt_app, tmp_path, kind, key, prefix, labels, suffix
):
    w = analytics_workflow
    report = w.s.build_report(kind, w.offering.id, student_id=w.student.id)
    expected = [*prefix, *labels.values(), *suffix]
    csv_path = tmp_path / "localized-headers.csv"
    export_csv(report, key, csv_path)
    assert csv_values(csv_path)[0] == expected

    table = section(report, key)
    enum_type = AttendanceStatus if key != "students" else StudentWorkStatus
    status_columns = table.columns[len(prefix) : len(prefix) + len(labels)]
    assert all(type(title) is enum_type for _, title in status_columns)
    assert [key for key, _ in status_columns] == [status.value.lower() for status in labels]

    # Use a neutral body row so localized cell values cannot hide a broken title.
    header_report = replace(
        report, metadata=(), tables=(replace(table, rows=((None,) * len(table.columns),)),)
    )
    html = report_html(header_report)
    assert all(f">{label}</th>" in html for label in expected)
    assert all(status.value not in html for status in labels)
    pdf_path = tmp_path / "localized-headers.pdf"
    export_pdf(header_report, pdf_path)
    pdf = QPdfDocument()
    try:
        assert pdf.load(str(pdf_path)) == QPdfDocument.Error.None_
        text = "".join(
            "".join(pdf.getAllText(page).text() for page in range(pdf.pageCount())).split()
        )
        # QtPdf may separate glyphs and omit decorative status symbols.
        assert all("".join(label.lstrip("—○⚠✓ ").split()) in text for label in expected)
        assert all(status.value not in text for status in labels)
    finally:
        pdf.close()


def test_csv_formula_injection_controls_and_text_grade_keep_real_numbers(
    synthetic_report, tmp_path
):
    prefixes = (
        "",
        " ",
        "\t",
        "\r",
        "\n",
        "\r\n",
        "\x00",
        "\x01",
        "\x1f",
        "\x7f",
        "\x85",
        "\xa0",
        "\u200b",
        "\ufeff",
        " \t\r\n\x01\u200b",
    )
    malicious = [f"{prefix}{trigger}SUM(1,2)" for prefix in prefixes for trigger in "=+-@"]
    malicious.extend(("-7", "-0.123456789012345", " +42", "\t-42"))
    grades = [
        e.Grade.traditional(
            metadata=EntityMetadata.create(instant()), attempt_id=EntityId.generate(), label=value
        )
        for value in malicious
    ]
    ordinary = ["Синтетический текст", "  literal", "first\nsecond", "1+2", "'already text"]
    numbers = [-7, -0.123456789012345, 0, 1.23456789012345]
    report = report_values(synthetic_report, [*malicious, *grades, *ordinary, *numbers])
    report = replace(
        report, tables=(replace(report.tables[0], columns=(("value", "\t=SUM(1,2)"),)),)
    )
    destination = tmp_path / "safe-text.csv"
    export_csv(report, "values", destination)
    rows = csv_values(destination)
    assert rows[0] == ["'\t=SUM(1,2)"]
    assert [row[0] for row in rows[1:]] == [
        *("'" + value for value in malicious),
        *("'" + value for value in malicious),
        *ordinary,
        *(str(value) for value in numbers),
    ]


@pytest.mark.parametrize("maximum", [None, 10.98765432109876])
def test_csv_numeric_grade_and_maximum_round_trip_without_display_rounding(
    runtime, analytics_workflow, tmp_path, maximum
):
    w = analytics_workflow
    score = 0.123456789012345
    w.s.add_attempt(
        w.work.id,
        instant(3),
        AttemptResult.SCORED,
        score=score,
        max_score=maximum,
        grade=GradeInput(GradeKind.NUMERIC),
    )
    before = database_facts(runtime._engine)
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    grade = section(report, "works").rows[0][7]
    assert grade.score == score and grade.max_score == maximum
    expected = str(score) if maximum is None else f"{score} / {maximum}"
    for key, index in (("works", 7), ("attempts", 4)):
        destination = tmp_path / f"precise-grade-{key}.csv"
        export_csv(report, key, destination)
        assert csv_values(destination)[1][index] == expected
    assert grade.score == score and grade.max_score == maximum
    assert database_facts(runtime._engine) == before


def test_csv_pdf_localize_only_supported_enum_types_and_keep_colliding_text(
    qt_app, synthetic_report, tmp_path
):
    class Unlocalized(StrEnum):
        ACCEPTED = "ACCEPTED"

    cases = [
        pair
        for labels in (
            ASSESSMENT_LABELS,
            ATTEMPT_LABELS,
            ATTENDANCE_LABELS,
            ITEM_OUTCOME_LABELS,
            STATUS_LABELS,
        )
        for pair in labels.items()
    ]
    values, expected = [], []
    for value, label in cases:
        assert column_title(value) == label
        assert column_title(value.value) == value.value
        text_grade = e.Grade.traditional(
            metadata=EntityMetadata.create(instant()),
            attempt_id=EntityId.generate(),
            label=value.value,
        )
        values.extend((value.value, value, text_grade))
        expected.extend((value.value, label, value.value))
    values.append(Unlocalized.ACCEPTED)
    expected.append("ACCEPTED")
    report = report_values(synthetic_report, values)
    report = replace(
        report,
        metadata=(("Synthetic name", "ACCEPTED"),),
        tables=(replace(report.tables[0], columns=(("value", "ACCEPTED"),)),),
    )
    csv_path, pdf_path = tmp_path / "literal.csv", tmp_path / "literal.pdf"
    export_csv(report, "values", csv_path)
    assert csv_values(csv_path) == [["ACCEPTED"], *[[value] for value in expected]]
    html = report_html(report)
    for value in expected:
        assert f"<td>{value}</td>" in html
    assert '<th width="100%">ACCEPTED</th>' in html
    assert "<b>Synthetic name:</b> ACCEPTED" in html
    export_pdf(report, pdf_path)
    pdf = QPdfDocument()
    try:
        assert pdf.load(str(pdf_path)) == QPdfDocument.Error.None_
        # QtPdf can insert separators between positioned glyphs on some pages.
        text = "".join(
            "".join(pdf.getAllText(page).text() for page in range(pdf.pageCount())).split()
        )
        # Decorative status symbols have platform-dependent PDF text mapping.
        assert all("".join(value.lstrip("—○⚠✓ ").split()) in text for value in expected)
    finally:
        pdf.close()


def link_or_skip(path, target, *, directory=False):
    try:
        path.symlink_to(target, target_is_directory=directory)
    except (NotImplementedError, OSError):
        pytest.skip("Symlinks unavailable on this host")


def tree_contents(root):
    return {
        str(path.relative_to(root)): path.readlink()
        if path.is_symlink()
        else path.read_bytes()
        if path.is_file()
        else None
        for path in root.rglob("*")
    }


@pytest.mark.parametrize("format", ["csv", "pdf"])
@pytest.mark.parametrize("marker", ["directory", "file"])
@pytest.mark.parametrize(
    "case",
    [
        "nested-new",
        "nested-existing",
        "missing-parent",
        "directory-link-in",
        "file-link-in",
        "dangling-file-link-in",
        "directory-link-out",
        "alias-file-link-out",
    ],
)
def test_export_rejects_git_working_trees_before_creating_any_artifact(
    qt_app, synthetic_report, tmp_path, format, marker, case
):
    checkout, ordinary = tmp_path / "checkout", tmp_path / "ordinary"
    checkout.mkdir()
    ordinary.mkdir()
    if marker == "directory":
        (checkout / ".git").mkdir()
    else:
        (checkout / ".git").write_text(
            "gitdir: ../synthetic-main/.git/worktrees/synthetic\n", encoding="utf-8"
        )
    nested = checkout / "nested" / "reports"
    nested.mkdir(parents=True)
    destination = nested / f"report.{format}"
    if case in ("nested-existing", "file-link-in"):
        destination.write_bytes(b"Existing synthetic file must survive")
    if case == "missing-parent":
        destination = nested / "not-created" / f"report.{format}"
    elif case == "directory-link-in":
        link_or_skip(ordinary / "link", nested, directory=True)
        destination = ordinary / "link" / f"report.{format}"
    elif case in ("file-link-in", "dangling-file-link-in"):
        link_or_skip(ordinary / f"link.{format}", destination)
        destination = ordinary / f"link.{format}"
    elif case == "directory-link-out":
        link_or_skip(nested / "link", ordinary, directory=True)
        destination = nested / "link" / f"report.{format}"
    elif case == "alias-file-link-out":
        link_or_skip(ordinary / "alias", nested, directory=True)
        link_or_skip(nested / f"link.{format}", ordinary / f"report.{format}")
        destination = ordinary / "alias" / f"link.{format}"
    before = tree_contents(tmp_path)
    with pytest.raises(ValueError, match="Git"):
        if format == "csv":
            export_csv(synthetic_report, "values", destination)
        else:
            export_pdf(synthetic_report, destination)
    assert tree_contents(tmp_path) == before


@pytest.mark.parametrize("format", ["csv", "pdf"])
@pytest.mark.parametrize("root_type", ["default", "override"])
@pytest.mark.parametrize(
    "case",
    [
        "new",
        "existing",
        "directory-link",
        "file-link",
        "dangling-file-link",
        "directory-link-out",
        "alias-file-link-out",
    ],
)
def test_export_rejects_managed_data_directory_without_artifacts(
    qt_app, synthetic_report, tmp_path, monkeypatch, format, root_type, case
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    root = tmp_path / ("Studium" if root_type == "default" else "custom-app")
    options = {} if root_type == "default" else {"data_directory": root}
    managed = root / "nested"
    managed.mkdir(parents=True)
    destination = managed / f"report.{format}"
    if case in ("existing", "file-link"):
        destination.write_bytes(b"Existing synthetic managed file")
    if case == "directory-link":
        link_or_skip(tmp_path / "alias", managed, directory=True)
        destination = tmp_path / "alias" / f"report.{format}"
    elif case in ("file-link", "dangling-file-link"):
        link_or_skip(tmp_path / f"alias.{format}", destination)
        destination = tmp_path / f"alias.{format}"
    elif case == "directory-link-out":
        link_or_skip(managed / "link", tmp_path, directory=True)
        destination = managed / "link" / f"report.{format}"
    elif case == "alias-file-link-out":
        link_or_skip(tmp_path / "alias", managed, directory=True)
        link_or_skip(managed / f"link.{format}", tmp_path / f"report.{format}")
        destination = tmp_path / "alias" / f"link.{format}"
    before = tree_contents(tmp_path)
    with pytest.raises(ValueError, match="вне хранилища Studium"):
        if format == "csv":
            export_csv(synthetic_report, "values", destination, **options)
        else:
            export_pdf(synthetic_report, destination, **options)
    assert tree_contents(tmp_path) == before


@pytest.mark.parametrize("format", ["csv", "pdf"])
@pytest.mark.parametrize("linked", [False, True])
def test_export_allows_ordinary_directories_outside_git_and_managed_storage(
    qt_app, synthetic_report, tmp_path, monkeypatch, format, linked
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ordinary = tmp_path / "Studium-reports"
    ordinary.mkdir()
    if linked:
        link_or_skip(tmp_path / "ordinary-alias", ordinary, directory=True)
        directory = tmp_path / "ordinary-alias"
    else:
        directory = ordinary
    destination = directory / f"report.{format}"
    destination.write_bytes(b"Synthetic previous export")
    if format == "csv":
        export_csv(synthetic_report, "values", destination)
        assert csv_values(destination) == [["Значение"]]
    else:
        export_pdf(synthetic_report, destination)
        assert destination.read_bytes().startswith(b"%PDF-")
    assert {path.name for path in ordinary.iterdir()} == {destination.name}
