"""Integrated QA commands/read DTOs over concrete ports, never SQL or Qt."""

import json
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import asdict, dataclass, fields, replace
from datetime import date, timedelta, timezone
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.qa_content_sources import QAContentSources
from studium.application.qa_summary import QASummary
from studium.domain import entities as e
from studium.domain import qa as q
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind, StudentWorkStatus
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, LocalDate, UtcInstant


def document(value):
    def encode(item):
        if isinstance(item, (EntityId, LocalDate)):
            return str(item)
        if isinstance(item, UtcInstant):
            return item.epoch_microseconds
        raise TypeError(type(item).__name__)

    return json.dumps(value, default=encode, ensure_ascii=False, sort_keys=True)


def record(value):
    return {f.name: getattr(value, f.name) for f in fields(value) if f.name != "metadata"} | {
        "id": value.id,
        "revision": value.revision,
    }


def stale(actual, expected):
    if actual.revision != expected:
        raise RepositoryError(RepositoryFailure.REVISION_CONFLICT, "Объект изменён; обновите форму")


@dataclass(frozen=True)
class PlanSnapshot:
    plan: q.SemesterPlan
    modules: tuple
    works: tuple
    issued: tuple
    history: tuple


@dataclass(frozen=True)
class PlanPreview:
    plan_id: EntityId
    expected_revision: int
    plan_values: dict
    module_changes: tuple
    work_changes: tuple
    warnings: tuple
    conflicts: tuple
    affected: tuple
    suggestions: tuple
    reason: str


@dataclass(frozen=True)
class QueueEntry:
    submission: q.Submission
    attempt: e.Attempt
    work: e.StudentWork
    assessment: e.Assessment
    student: e.Student
    group: e.StudentGroup
    course: e.Course
    deadline: UtcInstant
    state: str
    file_count: int
    reviewed: bool
    result: AttemptResult | None = None


@dataclass(frozen=True)
class StudentModuleResult:
    module: q.PlanModule
    student_id: EntityId
    state: str
    required_works: tuple
    debt_works: tuple
    required_set_id: EntityId | None
    offering_id: EntityId | None = None


class QAPackageService(QAContentSources, QASummary):
    def find_student_work(self, student_id, assessment_id):
        return self._r.works.find_for_student(student_id, assessment_id, include_deleted=True)

    def work_settings(self, offering_id):
        snapshot = self.semester_plan(offering_id)
        planned = {w.id: w for w in snapshot.works} if snapshot else {}
        by_assessment = (
            {i.assessment_id: planned[i.planned_work_id] for i in snapshot.issued}
            if snapshot
            else {}
        )
        with self._transaction() as r:
            rules = {}
            for rule in r.scoring_rules.list():
                if rule.assessment_id in by_assessment and (
                    rule.assessment_id not in rules
                    or rules[rule.assessment_id].sequence < rule.sequence
                ):
                    rules[rule.assessment_id] = rule
        return snapshot, by_assessment, rules

    def get_course_program(self, program_id):
        return self._require(self._r.course_programs, program_id, historical=True)

    def version_direction_ids(self, version_id):
        return tuple(link.direction_id for link in self._r.program_directions.for_owner(version_id))

    def get_program_version(self, version_id):
        return self._require(self._r.program_versions, version_id, historical=True)

    def fractional_scores_enabled(self):
        return getattr(self._preferences, "fractional_scores_enabled", lambda: False)()

    def set_fractional_scores_enabled(self, enabled):
        if type(enabled) is not bool:
            raise ValueError("Ожидается переключатель дробных баллов")
        self._preferences.set_fractional_scores_enabled(enabled)

    def review_settings(self):
        return getattr(self._preferences, "review_settings", lambda: (7, 24))()

    def set_review_settings(self, days, near_hours):
        q.deadline_state(None, self._clock(), days=days, near_hours=near_hours)
        self._preferences.set_review_settings(days, near_hours)

    def _input_bounds(self, minimum, maximum):
        enabled = self.fractional_scores_enabled()
        low, high = (
            q.score_cents(minimum, fractional=enabled),
            q.score_cents(maximum, fractional=enabled),
        )
        if low > high or high == 0:
            raise ValueError("Минимум должен быть не больше положительного максимума")
        return low, high

    def list_directions(self):
        return tuple(sorted(self._r.directions.list(), key=lambda d: (d.normalized_key, d.id)))

    def create_direction(self, code, name=""):
        code, key = q.direction_identity(code)
        value = q.Direction(metadata=self._meta(), code=code, normalized_key=key, name=name.strip())
        self._r.directions.insert(value)
        return value

    def list_course_programs(self, course_id=None):
        return tuple(
            p
            for p in self._r.course_programs.list()
            if course_id is None or p.course_id == course_id
        )

    def _content_snapshot(self, r, course_id, content):
        data = dict(content)
        modules = data.get("modules", [])
        for module in modules:
            ordinal = module.get("course_semester")
            if (
                type(ordinal) is not int
                or ordinal < 1
                or not module.get("title", "").strip()
                or not 1 <= module["start_week"] <= module["end_week"] <= 104
            ):
                raise ValueError("Укажите модуль, номер семестра курса и корректные недели")
        for ordinal in {m["course_semester"] for m in modules}:
            ordered = sorted(
                (m for m in modules if m["course_semester"] == ordinal),
                key=lambda m: m["start_week"],
            )
            if any(a["end_week"] >= b["start_week"] for a, b in zip(ordered, ordered[1:])):
                raise ValueError("Модули одного семестра пересекаются")
        definitions = []
        for work in data.get("works", []):
            definition = self._require(r.homework_definitions, EntityId(work["definition_id"]))
            if definition.course_id != course_id:
                raise ApplicationError("learning_course_mismatch")
            definitions.append(record(definition))
        data["definitions"] = definitions
        definition_ids = {EntityId(work["definition_id"]) for work in data.get("works", [])}
        for name in ("definition_topics", "definition_skills", "definition_problems"):
            data[name] = [
                record(link)
                for link in getattr(r, name).list()
                if link.definition_id in definition_ids
            ]
        data["problem_snapshots"] = [
            self._problem_snapshot(r, EntityId(id))
            for id in sorted({str(v["problem_id"]) for v in data["definition_problems"]})
        ]
        data["definition_files"] = {
            str(id): self._definition_files_snapshot(r, id) for id in definition_ids
        }
        for field, repository in (
            ("topic_ids", r.topics),
            ("skill_ids", r.skills),
            ("seminar_material_ids", r.seminar_materials),
            ("literature_item_ids", r.literature_items),
        ):
            snapshots = []
            for id in data.get(field, []):
                value = self._require(repository, EntityId(id))
                if value.course_id != course_id:
                    raise ApplicationError("learning_course_mismatch")
                snapshots.append(record(value))
            data[field + "_snapshots"] = snapshots
        data["material_files"] = {
            name: {
                str(v["id"]): [record(link) for link in getattr(r, attachments).for_owner(v["id"])]
                for v in data.get(field + "_snapshots", [])
            }
            for field, name, attachments in (
                ("seminar_material_ids", "seminars", "seminar_attachments"),
                ("literature_item_ids", "literature", "literature_attachments"),
            )
        }
        data["file_asset_ids"] = sorted(
            {
                str(v["file_asset_id"])
                for files in [
                    *data["definition_files"].values(),
                    *(p["files"] for p in data["problem_snapshots"]),
                    *(
                        files
                        for materials in data["material_files"].values()
                        for files in materials.values()
                    ),
                ]
                for v in files
            }
        )
        data["provenance"] = "explicit"
        return document(data)

    def _version_references(self, r, version):
        data = json.loads(version.content_json)
        fields = {
            "topic_id": data.get("topic_ids", []),
            "skill_id": data.get("skill_ids", []),
            "definition_id": [w["definition_id"] for w in data.get("works", [])],
            "seminar_material_id": data.get("seminar_material_ids", []),
            "literature_item_id": data.get("literature_item_ids", []),
            "file_asset_id": data.get("file_asset_ids", []),
        }
        for field, ids in fields.items():
            for id in set(ids):
                r.version_references.insert(
                    q.VersionReference(
                        metadata=self._meta(),
                        program_version_id=version.id,
                        **{field: EntityId(id)},
                    )
                )

    def create_course_program(
        self, course_id, title, *, direction_ids=(), content=None, notes="", label=""
    ):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            program = q.CourseProgram(
                metadata=self._meta(), course_id=course_id, title=title.strip(), notes=notes
            )
            version = q.ProgramVersion(
                metadata=self._meta(),
                course_program_id=program.id,
                version_no=1,
                content_json=self._content_snapshot(r, course_id, content or {}),
                label=label,
            )
            r.course_programs.insert(program)
            r.program_versions.insert(version)
            self._version_references(r, version)
            for id in set(direction_ids):
                self._require(r.directions, id)
                r.program_directions.insert(
                    q.ProgramDirection(
                        metadata=self._meta(), program_version_id=version.id, direction_id=id
                    )
                )
            return version

    def new_program_version(self, previous, *, content, direction_ids, label=""):
        with self._transaction() as r:
            program = self._require(r.course_programs, previous.course_program_id)
            versions = r.program_versions.for_owner(program.id, include_deleted=True)
            version = q.ProgramVersion(
                metadata=self._meta(),
                course_program_id=program.id,
                version_no=max(v.version_no for v in versions) + 1,
                label=label,
                content_json=self._content_snapshot(r, program.course_id, content),
            )
            r.program_versions.insert(version)
            self._version_references(r, version)
            for id in set(direction_ids):
                self._require(r.directions, id)
                r.program_directions.insert(
                    q.ProgramDirection(
                        metadata=self._meta(), program_version_id=version.id, direction_id=id
                    )
                )
            return version

    def program_versions(self, course_id):
        programs = {p.id for p in self.list_course_programs(course_id)}
        return tuple(v for v in self._r.program_versions.list() if v.course_program_id in programs)

    def program_display_names(self, course_id):
        with self._transaction() as r:
            programs = {p.id: p for p in r.course_programs.list() if p.course_id == course_id}
            directions = {d.id: d for d in r.directions.list(include_deleted=True)}
            codes = defaultdict(list)
            for link in r.program_directions.list(include_deleted=True):
                codes[link.program_version_id].append(directions[link.direction_id].code)
            versions = [v for v in r.program_versions.list() if v.course_program_id in programs]
            titles = {
                v.id: programs[v.course_program_id].title
                + (" — " + ", ".join(sorted(codes[v.id])) if codes[v.id] else "")
                for v in versions
            }
            counts = defaultdict(int)
            for title in titles.values():
                counts[title] += 1
            return {
                v.id: titles[v.id]
                + (
                    f" · версия {v.version_no}"
                    + (f" ({v.label})" if v.label else "")
                    + f" · {str(v.course_program_id)[:8]}"
                    if counts[titles[v.id]] > 1
                    else ""
                )
                for v in versions
            }

    def create_semester_plan(
        self,
        offering_id,
        *,
        version_id=None,
        course_semester=None,
        first_week_start=None,
        weeks=None,
        offset=180,
    ):
        with self._transaction() as r:
            context = self._context(r, offering_id)
            term = context.term
            existing = r.semester_plans.for_owner(offering_id)
            if existing:
                return existing[0]
            if version_id and (type(course_semester) is not int or course_semester < 1):
                raise ValueError("Укажите явный номер семестра курса")
            duration = min(
                104,
                max(
                    1,
                    (
                        (
                            date(term.ends_on.year, term.ends_on.month, term.ends_on.day)
                            - date(term.starts_on.year, term.starts_on.month, term.starts_on.day)
                        ).days
                        + 7
                    )
                    // 7,
                ),
            )
            plan = q.SemesterPlan(
                metadata=self._meta(),
                offering_id=offering_id,
                program_version_id=version_id,
                course_semester=course_semester,
                first_week_start=first_week_start or term.starts_on,
                weeks=weeks or duration,
                week_utc_offset_minutes=offset,
                configured=False,
            )
            r.semester_plans.insert(plan)
            if version_id:
                self._populate_content_plan(r, plan)
                snapshot = self._plan_snapshot(r, plan)
                conflicts, _, _ = self._validate_calendar(plan, snapshot.modules, snapshot.works)
                if conflicts:
                    raise ValueError("; ".join(conflicts))
            self._capture_plan(r, plan, "Первое сохранение плана")
            return plan

    def _assign_initial_plan(self, r, offering, version_id, course_semester):
        if type(course_semester) is not int or course_semester < 1:
            raise ValueError("Укажите явный номер семестра курса")
        term = self._require(r.terms, offering.term_id)
        plan = q.SemesterPlan(
            metadata=self._meta(),
            offering_id=offering.id,
            program_version_id=version_id,
            course_semester=course_semester,
            first_week_start=term.starts_on,
            weeks=17,
            week_utc_offset_minutes=term.week_utc_offset_minutes,
            configured=True,
        )
        r.semester_plans.insert(plan)
        self._populate_content_plan(r, plan)
        snapshot = self._plan_snapshot(r, plan)
        conflicts, _, _ = self._validate_calendar(plan, snapshot.modules, snapshot.works)
        if conflicts:
            raise ValueError("; ".join(conflicts))
        self._capture_plan(r, plan, "Назначена версия программы и явный номер семестра курса")

    def _populate_content_plan(self, r, plan):
        version = self._require(r.program_versions, plan.program_version_id, historical=True)
        program = self._require(r.course_programs, version.course_program_id, historical=True)
        offering = self._require(r.offerings, plan.offering_id)
        if program.course_id != offering.course_id:
            raise ApplicationError("learning_course_mismatch")
        data, modules = json.loads(version.content_json), {}
        for source in data.get("modules", []):
            if source.get("course_semester") != plan.course_semester:
                continue
            value = q.PlanModule(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                title=source["title"],
                start_week=source["start_week"],
                end_week=source["end_week"],
                sort_order=source.get("sort_order", 0),
            )
            r.plan_modules.insert(value)
            self._save_content_source(r, plan, module=value, content={"module": source})
            modules[source.get("key", source.get("id"))] = value.id
        definitions = {str(d["id"]): d for d in data.get("definitions", [])}
        for source in data.get("works", []):
            if source.get("course_semester") != plan.course_semester:
                continue
            definition = definitions.get(source["definition_id"], {})
            value = q.PlannedWork(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                definition_id=EntityId(source["definition_id"]),
                module_id=modules.get(source.get("module_key")),
                title=definition.get("title", source.get("title", "Работа")),
                type=AssessmentType(definition.get("type", "HOMEWORK")),
                number=definition.get("label", ""),
            )
            r.planned_works.insert(value)
            self._save_content_source(r, plan, work=value, content=data)

    def semester_plan(self, offering_id):
        with self._transaction() as r:
            plans = r.semester_plans.for_owner(offering_id)
            if not plans:
                return None
            return self._plan_snapshot(r, plans[0])

    @staticmethod
    def _plan_snapshot(r, plan):
        works = r.planned_works.for_owner(plan.id)
        ids = {w.id for w in works}
        return PlanSnapshot(
            plan,
            tuple(r.plan_modules.for_owner(plan.id)),
            tuple(works),
            tuple(i for i in r.issued_works.list() if i.planned_work_id in ids),
            tuple(r.plan_history.for_owner(plan.id)),
        )

    def _capture_plan(self, r, plan, reason):
        snapshot = self._plan_snapshot(r, plan)
        data = {
            "plan": record(plan),
            "modules": [record(m) for m in snapshot.modules],
            "works": [record(w) for w in snapshot.works],
            "content_sources": [record(v) for v in r.plan_content_sources.for_owner(plan.id)],
        }
        r.plan_history.insert(
            q.PlanHistory(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                plan_revision=plan.revision,
                snapshot_json=document(data),
                reason=reason,
            )
        )

    @staticmethod
    def _validate_calendar(plan, modules, works):
        conflicts, warnings, suggestions = [], [], []
        ordered = sorted(modules, key=lambda m: (m.start_week, m.end_week, m.id))
        for index, module in enumerate(ordered):
            if module.end_week > plan.weeks:
                conflicts.append(f"{module.title}: модуль выходит за {plan.weeks} недель")
            if index and ordered[index - 1].end_week >= module.start_week:
                conflicts.append(f"Пересечение: {ordered[index - 1].title} / {module.title}")
                suggestions.append(
                    f"Перенесите начало {module.title} на неделю {ordered[index - 1].end_week + 1} и проверьте окончание"
                )
        by_id = {m.id: m for m in modules}
        first = date(
            plan.first_week_start.year, plan.first_week_start.month, plan.first_week_start.day
        )
        last = first + timedelta(weeks=plan.weeks) - timedelta(days=1)
        for work in works:
            if work.module_id is not None and work.module_id not in by_id:
                conflicts.append(f"{work.title}: модуль из другого плана")
            deadline, exclusive = q.planned_deadline(work, plan)
            if deadline:
                due = (
                    deadline.value.astimezone(
                        timezone(timedelta(minutes=plan.week_utc_offset_minutes))
                    )
                    - (timedelta(microseconds=1) if exclusive else timedelta())
                ).date()
                if due > last or due < first:
                    warnings.append(f"{work.title}: срок {due:%d.%m.%Y} вне семестра")
                module = by_id.get(work.module_id)
                week = (due - first).days // 7 + 1
                if module and not module.start_week <= week <= module.end_week:
                    warnings.append(f"{work.title}: срок вне модуля {module.title}")
        return tuple(conflicts), tuple(warnings), tuple(suggestions)

    def preview_plan_change(
        self,
        offering_id,
        *,
        plan_values=None,
        module_changes=(),
        work_changes=(),
        reason="Изменение плана",
    ):
        snapshot = self.semester_plan(offering_id)
        if snapshot is None:
            raise ValueError("Сначала создайте план семестра")
        plan_values = dict(plan_values or {})
        work_changes = tuple(
            (
                id,
                revision,
                dict(values)
                | (
                    {
                        "exact_due_at": None,
                        "due_week": None,
                        "deadline_kind": "DATE_EXCLUSIVE" if values["due_date"] else "NONE",
                    }
                    if "due_date" in values and "deadline_kind" not in values
                    else {}
                ),
            )
            for id, revision, values in work_changes
        )
        allowed_plan = {"first_week_start", "weeks", "week_utc_offset_minutes", "configured"}
        allowed_module = {"title", "start_week", "end_week", "sort_order"}
        allowed_work = {
            "title",
            "number",
            "module_id",
            "issue_date",
            "due_date",
            "exact_due_at",
            "deadline_kind",
            "due_week",
            "cancelled",
            "sort_order",
        }
        if (
            set(plan_values) - allowed_plan
            or any(set(v) - allowed_module for _, _, v in module_changes)
            or any(set(v) - allowed_work for _, _, v in work_changes)
        ):
            raise ValueError("Недопустимое изменение плана")
        proposed = replace(snapshot.plan, **plan_values)
        modules, works = {m.id: m for m in snapshot.modules}, {w.id: w for w in snapshot.works}
        affected = []
        for id, revision, values in module_changes:
            stale(modules[id], revision)
            modules[id] = replace(modules[id], **values)
            affected.append(modules[id].title)
            affected.extend(w.title for w in works.values() if w.module_id == id)
        for id, revision, values in work_changes:
            stale(works[id], revision)
            works[id] = replace(works[id], **values)
            affected.append(works[id].title)
        conflicts, warnings, suggestions = self._validate_calendar(
            proposed, modules.values(), works.values()
        )
        return PlanPreview(
            snapshot.plan.id,
            snapshot.plan.revision,
            plan_values,
            tuple(module_changes),
            tuple(work_changes),
            warnings,
            conflicts,
            tuple(dict.fromkeys(affected)),
            suggestions,
            reason,
        )

    def apply_plan_change(self, preview, *, confirmed=False):
        if preview.conflicts:
            raise ValueError("; ".join(preview.conflicts))
        if preview.warnings and not confirmed:
            raise ValueError("Подтвердите срок за границами модуля/семестра")
        with self._transaction() as r:
            plan = self._require(r.semester_plans, preview.plan_id)
            stale(plan, preview.expected_revision)
            self._context(r, plan.offering_id)
            modules = {m.id: m for m in r.plan_modules.for_owner(plan.id)}
            works = {w.id: w for w in r.planned_works.for_owner(plan.id)}
            final_modules, final_works = dict(modules), dict(works)
            for id, revision, values in preview.module_changes:
                stale(modules[id], revision)
                final_modules[id] = replace(modules[id], **values)
            for id, revision, values in preview.work_changes:
                stale(works[id], revision)
                final_works[id] = replace(works[id], **values)
            proposed = replace(plan, **preview.plan_values)
            conflicts, warnings, _ = self._validate_calendar(
                proposed, final_modules.values(), final_works.values()
            )
            if conflicts or warnings and not confirmed:
                raise ValueError("; ".join(conflicts or warnings))
            plan = self._update(r.semester_plans, plan, **preview.plan_values)
            for id, _, values in preview.module_changes:
                self._update(r.plan_modules, modules[id], **values)
            for id, _, values in preview.work_changes:
                self._update(r.planned_works, works[id], **values)
            self._capture_plan(r, plan, preview.reason)
            return plan

    def add_plan_module(self, offering_id, title, start_week, end_week):
        with self._transaction() as r:
            plan = r.semester_plans.for_owner(offering_id)[0]
            self._context(r, offering_id)
            value = q.PlanModule(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                title=title.strip(),
                start_week=start_week,
                end_week=end_week,
            )
            conflicts, _, _ = self._validate_calendar(
                plan, [*r.plan_modules.for_owner(plan.id), value], ()
            )
            if conflicts:
                raise ValueError("; ".join(conflicts))
            r.plan_modules.insert(value)
            self._save_content_source(r, plan, module=value)
            plan = self._update(r.semester_plans, plan, configured=True)
            self._capture_plan(r, plan, "Добавлен модуль")
            return value

    def add_planned_work(
        self,
        offering_id,
        title,
        type,
        *,
        module_id=None,
        definition_id=None,
        issue_date=None,
        due_date=None,
        minimum=None,
        maximum=None,
        number="",
        confirmed=False,
    ):
        low, high = self._input_bounds(minimum, maximum) if minimum is not None else (None, None)
        with self._transaction() as r:
            plan = r.semester_plans.for_owner(offering_id)[0]
            self._context(r, offering_id)
            value = q.PlannedWork(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                module_id=module_id,
                definition_id=definition_id,
                title=title.strip(),
                type=type,
                number=number,
                issue_date=issue_date,
                due_date=due_date,
                deadline_kind="DATE_EXCLUSIVE" if due_date else "NONE",
                min_cents=low,
                max_cents=high,
            )
            conflicts, warnings, _ = self._validate_calendar(
                plan, r.plan_modules.for_owner(plan.id), [value]
            )
            if conflicts or warnings and not confirmed:
                raise ValueError("; ".join(conflicts or warnings))
            r.planned_works.insert(value)
            self._save_content_source(r, plan, work=value)
            plan = self._update(r.semester_plans, plan, configured=True)
            self._capture_plan(r, plan, "Добавлена работа")
            return value

    def issue_planned_work(self, planned_work_id, *, actual_issued_at=None):
        with self._transaction() as r:
            work = self._require(r.planned_works, planned_work_id)
            existing = r.issued_works.for_owner(work.id)
            if existing:
                return self._require(r.assessments, existing[0].assessment_id, historical=True)
            plan = self._require(r.semester_plans, work.semester_plan_id)
            self._context(r, plan.offering_id)
            if work.cancelled:
                raise ValueError("Работа отменена")
            issued_at = actual_issued_at or self._clock()
            if issued_at > self._clock():
                raise ValueError("Фактическая выдача не может быть в будущем")
            content = self._work_content(r, work)
            definition = next(
                (d for d in content.get("definitions", []) if d["id"] == str(work.definition_id)),
                {},
            )
            assessment = e.Assessment(
                metadata=self._meta(),
                offering_id=plan.offering_id,
                type=work.type,
                title=work.title,
                number=work.number,
                description=definition.get("description", ""),
                issued_at=issued_at,
                due_at=None,
                homework_definition_id=work.definition_id,
            )
            r.assessments.insert(assessment)
            r.issued_works.insert(
                q.IssuedWork(
                    metadata=self._meta(),
                    planned_work_id=work.id,
                    assessment_id=assessment.id,
                    actual_issued_at=issued_at,
                )
            )
            if work.definition_id:
                frozen = content
                for links_name, targets_name, cls, target in (
                    ("definition_topics", "assessment_topics", e.AssessmentTopic, "topic_id"),
                    ("definition_skills", "assessment_skills", e.AssessmentSkill, "skill_id"),
                ):
                    for source in frozen.get(links_name, []):
                        if source["definition_id"] == str(work.definition_id):
                            getattr(r, targets_name).insert(
                                cls(
                                    metadata=self._meta(),
                                    assessment_id=assessment.id,
                                    **{target: EntityId(source[target])},
                                )
                            )
                problems = {v["source"]["id"]: v for v in frozen.get("problem_snapshots", [])}
                for source in sorted(
                    frozen.get("definition_problems", []), key=lambda v: (v["sort_order"], v["id"])
                ):
                    if source["definition_id"] != str(work.definition_id):
                        continue
                    snapshot = problems.get(source["problem_id"])
                    if snapshot is None:
                        raise ValueError(
                            "Нет сохранённого содержания задачи; создайте новую явную версию"
                        )
                    self._add_assessment_problem(
                        r,
                        assessment,
                        EntityId(source["problem_id"]),
                        source["sort_order"],
                        snapshot=snapshot,
                    )
                from studium.domain import content as c
                from studium.domain import program as p

                for source in frozen.get("definition_files", {}).get(str(work.definition_id), []):
                    r.assessment_attachments.insert(
                        p.AssessmentAttachment(
                            metadata=self._meta(),
                            assessment_id=assessment.id,
                            file_asset_id=EntityId(source["file_asset_id"]),
                            role=c.MaterialFileRole(source["role"]),
                            sort_order=source["sort_order"],
                            caption=source.get("caption", ""),
                        )
                    )
            if work.min_cents is not None:
                r.scoring_rules.insert(
                    q.ScoringRule(
                        metadata=self._meta(),
                        assessment_id=assessment.id,
                        sequence=1,
                        min_cents=work.min_cents,
                        max_cents=work.max_cents,
                    )
                )
            return assessment

    def current_rule(self, assessment_id, r=None):
        rules = (r or self._r).scoring_rules.for_owner(assessment_id)
        return max(rules, key=lambda rule: rule.sequence, default=None)

    def change_scoring_rule(self, assessment_id, minimum, maximum):
        low, high = self._input_bounds(minimum, maximum)
        with self._transaction() as r:
            assessment = self._require(r.assessments, assessment_id)
            self._context(r, assessment.offering_id)
            previous = self.current_rule(assessment_id, r)
            rule = q.ScoringRule(
                metadata=self._meta(),
                assessment_id=assessment_id,
                sequence=previous.sequence + 1 if previous else 1,
                min_cents=low,
                max_cents=high,
            )
            r.scoring_rules.insert(rule)
            return rule

    def _submission_context(self, r, work_id, proposed=None):
        work = proposed or self._require(r.works, work_id)
        student = self._require(r.students, work.student_id)
        assessment = self._require(r.assessments, work.assessment_id)
        self._context(r, assessment.offering_id)
        if not student.active:
            raise ApplicationError("inactive_student")
        # The saved assignment and historical enrollment are both evidence.
        # Calendar end/archived bool are distinct from explicitly deleted rows.
        if not any(
            en.student_id == student.id and en.deleted_at is None
            for en in r.enrollments.for_offering(assessment.offering_id)
        ):
            raise ApplicationError("active_enrollment_required")
        return work, assessment

    def _insert_submission_work(self, r, proposed):
        _, context_assessment = self._submission_context(r, proposed.id, proposed)
        memberships = [
            en
            for en in r.enrollments.for_offering(context_assessment.offering_id)
            if en.student_id == proposed.student_id and en.deleted_at is None
        ]
        if not any(en.status.value == "ACTIVE" for en in memberships):
            enrollment = max(memberships, key=lambda en: (en.ended_at, en.id))
            r.late_work_authorizations.insert(
                q.LateWorkAuthorization(
                    metadata=self._meta(),
                    student_work_id=proposed.id,
                    enrollment_id=enrollment.id,
                    student_id=proposed.student_id,
                    assessment_id=proposed.assessment_id,
                )
            )
        r.works.insert(proposed)

    def register_submission(
        self, work_id, received_at, *, comment="", paths=(), offset=180, _proposed=None
    ):
        if received_at > self._clock():
            raise ValueError("Дата предъявления не может быть в будущем")
        with self._transaction() as r:
            self._submission_context(r, work_id, _proposed)
        metas = tuple(self._meta() for _ in paths)
        storage = self._file_adapters() if paths else None
        manager = (
            storage.import_files(tuple((Path(path), meta.id) for path, meta in zip(paths, metas)))
            if paths
            else nullcontext(())
        )
        with manager as imported:
            with self._transaction() as r:
                if _proposed:
                    self._insert_submission_work(r, _proposed)
                work, assessment = self._submission_context(r, work_id)
                history = r.attempts.history(work_id, include_deleted=True)
                attempt = e.Attempt(
                    metadata=self._meta(),
                    student_work_id=work_id,
                    attempt_no=max((a.attempt_no for a in history), default=0) + 1,
                    occurred_at=received_at,
                    result=AttemptResult.PRESENTED,
                    comment=comment,
                )
                rule = self.current_rule(assessment.id, r)
                submission = q.Submission(
                    metadata=self._meta(),
                    attempt_id=attempt.id,
                    received_at=received_at,
                    rule_id=rule.id if rule else None,
                    utc_offset_minutes=offset,
                )
                r.attempts.append(attempt)
                r.submissions.insert(submission)
                for index, (meta, payload) in enumerate(zip(metas, imported)):
                    asset = e.FileAsset(metadata=meta, **asdict(payload))
                    r.file_assets.insert(asset)
                    r.attempt_attachments.insert(
                        e.AttemptAttachment(
                            metadata=self._meta(),
                            attempt_id=attempt.id,
                            file_asset_id=asset.id,
                            sort_order=index,
                        )
                    )
                return submission

    _result_from_events = staticmethod(q.result_from_events)

    def _progress(self, work_id, attempts, submissions=(), reviews=()):
        from decimal import Decimal

        from studium.domain.services import StudentWorkProgress

        result = q.result_from_events(attempts, submissions, reviews)
        score = (
            Decimal(result.score) / 100
            if result.exact and result.score is not None
            else result.score
        )
        return StudentWorkProgress(
            result.status, score, sum(a.deleted_at is None for a in attempts)
        )

    def work_result(self, work_id):
        with self._transaction() as r:
            self._require(r.works, work_id, historical=True)
            return self._result_from_events(
                r.attempts.history(work_id), r.submissions.list(), r.reviews.list()
            )

    def submission_history(self, work_id):
        with self._transaction() as r:
            attempts = {a.id: a for a in r.attempts.history(work_id, include_deleted=True)}
            submissions = [
                s for s in r.submissions.list(include_deleted=True) if s.attempt_id in attempts
            ]
            reviews = r.reviews.list(include_deleted=True)
            grades = {g.review_id: g for g in r.review_grades.list(include_deleted=True)}
            files = r.review_files.list(include_deleted=True)
            returns = r.review_returns.list(include_deleted=True)
            return tuple(
                (
                    s,
                    attempts[s.attempt_id],
                    tuple(
                        (
                            v,
                            grades.get(v.id),
                            tuple(f for f in files if f.review_id == v.id),
                            tuple(t for t in returns if t.review_id == v.id),
                        )
                        for v in sorted(reviews, key=lambda v: v.review_seq)
                        if v.submission_id == s.id
                    ),
                )
                for s in sorted(submissions, key=lambda s: attempts[s.attempt_id].attempt_no)
            )

    def review_submission(
        self,
        submission_id,
        result,
        *,
        reviewed_at=None,
        score=None,
        rule_id=None,
        grade_kind=None,
        passed=None,
        label=None,
        comment="",
        paths=(),
        expected_review_seq=None,
    ):
        entered = (
            q.score_cents(score, fractional=self.fractional_scores_enabled())
            if score is not None
            else None
        )
        metas = tuple(self._meta() for _ in paths)
        storage = self._file_adapters() if paths else None
        manager = (
            storage.import_files(tuple((Path(path), meta.id) for path, meta in zip(paths, metas)))
            if paths
            else nullcontext(())
        )
        with manager as imported:
            with self._transaction() as r:
                submission = self._require(r.submissions, submission_id)
                attempt = self._require(r.attempts, submission.attempt_id)
                _, assessment = self._submission_context(r, attempt.student_work_id)
                reviews = r.reviews.for_owner(submission_id, include_deleted=True)
                sequence = max((v.review_seq for v in reviews), default=0)
                if expected_review_seq is not None and expected_review_seq != sequence:
                    raise RepositoryError(
                        RepositoryFailure.REVISION_CONFLICT, "Проверка уже изменилась"
                    )
                prior = self._result_from_events(
                    [attempt], [submission], reviews, target_attempt=attempt.id
                )
                if (
                    result == AttemptResult.SCORED
                    and prior.status == StudentWorkStatus.REVISION_REQUIRED
                ):
                    raise ValueError("После доработки требуется явный ACCEPTED")
                if assessment.type == AssessmentType.HOMEWORK and result == AttemptResult.REJECTED:
                    raise ApplicationError("homework_requires_revision")
                current = self.current_rule(assessment.id, r)
                if current and submission.rule_id != current.id and rule_id is None:
                    raise ValueError("Выберите прежнее или текущее правило явно")
                selected = rule_id or submission.rule_id
                if selected is not None and selected not in {
                    submission.rule_id,
                    current.id if current else None,
                }:
                    raise ValueError("Выберите правило этой сдачи или текущее")
                rule = (
                    self._require(r.scoring_rules, selected, historical=True) if selected else None
                )
                if rule and rule.assessment_id != assessment.id:
                    raise ApplicationError("learning_course_mismatch")
                if reviewed_at is not None and (
                    reviewed_at < submission.received_at or reviewed_at > self._clock()
                ):
                    raise ValueError("Дата проверки должна быть после сдачи и не в будущем")
                review = q.Review(
                    metadata=self._meta(),
                    submission_id=submission_id,
                    review_seq=sequence + 1,
                    result=result,
                    reviewed_at=reviewed_at or self._clock(),
                    rule_id=selected,
                    score_cents=entered,
                    min_cents=rule.min_cents if rule else None,
                    max_cents=rule.max_cents if rule else None,
                    comment=comment,
                )
                q.review_result(prior, review)
                evaluation = None
                if grade_kind == GradeKind.NUMERIC:
                    if entered is None:
                        raise ApplicationError("numeric_grade_requires_score")
                    evaluation = q.ReviewGrade(
                        metadata=self._meta(),
                        review_id=review.id,
                        kind=grade_kind,
                        score_cents=entered,
                        max_cents=rule.max_cents,
                    )
                elif grade_kind == GradeKind.PASS_FAIL:
                    if (
                        type(passed) is not bool
                        or passed
                        and result != AttemptResult.ACCEPTED
                        or not passed
                        and result not in {AttemptResult.NEEDS_REVISION, AttemptResult.REJECTED}
                    ):
                        raise ApplicationError("grade_result_mismatch")
                    evaluation = q.ReviewGrade(
                        metadata=self._meta(), review_id=review.id, kind=grade_kind, passed=passed
                    )
                elif grade_kind == GradeKind.TRADITIONAL:
                    if not label or not label.strip():
                        raise ApplicationError("invalid_grade")
                    evaluation = q.ReviewGrade(
                        metadata=self._meta(),
                        review_id=review.id,
                        kind=grade_kind,
                        label=label.strip(),
                    )
                r.reviews.insert(review)
                if evaluation:
                    r.review_grades.insert(evaluation)
                for index, (meta, payload) in enumerate(zip(metas, imported)):
                    asset = e.FileAsset(metadata=meta, **asdict(payload))
                    r.file_assets.insert(asset)
                    r.review_files.insert(
                        q.ReviewFile(
                            metadata=self._meta(),
                            review_id=review.id,
                            file_asset_id=asset.id,
                            sort_order=index,
                        )
                    )
                return review

    def record_review_return(self, review_id, returned_at, comment=""):
        with self._transaction() as r:
            review = self._require(r.reviews, review_id)
            if returned_at < review.reviewed_at or returned_at > self._clock():
                raise ValueError("Возврат должен быть после проверки и не в будущем")
            submission = self._require(r.submissions, review.submission_id)
            attempt = self._require(r.attempts, submission.attempt_id)
            self._submission_context(r, attempt.student_work_id)
            value = q.ReviewReturn(
                metadata=self._meta(), review_id=review_id, returned_at=returned_at, comment=comment
            )
            r.review_returns.insert(value)
            return value

    def review_queue(self, *, include_reviewed=False, now=None):
        now = now or self._clock()
        days, near = self.review_settings()
        with self._transaction() as r:
            submissions, reviews = r.submissions.list(), r.reviews.list()
            attempts = {a.id: a for a in r.attempts.list()}
            works = {w.id: w for w in r.works.list(include_deleted=include_reviewed)}
            assessments = {a.id: a for a in r.assessments.list(include_deleted=include_reviewed)}
            students = {s.id: s for s in r.students.list(include_deleted=include_reviewed)}
            offerings = {o.id: o for o in r.offerings.list(include_deleted=include_reviewed)}
            groups = {g.id: g for g in r.groups.list(include_deleted=include_reviewed)}
            courses = {c.id: c for c in r.courses.list(include_deleted=include_reviewed)}
            files = defaultdict(int)
            for file in r.attempt_attachments.list():
                files[file.attempt_id] += 1
            reviewed = {v.submission_id for v in reviews if v.result != AttemptResult.COMMENT_ONLY}
            last_reviews = {}
            for review in reviews:
                if review.result != AttemptResult.COMMENT_ONLY and (
                    review.submission_id not in last_reviews
                    or last_reviews[review.submission_id].review_seq < review.review_seq
                ):
                    last_reviews[review.submission_id] = review
            result = []
            for submission in submissions:
                attempt = attempts.get(submission.attempt_id)
                work = works.get(attempt.student_work_id) if attempt else None
                assessment = assessments.get(work.assessment_id) if work else None
                if not assessment or assessment.type not in {
                    AssessmentType.HOMEWORK,
                    AssessmentType.CONTROL_WORK,
                }:
                    continue
                offering = offerings.get(assessment.offering_id)
                if (
                    not offering
                    or work.student_id not in students
                    or offering.group_id not in groups
                    or offering.course_id not in courses
                ):
                    continue
                if submission.id in reviewed and not include_reviewed:
                    continue
                deadline, state = q.deadline_state(
                    submission.received_at,
                    now,
                    days=days,
                    near_hours=near,
                    offset=submission.utc_offset_minutes,
                )
                result.append(
                    QueueEntry(
                        submission,
                        attempt,
                        work,
                        assessment,
                        students[work.student_id],
                        groups[offering.group_id],
                        courses[offering.course_id],
                        deadline,
                        state,
                        files[attempt.id],
                        submission.id in reviewed,
                        last_reviews[submission.id].result
                        if submission.id in last_reviews
                        else None,
                    )
                )
            return tuple(
                sorted(
                    result,
                    key=lambda item: (
                        item.submission.received_at,
                        item.submission.created_at,
                        item.submission.id,
                    ),
                )
            )

    def set_required_works(self, module_id, student_id, work_ids, *, reason):
        with self._transaction() as r:
            module = self._require(r.plan_modules, module_id)
            plan = self._require(r.semester_plans, module.semester_plan_id)
            self._require(r.students, student_id)
            self._context(r, plan.offering_id)
            previous = [
                s
                for s in r.required_work_sets.for_owner(module_id, include_deleted=True)
                if s.student_id == student_id
            ]
            value = q.RequiredWorkSet(
                metadata=self._meta(),
                module_id=module_id,
                student_id=student_id,
                sequence=max((s.sequence for s in previous), default=0) + 1,
                reason=reason.strip(),
            )
            if not value.reason:
                raise ValueError("Укажите причину изменения обязательных работ")
            r.required_work_sets.insert(value)
            for id in set(work_ids):
                self._submission_context(r, id)
                r.required_work_bindings.insert(
                    q.RequiredWorkBinding(
                        metadata=self._meta(), required_set_id=value.id, student_work_id=id
                    )
                )
            return value

    def student_module_results(self, student_id):
        with self._transaction() as r:
            offering_ids = {
                en.offering_id
                for en in r.enrollments.list(include_deleted=True)
                if en.student_id == student_id
            }
            plans = {
                p.id: p
                for p in r.semester_plans.list(include_deleted=True)
                if p.offering_id in offering_ids
            }
            modules = [
                m for m in r.plan_modules.list(include_deleted=True) if m.semester_plan_id in plans
            ]
            sets = [s for s in r.required_work_sets.list() if s.student_id == student_id]
            bindings = r.required_work_bindings.list()
            attempts = r.attempts.list()
            submissions, reviews = r.submissions.list(), r.reviews.list()
            works = {
                w.id: w for w in r.works.list(include_deleted=True) if w.student_id == student_id
            }
            result = []
            for module in modules:
                selected = max(
                    (s for s in sets if s.module_id == module.id),
                    key=lambda s: s.sequence,
                    default=None,
                )
                required = tuple(
                    b.student_work_id
                    for b in bindings
                    if selected and b.required_set_id == selected.id
                )
                debt = tuple(
                    id
                    for id in required
                    if id not in works
                    or self._result_from_events(
                        [a for a in attempts if a.student_work_id == id], submissions, reviews
                    ).status
                    != StudentWorkStatus.ACCEPTED
                )
                result.append(
                    StudentModuleResult(
                        module,
                        student_id,
                        "unknown" if selected is None else "open" if debt else "closed",
                        required,
                        debt,
                        selected.id if selected else None,
                        plans[module.semester_plan_id].offering_id,
                    )
                )
            return tuple(result)

    def student_work_details(self, student_id, *, offering_id=None, kind=None, work_ids=None):
        choices = self.student_submission_choices(student_id)
        with self._transaction() as r:
            histories = defaultdict(list)
            for attempt in r.attempts.list():
                histories[attempt.student_work_id].append(attempt)
            submissions, reviews = r.submissions.list(), r.reviews.list()
            return tuple(
                (
                    a,
                    w,
                    f"{term.name} · {group.number} · {course.name}",
                    self._result_from_events(histories[w.id], submissions, reviews) if w else None,
                )
                for a, w, group, course, term in choices
                if (offering_id is None or a.offering_id == offering_id)
                and (kind is None or a.type == kind)
                and (work_ids is None or w and w.id in work_ids)
            )

    def create_answer_template(self, title, answers):
        value = q.AnswerTemplate(
            metadata=self._meta(), title=title.strip(), schema_json=document(answers)
        )
        self._r.answer_templates.insert(value)
        return value

    def restore_student_submission_context(
        self, student_id, assessment_id, *, confirmed=False, reason=""
    ):
        existing = self.find_student_work(student_id, assessment_id)
        proposed = (
            None
            if existing
            else e.StudentWork(
                metadata=self._meta(), student_id=student_id, assessment_id=assessment_id
            )
        )
        return self.restore_debt_context(
            (existing or proposed).id, confirmed=confirmed, reason=reason, _proposed=proposed
        )

    def restore_debt_context(self, work_id, *, confirmed=False, reason="", _proposed=None):
        """Explicit restoration of mutable context; immutable facts stay untouched."""
        if not confirmed or not reason.strip():
            raise ValueError("Подтвердите восстановление исходного контекста и укажите причину")
        with self._transaction() as r:
            work = _proposed or self._require(r.works, work_id, historical=True)
            assessment = self._require(r.assessments, work.assessment_id, historical=True)
            context = self._context(r, assessment.offering_id, historical=True)
            student = self._require(r.students, work.student_id, historical=True)
            enrollments = [
                en
                for en in r.enrollments.list(include_deleted=True)
                if en.student_id == student.id and en.offering_id == context.offering.id
            ]
            if not enrollments:
                raise ValueError("Нет подтверждённого исторического участия")
            enrollment = max(enrollments, key=lambda en: (en.enrolled_at, en.id))
            targets = [
                ("terms", context.term),
                ("courses", context.course),
                ("groups", context.group),
                ("offerings", context.offering),
                ("students", student),
                ("enrollments", enrollment),
                ("assessments", assessment),
                ("works", work),
            ]
            if _proposed:
                targets = targets[:-1]
            before = {
                name: record(value)
                | {"deleted_at": value.deleted_at, "active": getattr(value, "active", None)}
                for name, value in targets
            }
            if _proposed:
                before["work_absent"] = True
            changed = False
            for name, original in targets:
                if original.deleted_at is None and (name != "students" or original.active):
                    continue
                metadata = replace(original.metadata.touch(self._clock()), deleted_at=None)
                restored = replace(
                    original, metadata=metadata, **({"active": True} if name == "students" else {})
                )
                if name == "works":
                    r.works.restore(
                        original.id, expected_revision=original.revision, at=self._clock()
                    )
                else:
                    getattr(r, name).update(restored, expected_revision=original.revision)
                changed = True
            if _proposed:
                self._insert_submission_work(r, _proposed)
                changed = True
            if changed:
                r.debt_restorations.insert(
                    q.DebtRestoration(
                        metadata=self._meta(),
                        student_work_id=work_id,
                        before_json=document(before),
                        reason=reason.strip(),
                    )
                )
            return self._require(r.works, work_id)

    def answer_templates(self):
        return tuple(self._r.answer_templates.list())

    def work_is_late(self, assessment_id, instant=None):
        instant = instant or self._clock()
        with self._transaction() as r:
            links = [i for i in r.issued_works.list() if i.assessment_id == assessment_id]
            if not links:
                assessment = self._require(r.assessments, assessment_id, historical=True)
                return instant > assessment.due_at if assessment.due_at else None
            work = self._require(r.planned_works, links[0].planned_work_id, historical=True)
            plan = self._require(r.semester_plans, work.semester_plan_id, historical=True)
            if work.deadline_kind == "EXACT_INCLUSIVE" and work.exact_due_at:
                return instant > work.exact_due_at
            if work.deadline_kind == "WEEK_ONLY" and work.due_week:
                first = date(
                    plan.first_week_start.year,
                    plan.first_week_start.month,
                    plan.first_week_start.day,
                )
                last = first + timedelta(weeks=work.due_week) - timedelta(days=1)
                return instant >= q.day_boundary(
                    LocalDate.parse(last.isoformat()), plan.week_utc_offset_minutes
                )
            return (
                instant >= q.day_boundary(work.due_date, plan.week_utc_offset_minutes)
                if work.due_date
                else None
            )

    def student_submission_choices(self, student_id):
        with self._transaction() as r:
            memberships = {
                en.offering_id
                for en in r.enrollments.list(include_deleted=True)
                if en.student_id == student_id
            }
            offerings = {
                o.id: o for o in r.offerings.list(include_deleted=True) if o.id in memberships
            }
            groups = {g.id: g for g in r.groups.list(include_deleted=True)}
            courses = {c.id: c for c in r.courses.list(include_deleted=True)}
            terms = {t.id: t for t in r.terms.list(include_deleted=True)}
            works = {
                w.assessment_id: w
                for w in r.works.list(include_deleted=True)
                if w.student_id == student_id
            }
            return tuple(
                (a, works.get(a.id), groups[o.group_id], courses[o.course_id], terms[o.term_id])
                for a in r.assessments.list(include_deleted=True)
                if (o := offerings.get(a.offering_id))
            )

    def register_student_submission(self, student_id, assessment_id, received_at, **values):
        existing = self._r.works.find_for_student(student_id, assessment_id, include_deleted=True)
        proposed = (
            None
            if existing
            else e.StudentWork(
                metadata=self._meta(), student_id=student_id, assessment_id=assessment_id
            )
        )
        return self.register_submission(
            (existing or proposed).id, received_at, _proposed=proposed, **values
        )

    def update_answer_template(self, original, title, answers):
        q.validate_answers(answers)
        return self._update(
            self._r.answer_templates, original, title=title.strip(), schema_json=document(answers)
        )

    def splitter_sizes(self, key):
        return self._preferences.splitter_sizes(key) if self._preferences else ()

    def save_splitter_sizes(self, key, sizes):
        if self._preferences:
            self._preferences.save_splitter_sizes(key, sizes)

    def scoring_rule(self, rule_id):
        return self._require(self._r.scoring_rules, rule_id, historical=True)

    def set_required_assessments(self, module_id, student_id, assessment_ids, *, reason):
        from contextlib import contextmanager
        from copy import copy

        with self._transaction() as r:
            command = copy(self)
            command._r = r

            @contextmanager
            def transaction():
                yield r

            command._transaction = transaction
            ids = tuple(command.get_or_create_work(student_id, id).id for id in assessment_ids)
            return command.set_required_works(module_id, student_id, ids, reason=reason)

    def module_required_choices(self, module_id, student_id):
        with self._transaction() as r:
            module = self._require(r.plan_modules, module_id)
            plan = self._require(r.semester_plans, module.semester_plan_id)
            planned_ids = {
                w.id
                for w in r.planned_works.for_owner(plan.id)
                if w.module_id == module_id and not w.cancelled
            }
            assessment_ids = {
                i.assessment_id for i in r.issued_works.list() if i.planned_work_id in planned_ids
            }
            latest = max(
                (
                    v
                    for v in r.required_work_sets.for_owner(module_id)
                    if v.student_id == student_id
                ),
                key=lambda v: v.sequence,
                default=None,
            )
            works = {w.id: w.assessment_id for w in r.works.list()}
            selected = {
                works[b.student_work_id]
                for b in r.required_work_bindings.list()
                if latest and b.required_set_id == latest.id and b.student_work_id in works
            }
            return tuple(a for a in r.assessments.list() if a.id in assessment_ids), selected

    def select_plan_content(self, offering_id, version_id, course_semester, *, expected_revision):
        snapshot = self.semester_plan(offering_id)
        if snapshot and (snapshot.modules or snapshot.works):
            raise ValueError("Непустой план требует preview и подтверждённого переназначения")
        preview = self.preview_plan_content(
            offering_id, version_id, course_semester, expected_revision=expected_revision
        )
        return self.apply_plan_content(preview, confirmed=True)

    def preview_new_planned_work(self, offering_id, title, type, **values):
        with self._transaction() as r:
            self._context(r, offering_id)
            plans = r.semester_plans.for_owner(offering_id)
            if not plans:
                raise ValueError("Сначала сохраните план семестра")
            plan = plans[0]
            low, high = self._input_bounds(values.pop("minimum", None), values.pop("maximum", None))
            values.pop("confirmed", None)
            work = q.PlannedWork(
                metadata=self._meta(),
                semester_plan_id=plan.id,
                title=title,
                type=type,
                min_cents=low,
                max_cents=high,
                **values,
            )
            conflicts, warnings, suggestions = self._validate_calendar(
                plan, r.plan_modules.for_owner(plan.id), [work]
            )
            return tuple(conflicts), tuple(warnings), tuple(suggestions)
