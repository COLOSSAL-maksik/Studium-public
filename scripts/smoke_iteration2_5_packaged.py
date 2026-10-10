"""Exercise the actual frozen exe via Windows UIA, using only a temporary profile."""

import argparse
import json
import os
import stat
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from iteration2_scenario import seed
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from sqlalchemy import inspect

from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences

# This administrative smoke runs from the checkout, never from the frozen app.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.legacy_schema import HistoricalStudiumService as StudiumService
from tests.legacy_schema import repository_set, transaction_factory


def historical_profile(directory):
    directory.mkdir(parents=True)
    engine = create_database_engine(directory / "studium.sqlite", wal=False)
    try:
        with engine.begin() as connection:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "0006_content_workflow")
        sessions = create_session_factory(engine)
        service = StudiumService(
            repository_set(sessions),
            transaction_factory(sessions),
            JsonPreferences(directory / "preferences.json"),
            file_storage=LocalFileStorage(directory),
        )
        term = service.create_term("Legacy synthetic", LocalDate(2026, 9, 1), LocalDate(2027, 1, 1))
        course = service.create_course("Legacy synthetic course")
        group = service.create_group("LEGACY-TEST")
        offering = service.create_offering(term.id, course.id, group.id)
        student = service.create_student(offering.id, "Synthetic Student")
        assessment = service.create_assessment(
            offering.id,
            "Legacy exact deadline",
            AssessmentType.HOMEWORK,
            due_at=UtcInstant(UtcInstant.now().value + timedelta(days=1)),
        )
        attempt = service.record_attempt(
            student.id, assessment.id, occurred_at=UtcInstant.now(), result=AttemptResult.ACCEPTED
        )
        source = directory / "synthetic.txt"
        source.write_text("Synthetic immutable legacy bytes", encoding="utf8")
        link = service.import_file_for_attempt(attempt.id, source)
        file_path = service.accessible_file_path(link.file_asset_id)
        lesson = service.create_lesson(offering.id, LocalDate(2026, 9, 1))
        enrollment = service.list_students_for_offering(offering.id)[0].enrollment
        service.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.PRESENT)
        service.create_question_case(
            student.id, "Synthetic question", UtcInstant.now(), course_offering_id=offering.id
        )
        before = {}
        with engine.connect() as connection:
            for table in inspect(connection).get_table_names():
                if table != "alembic_version":
                    before[table] = connection.exec_driver_sql(
                        f'SELECT * FROM "{table}" ORDER BY id'
                    ).fetchall()
        return before, file_path
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots/iteration2_5"))
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("Native Windows only")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication([])
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts" / name))
    project = Path(__file__).resolve().parents[1]
    output_root = (project / args.output).resolve()
    capture_root = output_root / "packaged"
    capture_root.mkdir(parents=True, exist_ok=True)
    exe = project / "dist" / "Studium" / "Studium.exe"
    if not exe.is_file():
        raise RuntimeError("Build dist/Studium first")
    report = {
        "exe_bytes": exe.stat().st_size,
        "bundle_bytes": sum(p.stat().st_size for p in exe.parent.rglob("*") if p.is_file()),
        "runs": [],
    }
    with TemporaryDirectory(prefix="studium-packaged2-") as temp:
        root = Path(temp)
        profile = root / "profile"
        data_root = profile / "Studium"
        runtime = create_runtime(data_root)
        data = seed(runtime.service, data_root)
        runtime.close()
        engine = create_database_engine(data_root / "studium.sqlite", wal=False)
        with engine.connect() as connection:
            before_v7_schema = connection.exec_driver_sql(
                "SELECT type,name,sql FROM sqlite_master ORDER BY type,name"
            ).fetchall()
            before_v7 = {
                name: connection.exec_driver_sql(f'SELECT * FROM "{name}" ORDER BY id').fetchall()
                for name in inspect(connection).get_table_names()
                if name != "alembic_version"
            }
        engine.dispose()
        legacy_root = root / "legacy-profile" / "Studium"
        old_rows, legacy_file = historical_profile(legacy_root)
        old_file_bytes = legacy_file.read_bytes()
        env = dict(
            os.environ, LOCALAPPDATA=str(profile), QT_QPA_PLATFORM="windows", QT_SCALE_FACTOR="0.5"
        )
        env["PATH"] = (
            str(Path(os.environ["WINDIR"]) / "System32") + os.pathsep + os.environ["WINDIR"]
        )
        env.pop("PYTHONPATH", None)
        for mode in ("fresh", "migration", "workflow", "reopen"):
            env["LOCALAPPDATA"] = str(
                root / "fresh-profile"
                if mode == "fresh"
                else legacy_root.parent
                if mode == "migration"
                else profile
            )
            process = subprocess.Popen([str(exe)], env=env, cwd=root)
            try:
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(project / "scripts" / "smoke_iteration2_5_packaged.ps1"),
                        "-OwnProcessId",
                        str(process.pid),
                        "-Mode",
                        mode,
                        "-DropImage",
                        str(data.image),
                        "-DropPdf",
                        str(data.pdf),
                        "-OutputRoot",
                        str(capture_root),
                    ],
                    capture_output=True,
                    encoding="utf8",
                    errors="replace",
                    timeout=120,
                )
                (project / "tmp" / f"iteration2_5-packaged-{mode}.txt").write_text(
                    result.stdout + result.stderr, encoding="utf8"
                )
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                process.wait(timeout=10)
                assert process.returncode == 0
                report["runs"].append(
                    {"mode": mode, "exit": process.returncode, "checks": result.stdout.strip()}
                )
            finally:
                if process.poll() is None:
                    subprocess.run(
                        ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                    process.wait(timeout=10)
            if mode in {"fresh", "migration"}:
                actual_root = root / "fresh-profile" / "Studium" if mode == "fresh" else legacy_root
                engine = create_database_engine(actual_root / "studium.sqlite", wal=False)
                try:
                    with engine.connect() as connection:
                        assert (
                            connection.exec_driver_sql(
                                "SELECT version_num FROM alembic_version"
                            ).scalar_one()
                            == "0007_work_programs"
                        )
                        assert len(inspect(connection).get_table_names()) == 78
                        assert (
                            connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
                        )
                        if mode == "migration":
                            from tests.legacy_schema import preserved_rows

                            after = {
                                table: connection.exec_driver_sql(
                                    f'SELECT * FROM "{table}" ORDER BY id'
                                ).fetchall()
                                for table in old_rows
                            }
                            assert preserved_rows(old_rows, after)
                            assert legacy_file.read_bytes() == old_file_bytes
                finally:
                    engine.dispose()
        engine = create_database_engine(data_root / "studium.sqlite", wal=False)
        try:
            with engine.connect() as connection:
                assert (
                    connection.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    ).scalar_one()
                    == "0007_work_programs"
                )
                assert len(inspect(connection).get_table_names()) == 78
                assert (
                    connection.exec_driver_sql(
                        "SELECT type,name,sql FROM sqlite_master ORDER BY type,name"
                    ).fetchall()
                    == before_v7_schema
                )
                for name, rows in before_v7.items():
                    actual = {
                        row[0]: tuple(row)
                        for row in connection.exec_driver_sql(
                            f'SELECT * FROM "{name}" ORDER BY id'
                        ).fetchall()
                    }
                    for row in rows:
                        assert actual[row[0]] == tuple(row), name
                report["iteration2_database"] = (
                    "Existing populated v7: all previous rows and schema objects unchanged; new UI facts verified separately"
                )
                assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
                assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM attempt_skill_results WHERE deleted_at IS NULL"
                    ).scalar_one()
                    == 2
                )
                assert connection.exec_driver_sql(
                    "SELECT DISTINCT s.outcome, r.outcome FROM attempt_skill_results s "
                    "JOIN attempt_item_results r ON r.id=s.attempt_item_result_id "
                    "WHERE s.deleted_at IS NULL"
                ).fetchall() == [("INCORRECT", "CORRECT")]
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM attempts a JOIN student_works w ON w.id=a.student_work_id WHERE w.assessment_id=? AND w.student_id=?",
                        (str(data.homework_assessments[0].id), str(data.students[0][0].id)),
                    ).scalar_one()
                    == 5
                )
                assert (
                    connection.exec_driver_sql(
                        "SELECT a.result FROM attempts a JOIN student_works w "
                        "ON w.id=a.student_work_id WHERE w.assessment_id=? AND w.student_id=? "
                        "ORDER BY a.attempt_no DESC LIMIT 1",
                        (str(data.homework_assessments[0].id), str(data.students[0][0].id)),
                    ).scalar_one()
                    == "ACCEPTED"
                )
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM literature_attachments WHERE deleted_at IS NULL"
                    ).scalar_one()
                    == 5
                )
                report["schema"] = (
                    "v7 / 77 user tables / integrity and FK PASS / native picker multi-file additions survive reopen"
                )
        finally:
            engine.dispose()
        for path in root.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IWRITE | stat.S_IREAD)
    app.quit()
    screenshots = []
    for picture in sorted(capture_root.glob("iteration2_5-exe-*.png")):
        if "debug" not in picture.stem:
            screenshots.append(picture.name)
    report["screenshots"] = screenshots
    report["sqlalchemy_backend"] = "Pinned 2.1.1 Python implementations (ADR-043)"
    (output_root / "packaged-qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
