import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from studium.composition import create_runtime
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.messages import TEXT, error_message


def main() -> int:
    parser = argparse.ArgumentParser(description="Studium desktop")
    parser.add_argument("--data-dir", type=Path, help="Explicit development/test data directory")
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setApplicationName(TEXT["app"])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    runtime = None
    try:
        runtime = create_runtime(args.data_dir)
        window = MainWindow()
        window.initialize(runtime.service, runtime.diagnostics)
        window.show()
        return app.exec()
    except Exception as error:
        logging.getLogger(__name__).error("Startup failed (%s)", type(error).__name__)
        QMessageBox.critical(
            None, TEXT["error_title"], TEXT["startup_error"] + "\n" + error_message(error)
        )
        return 1
    finally:
        QThreadPool.globalInstance().waitForDone()
        if runtime:
            runtime.close()
