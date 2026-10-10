"""Compact entry of a new fact, reusing the validated Attempt form contract."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QToolButton, QWidget

from studium.domain.enums import AttemptResult
from studium.presentation.desktop.dialogs import AttemptDialog
from studium.presentation.desktop.messages import TEXT


class QuickAttemptDialog(AttemptDialog):
    def __init__(self, service, student, assessment, parent=None):
        super().__init__(
            lambda values: service.record_attempt(student.id, assessment.id, **values),
            assessment.max_score,
            parent,
            assessment_type=assessment.type,
        )
        self.setWindowTitle(TEXT["quick_attempt"])
        self.setMinimumWidth(520)
        self.context_label = QLabel(f"{student.full_name}\n{assessment.title}")
        self.context_label.setTextFormat(Qt.TextFormat.PlainText)
        self.context_label.setWordWrap(True)
        self.context_label.setProperty("role", "subheading")
        self.body_layout.insertWidget(0, self.context_label)
        # Keep the same validators/Grade semantics; only move optional controls.
        self.optional = QWidget()
        optional_form = QFormLayout(self.optional)
        while self.form.rowCount() > 3:
            row = self.form.takeRow(3)
            optional_form.addRow(row.labelItem.widget(), row.fieldItem.widget())
        for result in (AttemptResult.SCORED, AttemptResult.COMMENT_ONLY):
            self.result_combo.removeItem(self.result_combo.findData(result))
        self.details_button = QToolButton()
        self.details_button.setText(TEXT["optional_grade"])
        self.details_button.setCheckable(True)
        self.details_button.toggled.connect(self.show_optional)
        self.body_layout.insertWidget(2, self.details_button)
        self.body_layout.insertWidget(3, self.optional)
        self.optional.hide()
        for label in self.findChildren(QLabel):
            if label.text() in (TEXT["history_hint"], TEXT["progress_hint"], TEXT["local_time"]):
                label.hide()
        self.result_combo.setToolTip(TEXT["progress_hint"])
        self.occurred.setToolTip(TEXT["local_time"])
        self.save_button.setDefault(True)
        self.save_button.setAutoDefault(True)
        self.save_button.setProperty("primary", True)
        self.setTabOrder(self.occurred, self.result_combo)
        self.setTabOrder(self.result_combo, self.comment)
        self.setTabOrder(self.comment, self.details_button)
        self.setTabOrder(self.details_button, self.score)
        self.setTabOrder(self.label, self.save_button)
        self.result_combo.setFocus()

    def show_optional(self, shown):
        self.optional.setVisible(shown)
        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        self.result_combo.setFocus()
