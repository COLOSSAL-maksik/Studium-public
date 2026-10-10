"""Period management next to the current teaching context."""

from PySide6.QtWidgets import QDialog, QVBoxLayout

from studium.presentation.desktop.components import (
    confirm_delete,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import TermDialog
from studium.presentation.desktop.models import TableModel


class PeriodManager(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Учебные периоды")
        self.resize(720, 440)
        layout = QVBoxLayout(self)
        toolbar(
            layout,
            [
                ("Добавить", lambda: run_action(self, lambda: self.edit(new=True))),
                ("Изменить", lambda: run_action(self, self.edit)),
                ("Удалить", lambda: run_action(self, self.delete)),
            ],
        )
        self.model = TableModel(
            [
                ("Период", lambda t: t.name),
                ("Начало", lambda t: str(t.starts_on)),
                ("Окончание", lambda t: str(t.ends_on)),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.edit))
        self.refresh()

    def refresh(self):
        self.model.replace_rows(self.window.service.list_terms())

    def edit(self, *, new=False):
        original = None if new else selected(self.view)
        if not new and original is None:
            return
        service = self.window.service
        save = (
            (lambda values: service.update_term(original, **values))
            if original
            else (lambda values: service.create_term(**values))
        )
        if TermDialog(save, original=original, parent=self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.window.refresh()

    def delete(self):
        original = selected(self.view)
        if original and confirm_delete(self, self.window.service, "term", original):
            self.window.service.safe_delete("term", original)
            self.refresh()
            self.window.refresh()
