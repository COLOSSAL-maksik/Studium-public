"""Run the actual python -m studium entry point with isolated data and a bounded event loop."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import inspect

from studium.infrastructure.database.session import create_database_engine


def main():
    if os.name != "nt":
        raise RuntimeError("This smoke check requires native Windows Qt")
    with TemporaryDirectory(prefix="studium-native-smoke-") as directory:
        root = Path(directory)
        # Test-only hook leaves the production entry point and event loop intact.
        # Quit after verifying the real visible native window, never another process.
        (root / "sitecustomize.py").write_text(
            """from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
original_exec = QApplication.exec
def smoke_exec(self):
    def verify():
        try:
            assert QApplication.platformName() == 'windows'
            windows = [w for w in self.topLevelWidgets() if w.windowTitle() == 'Studium']
            assert len(windows) == 1 and windows[0].isVisible()
            assert windows[0].windowHandle().isVisible()
            print('NATIVE_WINDOW_VERIFIED', flush=True)
            windows[0].close()
            self.quit()
        except Exception as error:
            print('NATIVE_SMOKE_FAILED', type(error).__name__, flush=True)
            self.exit(1)
    QTimer.singleShot(1200, verify)
    return original_exec()
QApplication.exec = smoke_exec
""",
            encoding="utf-8",
        )
        env = dict(os.environ, LOCALAPPDATA=str(root / "profile"), QT_QPA_PLATFORM="windows")
        env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-m", "studium"], env=env, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 or "NATIVE_WINDOW_VERIFIED" not in result.stdout:
            raise RuntimeError(
                f"Native launch failed: {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
        engine = create_database_engine(root / "profile" / "Studium" / "studium.sqlite")
        try:
            with engine.connect() as c:
                revision = c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                assert revision == "0006_content_workflow"
                assert len(inspect(c).get_table_names()) == 48
                assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        finally:
            engine.dispose()
        print(
            f"python -m studium: native visible window, exit 0; {revision}; 47 user tables; FK PASS; temporary data only"
        )


if __name__ == "__main__":
    main()
