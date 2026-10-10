"""Read-only Qt table models over application query results."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from studium.domain.enums import StudentWorkStatus
from studium.presentation.desktop.messages import (
    ATTEMPT_LABELS,
    ENROLLMENT_LABELS,
    STATUS_LABELS,
    TEXT,
)


def display_time(value):
    return value.value.astimezone().strftime("%d.%m.%Y %H:%M") if value else "—"


def display_score(score, maximum=None):
    if score is None:
        return "—"
    number = f"{score:g}".replace(".", ",")
    return number if maximum is None else f"{number} / {maximum:g}".replace(".", ",")


def display_grade(grade):
    if grade is None:
        return "—"
    if grade.passed is not None:
        return TEXT["pass"] if grade.passed else TEXT["fail"]
    if grade.label is not None:
        return grade.label
    return display_score(grade.score, grade.max_score)


def progress_text(progress):
    if progress is None:
        return STATUS_LABELS[StudentWorkStatus.NOT_STARTED]
    return STATUS_LABELS[progress.status]


class TableModel(QAbstractTableModel):
    def __init__(self, columns, rows=(), parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows = list(rows)

    def replace_rows(self, rows):
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole)
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.columns[section][0]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return row
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return str(self.columns[index.column()][1](row))
        return None


class StudentTableModel(TableModel):
    def __init__(self, rows=(), parent=None):
        super().__init__(
            [
                (TEXT["full_name"], lambda r: r.student.full_name),
                (TEXT["notes"], lambda r: " ".join(r.student.notes.splitlines())),
                (TEXT["enrollment"], lambda r: ENROLLMENT_LABELS[r.enrollment.status]),
            ],
            rows,
            parent,
        )


class AttemptHistoryModel(TableModel):
    def __init__(self, rows=(), parent=None):
        super().__init__(
            [
                (TEXT["attempt_number"], lambda r: r.attempt.attempt_no),
                (TEXT["occurred_at"], lambda r: display_time(r.attempt.occurred_at)),
                (TEXT["result"], lambda r: ATTEMPT_LABELS[r.attempt.result]),
                (TEXT["comment"], lambda r: r.attempt.comment),
                (TEXT["score"], lambda r: display_score(r.attempt.score, r.attempt.max_score)),
                (TEXT["grade"], lambda r: display_grade(r.grade)),
            ],
            rows,
            parent,
        )


class MatrixModel(QAbstractTableModel):
    def __init__(self, matrix=None, parent=None):
        super().__init__(parent)
        self.matrix = matrix

    def replace_matrix(self, matrix):
        self.beginResetModel()
        self.matrix = matrix
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.matrix.roster) if self.matrix and not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.matrix.assessments) + 1 if self.matrix and not parent.isValid() else 0

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if self.matrix and orientation == Qt.Orientation.Horizontal:
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
                return (
                    TEXT["full_name"]
                    if section == 0
                    else self.matrix.assessments[section - 1].title
                )
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.matrix is None:
            return None
        entry = self.matrix.roster[index.row()]
        if index.column() == 0:
            return (
                entry.student.full_name
                if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole)
                else None
            )
        assessment = self.matrix.assessments[index.column() - 1]
        cell = self.matrix.cells[entry.student.id, assessment.id]
        progress = cell.progress
        if role == Qt.ItemDataRole.UserRole:
            return cell
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            count = progress.attempt_count if progress else 0
            return f"{entry.student.full_name}\n{assessment.title}\n{progress_text(progress)} · {TEXT['attempts']}: {count}"
        if role == Qt.ItemDataRole.ForegroundRole:
            status = progress.status if progress else StudentWorkStatus.NOT_STARTED
            return QColor(
                {
                    StudentWorkStatus.ACCEPTED: "#24684f",
                    StudentWorkStatus.REVISION_REQUIRED: "#8a641f",
                }.get(status, "#526177")
            )
        if role == Qt.ItemDataRole.DisplayRole:
            status = progress.status if progress else StudentWorkStatus.NOT_STARTED
            if status == StudentWorkStatus.ACCEPTED:
                suffix = (
                    str(progress.attempt_count).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
                    if progress.attempt_count > 1
                    else ""
                )
                return "✓" + suffix
            return {
                StudentWorkStatus.NOT_STARTED: "—",
                StudentWorkStatus.SUBMITTED: "○",
                StudentWorkStatus.REVISION_REQUIRED: "⚠",
            }.get(status, STATUS_LABELS[status])
        return None
