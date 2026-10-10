"""Actual onedir exe: PID-restricted UIA and populated v8 preservation."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from iteration2_scenario import seed
from preview_iteration3 import add_family
from PySide6.QtWidgets import QApplication

from studium.composition import create_runtime
from studium.domain.content import GenerationCriteria, ProblemPurpose
from studium.domain.enums import AssessmentType, AttendanceStatus
from studium.domain.value_objects import AcademicWeekNumber, LocalDate
from studium.infrastructure.database.migrations import migration_config
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.integration.test_file_migrations import snapshot
from tests.legacy_schema import (
    HistoricalStudiumService,
    preserved_objects,
    preserved_rows,
    repository_set,
    transaction_factory,
)


def historical_profile(root):
    root.mkdir(parents=True)
    engine = create_database_engine(root / "studium.sqlite", wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0008_problem_variants")
    sessions = create_session_factory(engine)
    s = HistoricalStudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(root / "preferences.json"),
        file_storage=LocalFileStorage(root),
    )
    term = s.create_term("Synthetic v8", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic course")
    group = s.create_group("V8-TEST")
    offering = s.create_offering(term.id, course.id, group.id)
    s.create_student(offering.id, "Synthetic Student")
    control = s.create_assessment(offering.id, "Legacy control", AssessmentType.CONTROL_WORK)
    problem = s.create_material(
        "problems",
        course_id=course.id,
        title="Legacy task",
        statement="Unchanged condition",
        correct_answer="Unchanged answer",
    )
    source = root / "synthetic.txt"
    source.write_bytes(b"immutable v7 file bytes")
    file = s.import_file_for_material("problems", problem.id, source)
    s.save_ticket_set(
        offering.id,
        s.generate_ticket_draft(GenerationCriteria(course.id, 1)),
        assessment_id=control.id,
        assign_students=True,
    )
    file_path = s.accessible_file_path(file.file_asset_id)
    with engine.connect() as connection:
        rows, objects = snapshot(connection)
    engine.dispose()
    return rows, objects, file_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="store_true", help="Diagnose native QA before packaging")
    parser.add_argument("--output", type=Path, help="Separate review output directory")
    parser.add_argument(
        "--exe", type=Path, help="Installed Studium.exe to exercise instead of dist"
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This acceptance harness requires native Windows")
    if args.source and args.exe:
        parser.error("--exe cannot be combined with --source")
    project = Path(__file__).resolve().parents[1]
    output = args.output or project / "docs/screenshots/iteration4"
    exe = args.exe.resolve() if args.exe else project / "dist/Studium/Studium.exe"
    assert args.source or exe.is_file()
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication([])
    report = {
        "target": "source" if args.source else "packaged exe",
        "exe_bytes": None if args.source else exe.stat().st_size,
        "bundle_bytes": None
        if args.source
        else sum(p.stat().st_size for p in exe.parent.rglob("*") if p.is_file()),
        "runs": [],
    }
    with TemporaryDirectory(prefix="studium-iteration4-exe-") as temporary:
        root = Path(temporary)
        qa_logs = root / "qa-logs"
        qa_logs.mkdir()
        runtime_names = (
            "studium.sqlite",
            "preferences.json",
            "files",
            "cache",
            "logs",
            "backups",
            "exports",
            "data",
            "runtime",
            "storage",
            "temp",
        )
        repository_runtime_before = {name for name in runtime_names if (project / name).exists()}
        profile = root / "workflow/Studium"
        runtime = create_runtime(profile)
        s = runtime.service
        data = seed(s, profile)
        bulk_lesson = s.create_lesson(
            data.offerings[0].id,
            LocalDate(2026, 10, 6),
            planned_week=AcademicWeekNumber(6),
            title="Native bulk attendance QA",
        )
        assert not any(e.attendance for e in s.list_lesson_attendance(bulk_lesson.id))
        qa_pdf = root / "native-seminar.pdf"
        qa_pdf.write_bytes(data.pdf.read_bytes())
        for assessment in s.list_assessments(data.offerings[0].id):
            if assessment.type == AssessmentType.HOMEWORK:
                work = s.get_or_create_work(data.students[0][0].id, assessment.id)
                entries = s.history(work.id).entries
                if entries:
                    s.import_file_for_attempt(entries[0].attempt.id, data.pdf)
        family, _ = add_family(s, data)
        s.save_ticket_set(
            data.offerings[0].id,
            s.generate_ticket_draft(
                GenerationCriteria(
                    data.course.id, 3, purpose=ProblemPurpose.CONTROL, problem_ids=(family.id,)
                )
            ),
            title="Рубежный контроль · три варианта",
        )
        # Remove each synthetic source while keeping managed immutable copies.
        removed_sources = []
        for source in profile.iterdir():
            if source.is_file() and source.suffix.lower() in {
                ".png",
                ".jpg",
                ".pdf",
                ".txt",
                ".doc",
                ".docx",
            }:
                removed_sources.append(source.name)
                source.unlink()
        assert removed_sources
        report["removed_sources"] = removed_sources
        runtime.close()
        engine = create_database_engine(profile / "studium.sqlite", wal=False)
        with engine.connect() as connection:
            workflow_rows, workflow_objects = snapshot(connection)
        engine.dispose()
        file_bytes = {
            p.relative_to(profile): p.read_bytes()
            for p in (profile / "files").rglob("*")
            if p.is_file()
        }
        legacy = root / "migration/Studium"
        old_rows, old_objects, file = historical_profile(legacy)
        legacy_bytes = file.read_bytes()
        env = dict(os.environ, QT_QPA_PLATFORM="windows", QT_SCALE_FACTOR="0.5")
        env["PATH"] = (
            str(Path(os.environ["WINDIR"]) / "System32") + os.pathsep + os.environ["WINDIR"]
        )
        env.pop("PYTHONPATH", None)
        env["STUDIUM_QA_SOURCE"] = "1" if args.source else "0"
        env["STUDIUM_QA_PDF"] = str(qa_pdf)
        for mode in (
            ("workflow", "reopen") if args.source else ("fresh", "migration", "workflow", "reopen")
        ):
            actual = root / ("workflow" if mode == "reopen" else mode) / "Studium"
            assert not actual.resolve().is_relative_to(project.resolve())
            env["LOCALAPPDATA"] = str(actual.parent)
            env["STUDIUM_QA_TRACE"] = str(qa_logs / f"{mode}-native-trace.txt")
            process = subprocess.Popen(
                [sys.executable, "-m", "studium"] if args.source else [str(exe)],
                env=env,
                cwd=project,
            )
            try:
                result = subprocess.run(
                    [
                        str(
                            Path(os.environ["WINDIR"])
                            / "System32/WindowsPowerShell/v1.0/powershell.exe"
                        ),
                        "-NoProfile",
                        "-File",
                        str(project / "scripts/smoke_iteration4_packaged.ps1"),
                        "-OwnProcessId",
                        str(process.pid),
                        "-Mode",
                        mode,
                    ],
                    capture_output=True,
                    encoding="utf8",
                    errors="replace",
                    env=env,
                    timeout=240,
                )
                (qa_logs / f"{mode}.txt").write_text(result.stdout + result.stderr, encoding="utf8")
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                process.wait(timeout=10)
                assert process.returncode == 0
                report["runs"].append({"mode": mode, "exit": 0, "checks": result.stdout.strip()})
            finally:
                if process.poll() is None:
                    subprocess.run(
                        ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                    process.wait(timeout=10)
            engine = create_database_engine(actual / "studium.sqlite", wal=False)
            with engine.connect() as connection:
                assert (
                    connection.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    ).scalar_one()
                    == "0009_daily_workflow"
                )
                assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
                assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
                after, objects = snapshot(connection)
                report["user_tables"] = len(after)
                report["alembic_head"] = "0009_daily_workflow"
                if mode == "migration":
                    assert preserved_rows(old_rows, after) and preserved_objects(
                        old_objects, objects
                    )
                    assert file.read_bytes() == legacy_bytes
                elif mode in {"workflow", "reopen"}:
                    assert (
                        all(
                            set(map(tuple, rows)).issubset(set(map(tuple, after[table])))
                            for table, rows in workflow_rows.items()
                        )
                        and workflow_objects == objects
                    )
                    if mode == "reopen":
                        assert after == workflow_rows
                    assert all((profile / p).read_bytes() == b for p, b in file_bytes.items())
            engine.dispose()
            if mode == "workflow":
                check = create_runtime(profile)
                try:
                    marks = [
                        e
                        for e in check.service.list_lesson_attendance(bulk_lesson.id)
                        if e.attendance
                    ]
                    assert len(marks) == 3 and all(
                        e.attendance.status == AttendanceStatus.PRESENT for e in marks
                    )
                    seminar = next(
                        m
                        for m in check.service.list_materials("seminars")
                        if m.title == "Native QA seminar"
                    )
                    assert seminar.plan_text == "Native synthetic seminar plan"
                    linked = check.service.content_targets("seminar_problems", seminar.id)
                    assert len(linked) == 2
                    assert any(
                        p.title == "Native QA new task" and p.purposes == (ProblemPurpose.SEMINAR,)
                        for p in linked
                    )
                    assert len(check.service.list_material_files("seminars", seminar.id)) == 1
                    report["native_facts"] = {
                        "attendance_selected": 3,
                        "other_students_unchanged": True,
                        "seminar_tasks": 2,
                        "seminar_pdf": 1,
                        "new_task_in_bank": True,
                    }
                finally:
                    check.close()
                workflow_rows = after
                qa_pdf.unlink()
            if mode in {"workflow", "reopen"}:
                preferences = json.loads((profile / "preferences.json").read_text(encoding="utf8"))
                assert preferences["theme"] == "dark"
                assert preferences["sidebar_expanded"]
        report["schema"] = (
            "0009_daily_workflow / workflow + reopen preservation / files, TicketSets and assignments / integrity + FK PASS"
            if args.source
            else "0009_daily_workflow / populated v8 preservation / files, TicketSets and assignments / integrity + FK PASS"
        )
        report["runtime_isolation"] = {
            "launch_cwd": "repository",
            "temporary_localappdata": True,
            "all_managed_files_outside_repository": all(
                not (profile / p).resolve().is_relative_to(project.resolve()) for p in file_bytes
            ),
            "no_new_runtime_entries_in_repository": repository_runtime_before
            == {name for name in runtime_names if (project / name).exists()},
        }
        assert all(
            report["runtime_isolation"][key]
            for key in (
                "all_managed_files_outside_repository",
                "no_new_runtime_entries_in_repository",
            )
        )
    app.quit()
    output.mkdir(parents=True, exist_ok=True)
    (output / ("native-source-qa.json" if args.source else "packaged-qa.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
