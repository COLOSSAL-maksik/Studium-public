"""Bounded Qt worker calls for file IO; results are delivered on the GUI thread."""

import weakref

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid


class _Worker(QRunnable):
    def __init__(self, call, action):
        super().__init__()
        self.call, self.action = call, action

    def run(self):
        try:
            result = self.action()
        except Exception as error:
            self.call.finished.emit(None, error)
        else:
            self.call.finished.emit(result, None)


class BackgroundCall(QObject):
    finished = Signal(object, object)

    def __init__(self, owner, action, success, failure):
        # Survives a closed/destroyed view until its worker has finished.
        super().__init__(QApplication.instance())
        self.owner = weakref.ref(owner)
        self.success, self.failure = success, failure
        self.finished.connect(self.complete, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(_Worker(self, action))

    @Slot(object, object)
    def complete(self, result, error):
        owner = self.owner()
        if owner is not None and isValid(owner):
            if error is None:
                self.success(result)
            else:
                self.failure(error)
        self.deleteLater()
