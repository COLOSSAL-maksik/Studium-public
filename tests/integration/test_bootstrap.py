import os
import subprocess
import sys


def test_qapplication_mainwindow_and_event_loop_start(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", LOCALAPPDATA=str(tmp_path))
    code = """
import runpy
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from studium.presentation.desktop import bootstrap

original_init = bootstrap.MainWindow.__init__
def checked_init(self):
    original_init(self)
    assert self.windowTitle() == 'Studium'
    assert QApplication.instance().applicationName() == 'Studium'
    QTimer.singleShot(100, QApplication.instance().quit)

bootstrap.MainWindow.__init__ = checked_init
sys.argv = ['studium']
runpy.run_module('studium', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "Studium" / "studium.sqlite").exists()
