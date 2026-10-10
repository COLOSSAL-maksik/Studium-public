"""Portable CSV and paginated Qt PDF from the same immutable preview model."""

import csv
from html import escape
from io import StringIO
from pathlib import Path
from unicodedata import category

from PySide6.QtCore import QIODevice, QRectF, QSaveFile, QSizeF, Qt
from PySide6.QtGui import (
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextDocument,
    QTextOption,
)

from studium.application.errors import ApplicationError
from studium.domain.entities import Grade
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    GradeKind,
    ItemOutcome,
    StudentWorkStatus,
)
from studium.domain.value_objects import UtcInstant
from studium.infrastructure.user_data import data_directory as default_data_directory
from studium.infrastructure.user_data import ensure_outside_repository
from studium.presentation.desktop.messages import (
    ASSESSMENT_LABELS,
    ATTEMPT_LABELS,
    ATTENDANCE_LABELS,
    ITEM_OUTCOME_LABELS,
    STATUS_LABELS,
)
from studium.presentation.desktop.models import display_grade, display_time

ENUM_LABELS = (
    (AssessmentType, ASSESSMENT_LABELS),
    (AttemptResult, ATTEMPT_LABELS),
    (AttendanceStatus, ATTENDANCE_LABELS),
    (ItemOutcome, ITEM_OUTCOME_LABELS),
    (StudentWorkStatus, STATUS_LABELS),
)


def column_title(title):
    return display_cell(title)


def display_cell(value):
    if value is None:
        return "—"
    if isinstance(value, UtcInstant):
        return display_time(value)
    if isinstance(value, Grade):
        return display_grade(value)
    if isinstance(value, float):
        return f"{value:g}"
    for enum_type, labels in ENUM_LABELS:
        if isinstance(value, enum_type):
            return labels[value]
    return str(value)


def _csv_text(value):
    """Force potentially executable spreadsheet text to stay a literal cell."""
    for character in value:
        if character.isspace() or category(character) in {"Cc", "Cf"}:
            continue
        return "'" + value if character in "=+-@" else value
    return value


def csv_cell(value):
    """Recorded numeric precision; formula protection applies only to text."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, UtcInstant):
        return value.value.isoformat()
    if isinstance(value, Grade) and value.kind == GradeKind.NUMERIC:
        score = str(value.score)
        return score if value.max_score is None else f"{score} / {value.max_score}"
    return _csv_text(display_cell(value))


def validate_export_destination(path, *, data_directory=None):
    """Reject unsafe destinations before any atomic-output temporary file is opened."""
    destination = Path(path).expanduser().absolute()
    managed = default_data_directory() if data_directory is None else Path(data_directory)
    root = managed.expanduser().resolve()
    if any(
        candidate.is_relative_to(root)
        for ancestor in (destination, *destination.parents)
        for candidate in (ancestor, ancestor.resolve())
    ):
        raise ValueError("Выберите папку вне хранилища Studium.")
    try:
        ensure_outside_repository(destination)
    except ApplicationError:
        raise ValueError("Выберите папку вне Git-репозитория и его рабочих деревьев.") from None
    return destination


def _output(path, *, data_directory=None):
    path = validate_export_destination(path, data_directory=data_directory)
    output = QSaveFile(str(path))
    if not output.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Cannot open report destination")
    return output


def export_csv(report, table_key, path, *, data_directory=None):
    section = next((t for t in report.tables if t.key == table_key), None)
    if section is None:
        raise ValueError("Unknown report table")
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(csv_cell(title) for _, title in section.columns)
    writer.writerows([csv_cell(cell) for cell in row] for row in section.rows)
    # BOM makes UTF-8 Cyrillic portable to common Windows spreadsheet applications.
    payload = stream.getvalue().encode("utf-8-sig")
    output = _output(path, data_directory=data_directory)
    if output.write(payload) != len(payload) or not output.commit():
        output.cancelWriting()
        raise OSError("Cannot save CSV report")


def report_html(report):
    def text(value):
        return escape(display_cell(value)).replace("\n", "<br>")

    parts = [
        "<html><head><style>body { font-size: 9pt; color: #1c304a; }"
        "h1 { font-size: 18pt; } h2 { font-size: 12pt; }"
        "td, th { padding: 4px; } th { background-color: #eef2f6; }"
        "</style></head><body>",
        f"<h1>{escape(report.title)}</h1>",
        f"<p>Сформирован: {text(report.generated_at)}</p>",
    ]
    parts.extend(
        f"<p><b>{escape(label)}:</b> {text(value)}</p>" for label, value in report.metadata
    )
    for section in report.tables:
        parts.append(f"<h2>{escape(section.title)}</h2>")
        if not section.rows:
            parts.append("<p>Нет данных</p>")
            continue
        parts.append('<table border="1" cellspacing="0" width="100%"><thead><tr>')
        width = 100 / len(section.columns)
        parts.extend(
            f'<th width="{width:g}%">{escape(column_title(title))}</th>'
            for _, title in section.columns
        )
        parts.append("</tr></thead><tbody>")
        for row in section.rows:
            parts.append("<tr>" + "".join(f"<td>{text(cell)}</td>" for cell in row) + "</tr>")
        parts.append("</tbody></table>")
    return "".join(parts) + "</body></html>"


def export_pdf(report, path, *, data_directory=None):
    """Landscape A4, repeated table headers, Unicode fonts and page footers."""
    output = _output(Path(path), data_directory=data_directory)
    writer = QPdfWriter(output)
    writer.setTitle(report.title)
    writer.setCreator("Studium")
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    font = QFont("Arial", 9)
    font.setStyleStrategy(QFont.StyleStrategy.PreferOutline)
    document = QTextDocument()
    document.documentLayout().setPaintDevice(writer)
    document.setDefaultFont(font)
    option = document.defaultTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    document.setDefaultTextOption(option)
    content_height = writer.height() - 28
    document.setPageSize(QSizeF(writer.width(), content_height))
    document.setHtml(report_html(report))
    pages = document.pageCount()
    painter = QPainter()
    try:
        if not painter.begin(writer):
            raise OSError("Cannot start PDF export")
        painter.setFont(font)
        for page in range(pages):
            if page and not writer.newPage():
                raise OSError("Cannot create PDF page")
            painter.save()
            painter.setClipRect(QRectF(0, 0, writer.width(), content_height))
            painter.translate(0, -page * content_height)
            document.drawContents(
                painter, QRectF(0, page * content_height, writer.width(), content_height)
            )
            painter.restore()
            painter.drawText(
                QRectF(0, content_height + 5, writer.width(), 22),
                Qt.AlignmentFlag.AlignRight,
                f"{page + 1} / {pages}",
            )
    except Exception:
        output.cancelWriting()
        raise
    finally:
        if painter.isActive():
            painter.end()
        # The layout's paint device must outlive the document.
        del document
        # Finalize the PDF trailer before committing the atomic output file.
        del writer
    if not output.commit():
        raise OSError("Cannot save PDF report")
    return pages
