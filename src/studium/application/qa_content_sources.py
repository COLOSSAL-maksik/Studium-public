"""Frozen source content and explicit, transactional plan reassignment."""

import json
from dataclasses import dataclass

from studium.domain import qa as q
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId


@dataclass(frozen=True)
class PlanContentPreview:
    offering_id: EntityId
    version_id: EntityId
    course_semester: int
    expected_revision: int
    mode: str
    fingerprint: str
    retained_modules: tuple
    retained_works: tuple
    retired_modules: tuple
    retired_works: tuple
    incoming_modules: tuple
    incoming_works: tuple
    facts: tuple
    conflicts: tuple
    warnings: tuple


class QAContentSources:
    def _problem_snapshot(self, r, problem_id):
        from studium.application.qa_services import record

        source = self._require(r.problems, problem_id)
        problem = self._effective_problem(r, source)
        owner = problem.family_id or problem.id
        return {
            "source": record(source),
            "family": record(self._require(r.problems, source.family_id))
            if source.family_id
            else None,
            "title": problem.title,
            "statement": problem.statement,
            "correct_answer": problem.correct_answer,
            "solution": problem.solution,
            "details_json": problem.details_json,
            "topic_ids": [v.topic_id for v in r.problem_topics.for_owner(owner)],
            "skill_ids": [v.skill_id for v in r.problem_skills.for_owner(owner)],
            "files": [record(v) for v in self._problem_files(r, problem)],
        }

    def _definition_files_snapshot(self, r, definition_id):
        from studium.application.qa_services import record

        files = list(r.homework_attachments.for_owner(definition_id))
        for link in r.homework_pack_works.list():
            if link.definition_id == definition_id:
                files.extend(r.homework_pack_attachments.for_owner(link.homework_pack_id))
        return [record(v) for v in {v.file_asset_id: v for v in files}.values()]

    def _save_content_source(self, r, plan, *, module=None, work=None, content=None):
        from studium.application.qa_services import document, record

        manual = content is None
        if content is None:
            content = {"module": record(module)} if module else {}
            if work and work.definition_id:
                content = json.loads(
                    self._content_snapshot(
                        r,
                        self._require(r.offerings, plan.offering_id).course_id,
                        {"works": [{"definition_id": str(work.definition_id)}]},
                    )
                )
        if work and work.definition_id:
            definition_id = str(work.definition_id)
            selected = {
                name: [
                    v
                    for v in content.get(name, [])
                    if str(v.get("definition_id", v.get("id"))) == definition_id
                ]
                for name in (
                    "definitions",
                    "definition_topics",
                    "definition_skills",
                    "definition_problems",
                )
            }
            problem_ids = {str(v["problem_id"]) for v in selected["definition_problems"]}
            selected["problem_snapshots"] = [
                v
                for v in content.get("problem_snapshots", [])
                if str(v["source"]["id"]) in problem_ids
            ]
            selected["definition_files"] = {
                definition_id: content.get("definition_files", {}).get(definition_id, [])
            }
            if "problem_snapshots" not in content:
                selected.pop("problem_snapshots")
            content = selected
        source = q.PlanContentSource(
            metadata=self._meta(),
            semester_plan_id=plan.id,
            plan_module_id=module.id if module else None,
            planned_work_id=work.id if work else None,
            program_version_id=plan.program_version_id if not manual else None,
            course_semester=plan.course_semester,
            snapshot_json=document(content),
        )
        r.plan_content_sources.insert(source)
        return source

    def plan_content_bindings(self, offering_id):
        snapshot = self.semester_plan(offering_id)
        return tuple(self._r.plan_content_sources.for_owner(snapshot.plan.id)) if snapshot else ()

    def _work_content(self, r, work):
        sources = [
            v
            for v in r.plan_content_sources.for_owner(work.semester_plan_id)
            if v.planned_work_id == work.id
        ]
        if not sources:
            raise ValueError("Нет сохранённой привязки содержания работы")
        source = sources[0]
        data = json.loads(source.snapshot_json)
        if work.definition_id and "problem_snapshots" not in data:
            raise ValueError(
                "Прежняя версия не содержит снимков задач; явно назначьте новую версию с preview"
            )
        return data

    def _assessment_content(self, r, assessment_id):
        if r.issued_works is None:
            return None
        issued = next((v for v in r.issued_works.list() if v.assessment_id == assessment_id), None)
        if not issued:
            return None
        work = self._require(r.planned_works, issued.planned_work_id, historical=True)
        source = next(
            (
                v
                for v in r.plan_content_sources.for_owner(work.semester_plan_id)
                if v.planned_work_id == work.id
            ),
            None,
        )
        return json.loads(source.snapshot_json) if source else None

    def _frozen_assessment_problem(self, r, assessment_id, problem_id):
        data = self._assessment_content(r, assessment_id)
        return next(
            (
                v
                for v in (data or {}).get("problem_snapshots", [])
                if v["source"]["id"] == str(problem_id)
            ),
            None,
        )

    def preview_plan_content(
        self, offering_id, version_id, course_semester, *, expected_revision, mode="retain"
    ):
        from studium.application.qa_services import document, record, stale

        if mode not in {"retain", "replace_unissued"}:
            raise ValueError("Выберите сохранение назначений или замену невыданных работ")
        with self._transaction() as r:
            plans = r.semester_plans.for_owner(offering_id)
            if not plans:
                raise ValueError("Сначала сохраните план семестра")
            snapshot = self._plan_snapshot(r, plans[0])
            stale(snapshot.plan, expected_revision)
            version = self._require(r.program_versions, version_id)
            program = self._require(r.course_programs, version.course_program_id)
            context = self._context(r, offering_id)
            if (
                program.course_id != context.course.id
                or type(course_semester) is not int
                or course_semester < 1
            ):
                raise ValueError("Выберите программу этой дисциплины и номер семестра")
            issued_ids = {v.planned_work_id for v in snapshot.issued}
            required = [
                v
                for v in r.required_work_sets.list(include_deleted=True)
                if v.module_id in {m.id for m in snapshot.modules}
            ]
            retained_works = tuple(
                w for w in snapshot.works if mode == "retain" or w.id in issued_ids
            )
            retained_module_ids = {w.module_id for w in retained_works} | {
                v.module_id for v in required
            }
            retained_modules = tuple(
                m for m in snapshot.modules if mode == "retain" or m.id in retained_module_ids
            )
            retired_works = tuple(w for w in snapshot.works if w not in retained_works)
            retired_modules = tuple(m for m in snapshot.modules if m not in retained_modules)
            data = json.loads(version.content_json)
            unchanged = (snapshot.plan.program_version_id, snapshot.plan.course_semester) == (
                version_id,
                course_semester,
            )
            if unchanged:
                retained_modules, retained_works = snapshot.modules, snapshot.works
                retired_modules = retired_works = ()
            incoming_modules = (
                tuple(
                    m
                    for m in data.get("modules", [])
                    if m.get("course_semester") == course_semester
                )
                if not unchanged
                else ()
            )
            incoming_works = (
                tuple(
                    w for w in data.get("works", []) if w.get("course_semester") == course_semester
                )
                if not unchanged
                else ()
            )
            conflicts = []
            if snapshot.plan.course_semester != course_semester and (
                retained_works or retained_modules
            ):
                conflicts.append(
                    "Сохраняемые назначения принадлежат прежнему семестру курса. Создайте отдельный план исходного периода; факты между семестрами не переносятся."
                )
            ranges = [(m.title, m.start_week, m.end_week) for m in retained_modules] + [
                (m["title"], m["start_week"], m["end_week"]) for m in incoming_modules
            ]
            ordered = sorted(ranges, key=lambda m: m[1])
            if any(m[2] > snapshot.plan.weeks for m in ranges):
                conflicts.append("Новые модули выходят за календарь семестра")
            for a, b in zip(ordered, ordered[1:]):
                if a[2] >= b[1]:
                    conflicts.append(
                        f"Пересечение модулей «{a[0]}» и «{b[0]}»: явно согласуйте календарь до переназначения"
                    )
            work_ids = {
                w.id
                for w in r.works.list(include_deleted=True)
                if w.assessment_id in {i.assessment_id for i in snapshot.issued}
            }
            attempts = [
                a for a in r.attempts.list(include_deleted=True) if a.student_work_id in work_ids
            ]
            submissions = [
                s
                for s in r.submissions.list(include_deleted=True)
                if s.attempt_id in {a.id for a in attempts}
            ]
            reviews = [
                v
                for v in r.reviews.list(include_deleted=True)
                if v.submission_id in {s.id for s in submissions}
            ]
            facts = (
                len(snapshot.issued),
                len(attempts),
                len(submissions),
                len(reviews),
                len(required),
            )
            fingerprint = document(
                {
                    "plan": record(snapshot.plan),
                    "modules": [record(m) for m in snapshot.modules],
                    "works": [record(w) for w in snapshot.works],
                    "issued": [record(i) for i in snapshot.issued],
                    "required": [record(v) for v in required],
                    "required_bindings": [
                        record(v)
                        for v in r.required_work_bindings.list(include_deleted=True)
                        if v.required_set_id in {s.id for s in required}
                    ],
                    "student_works": [
                        record(v) for v in r.works.list(include_deleted=True) if v.id in work_ids
                    ],
                    "attempts": [record(v) for v in attempts],
                    "submissions": [record(v) for v in submissions],
                    "reviews": [record(v) for v in reviews],
                    "sources": [
                        record(v) for v in r.plan_content_sources.for_owner(snapshot.plan.id)
                    ],
                }
            )
            warnings = ("Существующие выдачи и факты сохраняют исходные UUID, версию и семестр.",)
            if retired_works:
                warnings += (
                    f"Невыданные работы будут явно архивированы: {len(retired_works)}. Сохранённое содержание и история остаются доступны.",
                )
            return PlanContentPreview(
                offering_id,
                version_id,
                course_semester,
                expected_revision,
                mode,
                fingerprint,
                retained_modules,
                retained_works,
                retired_modules,
                retired_works,
                incoming_modules,
                incoming_works,
                facts,
                tuple(conflicts),
                warnings,
            )

    def apply_plan_content(self, preview, *, confirmed=False):
        from contextlib import contextmanager
        from copy import copy

        if not confirmed:
            raise ValueError("Подтвердите preview переназначения содержания")
        with self._transaction() as r:
            command = copy(self)
            command._r = r

            @contextmanager
            def transaction():
                yield r

            command._transaction = transaction
            current = command.preview_plan_content(
                preview.offering_id,
                preview.version_id,
                preview.course_semester,
                expected_revision=preview.expected_revision,
                mode=preview.mode,
            )
            if current != preview:
                raise RepositoryError(
                    RepositoryFailure.REVISION_CONFLICT,
                    "Назначения или факты изменились; повторите preview",
                )
            if current.conflicts:
                raise ValueError("; ".join(current.conflicts))
            plan = r.semester_plans.for_owner(preview.offering_id)[0]
            if (plan.program_version_id, plan.course_semester) == (
                preview.version_id,
                preview.course_semester,
            ):
                return plan
            for work in preview.retired_works:
                r.planned_works.soft_delete(
                    work.id, expected_revision=work.revision, at=self._clock()
                )
            for module in preview.retired_modules:
                r.plan_modules.soft_delete(
                    module.id, expected_revision=module.revision, at=self._clock()
                )
            plan = self._update(
                r.semester_plans,
                plan,
                program_version_id=preview.version_id,
                course_semester=preview.course_semester,
                configured=True,
            )
            self._populate_content_plan(r, plan)
            self._capture_plan(
                r,
                plan,
                "Подтверждённое переназначение: "
                + preview.mode
                + "; прежние bindings и факты сохранены",
            )
            return plan
