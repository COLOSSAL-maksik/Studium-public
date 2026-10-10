"""Create only new, synthetic demo data outside any Git checkout (offline)."""

import argparse
from pathlib import Path

from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.user_data import AppPaths


def create_demo(directory: Path) -> dict:
    paths = AppPaths(directory)
    if paths.root.is_relative_to(AppPaths.resolve().root):
        raise ValueError("Choose a separate demo directory, not production Studium")
    # Exclusive directory creation: never open or overwrite an existing user DB.
    paths.root.mkdir(parents=True, exist_ok=False)
    runtime = create_runtime(paths.root)
    try:
        service = runtime.service
        term = service.create_term(
            "DEMO · осень 2026", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31)
        )
        course = service.create_course("Демонстрационная дисциплина", "DEMO")
        group = service.create_group("DEMO-02", "Синтетическая кафедра")
        offering = service.create_offering(term.id, course.id, group.id)
        students = [
            service.create_student(offering.id, f"Студент {i:03d}", "Синтетическая запись")
            for i in range(1, 4)
        ]
        assessment = service.create_assessment(
            offering.id, "DEMO · работа 1", AssessmentType.HOMEWORK
        )
        attempt = service.record_attempt(
            students[0].id,
            assessment.id,
            occurred_at=UtcInstant.now(),
            result=AttemptResult.ACCEPTED,
            comment="Синтетический результат",
        )
        source = paths.temp_dir / "demo.txt"
        source.parent.mkdir()
        source.write_text("Studium DEMO: generated synthetic attachment.\n", encoding="utf8")
        service.import_file_for_attempt(attempt.id, source)
        source.unlink()
        source.parent.rmdir()
        service.select_term(term.id)
        return {"students": len(students), "group": group.number, "synthetic": True}
    finally:
        runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="NEW directory outside Git; never production Studium",
    )
    args = parser.parse_args()
    # Block the default production root even when it happens to be empty today.
    if args.data_dir.expanduser().resolve().is_relative_to(AppPaths.resolve().root):
        parser.error("Choose a separate new demo directory, not the production root")
    try:
        print(create_demo(args.data_dir))
    except FileExistsError:
        parser.error("Demo directory already exists; nothing was opened or changed")


if __name__ == "__main__":
    main()
