"""The 25 checkpoint SQL contracts, now pytest against production migrations."""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.util.exc import CommandError

import studium.infrastructure.database.migrations.versions.v0001 as migration
from studium.infrastructure.database.migrations import SCHEMA_REVISION, upgrade_database
from studium.infrastructure.database.session import create_database_engine

SCHEMA = Path(migration.__file__).with_suffix(".sql")
T0 = 1_790_769_600_000_000
TABLES = {
    "academic_terms",
    "courses",
    "student_groups",
    "course_offerings",
    "students",
    "enrollments",
    "assessments",
    "student_works",
    "attempts",
    "grades",
}
LEARNING_TABLES = {
    "topics",
    "skills",
    "lessons",
    "attendance",
    "assessment_items",
    "topic_skills",
    "lesson_topics",
    "assessment_topics",
    "assessment_skills",
    "assessment_item_topics",
    "assessment_item_skills",
}


class TestDatabaseContracts:
    @pytest.fixture(autouse=True)
    def database(self, tmp_path):
        self.path = tmp_path / "contract.sqlite"
        self.engine = create_database_engine(self.path)
        upgrade_database(self.engine)
        self.db = self.reopen()
        self.term = self.insert(
            "academic_terms", name="Test term", starts_on="2026-09-01", ends_on="2027-01-31"
        )
        self.course = self.insert("courses", name="Test course")
        self.group = self.insert("student_groups", number="TEST-01")
        self.student = self.insert("students", full_name="Synthetic student")
        self.offering = self.insert(
            "course_offerings", term_id=self.term, course_id=self.course, group_id=self.group
        )
        self.enrollment = self.insert(
            "enrollments",
            student_id=self.student,
            offering_id=self.offering,
            enrolled_at=T0,
            status="ACTIVE",
        )
        self.assessment = self.insert(
            "assessments",
            offering_id=self.offering,
            type="HOMEWORK",
            title="Test",
            issued_at=T0,
            due_at=T0 + 1000,
            max_score=10,
        )
        self.work = self.insert(
            "student_works", assessment_id=self.assessment, student_id=self.student
        )
        self.db.commit()
        yield
        self.db.close()
        self.engine.dispose()

    def reopen(self):
        upgrade_database(self.engine)
        raw = self.engine.raw_connection()
        raw.driver_connection.row_factory = sqlite3.Row
        return raw

    def insert(self, table, **fields):
        assert table in TABLES
        values = {"id": str(uuid4()), "created_at": T0, "updated_at": T0, "revision": 1, **fields}
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        self.db.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values())
        )
        return values["id"]

    def row(self, table, row_id):
        assert table in TABLES
        return self.db.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()

    def attempt(self, number, result="PRESENTED", **fields):
        return self.insert(
            "attempts",
            student_work_id=self.work,
            attempt_no=number,
            occurred_at=T0 + number,
            result=result,
            **fields,
        )

    def test_current_database_is_created_at_latest_version(self):
        assert (
            self.db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            == SCHEMA_REVISION
        )
        names = {
            row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        from studium.infrastructure.database.models.program import SPECS
        from studium.infrastructure.database.models.qa import SPECS as QA_SPECS

        assert names == {row.__table__.name for _, row, _, _ in QA_SPECS.values()} | {
            row.__table__.name for _, row, _, _ in SPECS.values()
        } | TABLES | LEARNING_TABLES | {
            "file_assets",
            "attempt_attachments",
            "question_cases",
            "messages",
            "message_attachments",
            "question_case_assessments",
            "question_case_attempts",
            "question_case_topics",
            "question_case_skills",
            "attempt_item_results",
            "homework_definitions",
            "problems",
            "problem_collections",
            "problem_collection_members",
            "seminar_materials",
            "seminar_material_topics",
            "literature_items",
            "homework_attachments",
            "problem_attachments",
            "seminar_attachments",
            "literature_attachments",
            "ticket_sets",
            "tickets",
            "ticket_problems",
            "ticket_problem_files",
            "ticket_assignments",
            "alembic_version",
        }
        assert self.db.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_academic_term_keeps_calendar_dates(self):
        assert self.row("academic_terms", self.term)["starts_on"] == "2026-09-01"
        with pytest.raises(sqlite3.IntegrityError):
            self.insert(
                "academic_terms", name="Invalid", starts_on="2026-02-30", ends_on="2026-03-01"
            )
        with pytest.raises(sqlite3.IntegrityError):
            self.insert(
                "academic_terms", name="Invalid", starts_on="2026-10-01", ends_on="2026-09-01"
            )

    def test_group_is_created(self):
        assert self.row("student_groups", self.group)["number"] == "TEST-01"

    def test_student_is_created(self):
        assert self.row("students", self.student)["active"] == 1
        assert self.row("students", self.student)["deleted_at"] is None

    def test_membership_is_unique_in_offering_context(self):
        with pytest.raises(sqlite3.IntegrityError):
            self.insert(
                "enrollments",
                student_id=self.student,
                offering_id=self.offering,
                enrolled_at=T0,
                status="ACTIVE",
            )
        other = self.insert(
            "course_offerings", term_id=self.term, course_id=self.course, group_id=self.group
        )
        self.insert(
            "enrollments",
            student_id=self.student,
            offering_id=other,
            enrolled_at=T0,
            status="ACTIVE",
        )
        assert self.db.execute("SELECT count(*) FROM enrollments").fetchone()[0] == 2

    def test_membership_history_can_end_and_resume_without_overlap(self):
        self.db.execute(
            "UPDATE enrollments SET status='WITHDRAWN', ended_at=?, updated_at=?, revision=2 WHERE id=?",
            (T0 + 10, T0 + 10, self.enrollment),
        )
        self.insert(
            "enrollments",
            student_id=self.student,
            offering_id=self.offering,
            enrolled_at=T0 + 10,
            status="ACTIVE",
        )
        with pytest.raises(sqlite3.IntegrityError):
            self.insert(
                "enrollments",
                student_id=self.student,
                offering_id=self.offering,
                enrolled_at=T0 + 5,
                ended_at=T0 + 8,
                status="COMPLETED",
            )

    def test_assessment_creation_and_due_instant(self):
        row = self.row("assessments", self.assessment)
        assert (row["type"], row["due_at"]) == ("HOMEWORK", T0 + 1000)
        with pytest.raises(sqlite3.IntegrityError):
            self.insert(
                "assessments",
                offering_id=self.offering,
                type="HOMEWORK",
                title="Invalid",
                issued_at=T0,
                due_at=T0 - 1,
            )

    def test_student_work_is_one_logical_identity(self):
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("student_works", assessment_id=self.assessment, student_id=self.student)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(student_works)")}
        assert "status" not in columns
        assert "final_score" not in columns

    def test_student_work_requires_membership_in_assessment_offering(self):
        other = self.insert("students", full_name="Другой синтетический студент")
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("student_works", assessment_id=self.assessment, student_id=other)

    def test_first_and_second_attempt_preserve_both_facts(self):
        first = self.attempt(1, "NEEDS_REVISION", comment="First fact")
        second = self.attempt(2, "ACCEPTED", score=8, max_score=10)
        assert first != second
        assert self.row("attempts", first)["comment"] == "First fact"
        assert self.row("attempts", first)["result"] == "NEEDS_REVISION"
        assert self.row("attempts", second)["result"] == "ACCEPTED"

    def test_duplicate_and_nonincreasing_attempt_numbers_are_rejected(self):
        self.attempt(1)
        self.attempt(3)
        for number in [1, 2, 3]:
            with pytest.raises(sqlite3.IntegrityError):
                self.attempt(number)
        indexes = list(self.db.execute("PRAGMA index_list(attempts)"))
        assert any(
            row[2] == 1
            and [c[2] for c in self.db.execute(f"PRAGMA index_info('{row[1]}')")]
            == ["student_work_id", "attempt_no"]
            for row in indexes
        )

    def test_history_order_is_by_attempt_number(self):
        for number in [1, 2, 3]:
            self.attempt(number)
        history = self.db.execute(
            "SELECT attempt_no FROM attempts WHERE student_work_id=? ORDER BY attempt_no",
            (self.work,),
        ).fetchall()
        assert [row[0] for row in history] == [1, 2, 3]

    def test_attempt_primary_fields_cannot_be_overwritten(self):
        attempt = self.attempt(1, "NEEDS_REVISION")
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE attempts SET result='ACCEPTED', updated_at=?, revision=2 WHERE id=?",
                (T0 + 2, attempt),
            )
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE attempts SET attempt_no=2, updated_at=?, revision=2 WHERE id=?",
                (T0 + 2, attempt),
            )
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM attempts WHERE id=?", (attempt,))

    def test_persisted_data_survives_reopen(self):
        attempt = self.attempt(1, "NEEDS_REVISION", comment="Persisted")
        self.db.commit()
        self.db.close()
        self.db = self.reopen()
        assert self.row("attempts", attempt)["comment"] == "Persisted"
        assert self.db.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_soft_delete_keeps_facts_and_does_not_reuse_number(self):
        attempt = self.attempt(1, "NEEDS_REVISION")
        self.db.execute(
            "UPDATE attempts SET deleted_at=?, updated_at=?, revision=2 WHERE id=?",
            (T0 + 5, T0 + 5, attempt),
        )
        assert self.row("attempts", attempt)["result"] == "NEEDS_REVISION"
        assert (
            self.db.execute("SELECT count(*) FROM attempts WHERE deleted_at IS NULL").fetchone()[0]
            == 0
        )
        with pytest.raises(sqlite3.IntegrityError):
            self.attempt(1)
        self.attempt(2, "ACCEPTED")

    def test_deleted_work_keeps_identity_and_attempt_history(self):
        attempt = self.attempt(1)
        self.db.execute(
            "UPDATE student_works SET deleted_at=?, updated_at=?, revision=2 WHERE id=?",
            (T0 + 5, T0 + 5, self.work),
        )
        assert self.row("attempts", attempt) is not None
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("student_works", student_id=self.student, assessment_id=self.assessment)
        with pytest.raises(sqlite3.IntegrityError):
            self.attempt(2)

    def test_revision_and_metadata_invariants(self):
        for revision in [0, 1, 3]:
            with pytest.raises(sqlite3.IntegrityError):
                self.db.execute(
                    "UPDATE students SET notes='New', updated_at=?, revision=? WHERE id=?",
                    (T0 + 5, revision, self.student),
                )
        self.db.execute(
            "UPDATE students SET notes='New', updated_at=?, revision=2 WHERE id=?",
            (T0 + 5, self.student),
        )
        assert self.row("students", self.student)["revision"] == 2
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE students SET updated_at=?, revision=3 WHERE id=?", (T0 + 1, self.student)
            )
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("students", full_name="Invalid", revision=0)

    def test_foreign_key_integrity_is_enforced(self):
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM courses WHERE id=?", (self.course,))
        assert self.db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert len(self.db.execute("PRAGMA foreign_key_list(course_offerings)").fetchall()) > 0

    def test_historical_offering_and_assessment_context_cannot_change(self):
        other = self.insert("courses", name="Другой тестовый курс")
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE course_offerings SET course_id=?, updated_at=?, revision=2 WHERE id=?",
                (other, T0 + 5, self.offering),
            )
        second = self.insert(
            "course_offerings", term_id=self.term, course_id=other, group_id=self.group
        )
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE assessments SET offering_id=?, updated_at=?, revision=2 WHERE id=?",
                (second, T0 + 5, self.assessment),
            )

    def test_current_assessment_maximum_does_not_change_attempt_snapshot(self):
        original_maximum = self.row("assessments", self.assessment)["max_score"]
        attempt = self.attempt(1, "ACCEPTED", score=8, max_score=10)
        with pytest.raises(sqlite3.IntegrityError, match="semantics after first attempt"):
            self.db.execute(
                "UPDATE assessments SET max_score=20, updated_at=?, revision=2 WHERE id=?",
                (T0 + 5, self.assessment),
            )
        assert self.row("assessments", self.assessment)["max_score"] == original_maximum
        assert self.row("attempts", attempt)["max_score"] == 10

    def test_grade_supports_all_four_representations(self):
        accepted = self.attempt(1, "ACCEPTED")
        failed = self.attempt(2, "NEEDS_REVISION")
        numeric = self.attempt(3, "SCORED", score=7)
        bounded = self.attempt(4, "SCORED", score=8, max_score=10)
        traditional = self.attempt(5, "ACCEPTED")
        for attempt, kind, fields in [
            (accepted, "PASS_FAIL", {"passed": 1}),
            (failed, "PASS_FAIL", {"passed": 0}),
            (numeric, "NUMERIC", {"score": 7}),
            (bounded, "NUMERIC", {"score": 8, "max_score": 10}),
            (traditional, "TRADITIONAL", {"label": "отлично"}),
        ]:
            self.insert("grades", attempt_id=attempt, kind=kind, **fields)
        assert self.db.execute("SELECT count(*) FROM grades").fetchone()[0] == 5
        assert self.row("attempts", numeric)["score"] == 7

    def test_grade_cannot_overwrite_or_contradict_attempt(self):
        attempt = self.attempt(1, "ACCEPTED", score=8, max_score=10)
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("grades", attempt_id=attempt, kind="NUMERIC", score=9, max_score=10)
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("grades", attempt_id=attempt, kind="PASS_FAIL", passed=0)
        grade = self.insert("grades", attempt_id=attempt, kind="NUMERIC", score=8, max_score=10)
        with pytest.raises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE grades SET score=9, updated_at=?, revision=2 WHERE id=?", (T0 + 5, grade)
            )
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("grades", attempt_id=attempt, kind="TRADITIONAL", label="5")

    def test_score_checks_reject_invalid_ranges(self):
        for fields in [
            {"score": -1},
            {"score": 11, "max_score": 10},
            {"score": float("inf")},
            {"max_score": 0},
        ]:
            with pytest.raises(sqlite3.IntegrityError):
                self.attempt(1, "SCORED", **fields)
        with pytest.raises(sqlite3.IntegrityError):
            self.attempt(1, "SCORED")

    def test_uuid_identity_is_not_autoincrement(self):
        with pytest.raises(sqlite3.IntegrityError):
            self.insert("students", id="123", full_name="Invalid")
        assert "AUTOINCREMENT" not in SCHEMA.read_text(encoding="utf-8").upper()

    def test_unknown_newer_version_is_rejected_without_data_reset(self):
        self.db.execute("UPDATE alembic_version SET version_num='unknown_future_revision'")
        self.db.commit()
        with pytest.raises(CommandError):
            upgrade_database(self.engine)
        assert self.row("students", self.student) is not None
