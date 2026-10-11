"""Bounded Qt worker calls for file IO; results are delivered on the GUI thread."""

import gc
import weakref

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

_gc_timer = None


def _gui_collection():
    """Qt wrapper cycles must be collected on the application thread."""
    global _gc_timer
    app = QApplication.instance()
    if QThread.currentThread() != app.thread():
        raise RuntimeError("BackgroundCall must be started from the GUI thread")
    if _gc_timer is not None and isValid(_gc_timer):
        return
    enabled = gc.isenabled()
    gc.disable()
    gc.collect()
    _gc_timer = QTimer(app)
    _gc_timer.setInterval(3000)
    _gc_timer.timeout.connect(gc.collect)
    _gc_timer.start()

    def restore():
        QThreadPool.globalInstance().waitForDone()
        _gc_timer.stop()
        gc.collect()
        if enabled:
            gc.enable()

    app.aboutToQuit.connect(restore)


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
        _gui_collection()
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
