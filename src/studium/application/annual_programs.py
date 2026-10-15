"""Annual program commands over existing repositories and immutable content snapshots."""

import json
from copy import deepcopy
from dataclasses import dataclass

from studium.application.errors import ApplicationError
from studium.application.qa_services import document, record, stale
from studium.domain import annual_program as a
from studium.domain import content as c
from studium.domain import qa as q
from studium.domain.enums import AssessmentType
from studium.domain.value_objects import EntityId


@dataclass(frozen=True)
class ProgramUsage:
    version: q.ProgramVersion
    plan: q.SemesterPlan
    group: str
    term: str


class AnnualProgramService:
    def list_program_drafts(self, course_id=None):
        programs = {p.id for p in self.list_course_programs(course_id)}
        return tuple(d for d in self._r.program_drafts.list() if d.course_program_id in programs)

    def get_program_draft(self, id):
        return self._require(self._r.program_drafts, id)

    def create_program_draft(
        self, course_id, title="Новая программа", *, previous=None, independent=False
    ):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            if previous:
                previous = self._require(r.program_versions, previous.id, historical=True)
                source_program = self._require(r.course_programs, previous.course_program_id)
                if source_program.course_id != course_id:
                    raise ApplicationError("learning_course_mismatch")
                data = json.loads(previous.content_json)
                if "annual" not in data:
                    data["annual"] = self._legacy_annual(r, source_program, previous, data)
                if independent:
                    data["annual"] = a.copy_fragment(data["annual"])
                    data["annual"]["passport"]["title"] += " — копия"
                program = source_program
            else:
                data = {"annual": a.new_annual(title)}
            if not previous or independent:
                program = q.CourseProgram(
                    metadata=self._meta(),
                    course_id=course_id,
                    title=data["annual"]["passport"]["title"] or title,
                )
                r.course_programs.insert(program)
            draft = a.ProgramDraft(
                metadata=self._meta(),
                course_program_id=program.id,
                base_version_id=previous.id if previous and not independent else None,
                content_json=document(data),
            )
            r.program_drafts.insert(draft)
            return draft

    def _legacy_annual(self, r, program, version, data):
        for field, legacy_name, target in (
            ("topic_ids", "program_topics", "topic_id"),
            ("skill_ids", "program_skills", "skill_id"),
            ("seminar_material_ids", "program_materials", "seminar_material_id"),
            ("literature_item_ids", "program_literature", "literature_item_id"),
            ("file_asset_ids", "program_attachments", "file_asset_id"),
        ):
            data.setdefault(field, sorted({v[target] for v in data.get(legacy_name, [])}))
        data["topic_ids"] = sorted(
            set(data["topic_ids"]) | {v["topic_id"] for v in data.get("module_topics", [])}
        )
        annual = a.new_annual(program.title)
        annual["semesters"] = []
        annual["passport"].update(
            label=version.label,
            notes=program.notes,
            directions=[
                {"code": d.code, "name": d.name}
                for d in r.directions.list()
                if d.id in self.version_direction_ids(version.id)
            ],
        )
        annual["legacy_unmapped_modules"] = []
        for old in data.get("modules", []):
            ordinal = old.get("course_semester")
            if not ordinal:
                annual["legacy_unmapped_modules"].append(deepcopy(old))
                continue
            semester = next((s for s in annual["semesters"] if s["number"] == ordinal), None)
            if semester is None:
                semester = {
                    "key": a.key(),
                    "number": ordinal,
                    "title": f"Семестр {ordinal}",
                    "weeks": max(17, old["end_week"]),
                    "modules": [],
                }
                annual["semesters"].append(semester)
            semester["weeks"] = max(semester["weeks"], old["end_week"])
            module = {
                "key": old.get("key", old.get("id", a.key())),
                "title": old["title"],
                "start_week": old["start_week"],
                "end_week": old["end_week"],
                "lessons": [],
                "works": [],
            }
            definitions = {str(v["id"]): v for v in data.get("definitions", [])}
            for w in data.get("works", []):
                if w.get("module_key", w.get("module_id")) == module["key"]:
                    definition = definitions.get(str(w["definition_id"]), {})
                    module["works"].append(
                        dict(
                            w,
                            key=a.key(),
                            title=definition.get("title", w.get("title", "")),
                            category=definition.get("type", "HOMEWORK"),
                        )
                    )
            semester["modules"].append(module)
        return annual

    def _annual_dependencies(self, r, course_id, data, *, publish=False):
        """Keep recorded dependencies; capture only newly selected library identities."""
        annual = data["annual"]
        a.validate(annual, ready=publish)
        if publish and annual.get("legacy_unmapped_modules"):
            raise ValueError(
                "Семестр старых модулей неизвестен: явно сопоставьте их в годовом плане"
            )
        topic_ids, skill_ids = set(data.get("topic_ids", [])), set(data.get("skill_ids", []))
        for s in annual["semesters"]:
            for m in s["modules"]:
                for lesson in m["lessons"]:
                    topic_ids.update(lesson["topic_ids"])
        for o in annual["outcomes"]:
            topic_ids.update(o.get("topic_ids", []))
            skill_ids.update(o.get("skill_ids", []))
        frozen_definitions = {str(v["id"]) for v in data.get("definitions", [])}
        for semester in annual["semesters"]:
            for module in semester["modules"]:
                for work in module["works"]:
                    if work.get("definition_id"):
                        definition = self._require(
                            r.homework_definitions,
                            EntityId(work["definition_id"]),
                            historical=work["definition_id"] in frozen_definitions,
                        )
                        if definition.course_id != course_id:
                            raise ApplicationError("learning_course_mismatch")
        for field, repository in (
            ("seminar_material_ids", r.seminar_materials),
            ("literature_item_ids", r.literature_items),
        ):
            for id in data.get(field, []):
                value = self._require(repository, EntityId(id), historical=True)
                if value.course_id not in (None, course_id):
                    raise ApplicationError("learning_course_mismatch")
        for id in data.get("file_asset_ids", []):
            self._require(r.file_assets, EntityId(id), historical=True)
        # Hierarchy is included, with cycle checks even for a partially filled draft.
        existing_topics = {str(v["id"]): v for v in data.get("topic_ids_snapshots", [])}

        def topic(id, path):
            if id in path:
                raise ValueError("Цикл иерархии тем")
            value = existing_topics.get(id)
            if value is None:
                row = self._require(r.topics, EntityId(id))
                if row.course_id != course_id:
                    raise ApplicationError("learning_course_mismatch")
                value = json.loads(document(record(row)))
                existing_topics[id] = value
            parent = value.get("parent_topic_id")
            if parent:
                topic(str(parent), path | {id})

        for id in sorted(topic_ids):
            topic(str(id), set())
        if "topic_skill_links" not in data:
            data["topic_skill_links"] = []
        recorded_topics = {v["topic_id"] for v in data["topic_skill_links"]}
        for link in r.topic_skills.list():
            if str(link.topic_id) in existing_topics and str(link.topic_id) not in recorded_topics:
                data["topic_skill_links"].append(
                    {"topic_id": str(link.topic_id), "skill_id": str(link.skill_id)}
                )
        skill_ids.update(v["skill_id"] for v in data["topic_skill_links"])
        data["topic_ids"] = sorted(existing_topics)
        data["topic_ids_snapshots"] = list(existing_topics.values())
        existing_skills = {str(v["id"]): v for v in data.get("skill_ids_snapshots", [])}
        for id in skill_ids:
            if str(id) not in existing_skills:
                row = self._require(r.skills, EntityId(id))
                if row.course_id != course_id:
                    raise ApplicationError("learning_course_mismatch")
                existing_skills[str(id)] = json.loads(document(record(row)))
        data["skill_ids"] = sorted(existing_skills)
        data["skill_ids_snapshots"] = list(existing_skills.values())
        for p in annual["prerequisites"]:
            if p.get("course_id"):
                self._require(r.courses, EntityId(p["course_id"]), historical=True)
        self._assert_saved_taxonomy_live(r, data)
        return data

    def save_program_draft(self, original, content):
        data = deepcopy(content)
        with self._transaction() as r:
            current = self._require(r.program_drafts, original.id)
            stale(current, original.revision)
            program = self._require(r.course_programs, current.course_program_id)
            data = self._annual_dependencies(r, program.course_id, data)
            # Fractional OFF allows unchanged recorded bounds, never new fractional inputs.
            if not self.fractional_scores_enabled():
                old = json.loads(current.content_json)

                def scores(value):
                    result = {}
                    for s in value["annual"]["semesters"]:
                        for m in s["modules"]:
                            for w in m["works"]:
                                result[w["key"]] = (w.get("min_cents"), w.get("max_cents"))
                    for b in value["annual"]["budgets"]:
                        result[b["key"]] = (b["max_cents"],)
                    return result

                before = scores(old)
                for id, values in scores(data).items():
                    if values != before.get(id) and any(v is not None and v % 100 for v in values):
                        raise ValueError("Дробный ввод выключен")
            return self._update(r.program_drafts, current, content_json=document(data))

    def check_program_draft(self, original):
        data = json.loads(original.content_json)
        issues = list(a.validate(data["annual"]))
        if data["annual"].get("legacy_unmapped_modules"):
            issues.append("Семестр старых модулей неизвестен")
        return tuple(issues)

    def _freeze_annual(self, r, course_id, data):
        """One snapshot, with compatibility projections for the existing plan/issuance."""
        data = self._annual_dependencies(r, course_id, deepcopy(data), publish=True)
        source_files = q.snapshot_file_ids(
            {
                name: data.get(name, {})
                for name in ("definition_files", "problem_snapshots", "material_files")
            }
        )
        data.setdefault(
            "document_file_ids", sorted(set(data.get("file_asset_ids", [])) - source_files)
        )
        selected = {
            str(w["definition_id"])
            for sem in data["annual"]["semesters"]
            for mod in sem["modules"]
            for w in mod["works"]
            if w.get("definition_id")
        }
        data["definitions"] = [v for v in data.get("definitions", []) if str(v["id"]) in selected]
        for name in ("definition_topics", "definition_skills", "definition_problems"):
            data[name] = [v for v in data.get(name, []) if str(v["definition_id"]) in selected]
        data["definition_files"] = {
            id: links for id, links in data.get("definition_files", {}).items() if id in selected
        }
        needed_problems = {str(v["problem_id"]) for v in data["definition_problems"]}
        data["problem_snapshots"] = [
            v
            for v in data.get("problem_snapshots", [])
            if str(v["source"]["id"]) in needed_problems
        ]
        if needed_problems - {str(v["source"]["id"]) for v in data["problem_snapshots"]}:
            raise ValueError(
                "В старой версии отсутствуют снимки задач. Явно обновите библиотечные источники новой редакции."
            )
        for field, kind in (
            ("seminar_material_ids", "seminars"),
            ("literature_item_ids", "literature"),
        ):
            data[field + "_snapshots"] = [
                v for v in data.get(field + "_snapshots", []) if str(v["id"]) in data.get(field, [])
            ]
            data.setdefault("material_files", {})[kind] = {
                id: links
                for id, links in data.get("material_files", {}).get(kind, {}).items()
                if id in data.get(field, [])
            }
        definitions = {str(v["id"]): v for v in data.get("definitions", [])}
        data["modules"], data["works"] = [], []
        for s in data["annual"]["semesters"]:
            for order, m in enumerate(s["modules"]):
                data["modules"].append(
                    {k: deepcopy(v) for k, v in m.items() if k not in {"lessons", "works"}}
                    | {"course_semester": s["number"], "sort_order": order}
                )
                for index, w in enumerate(m["works"]):
                    if not w.get("definition_id"):
                        definition = c.HomeworkDefinition(
                            metadata=self._meta(),
                            course_id=course_id,
                            title=w["title"],
                            type=AssessmentType(w["category"]),
                            description=w.get("rules", ""),
                        )
                        r.homework_definitions.insert(definition)
                        w["definition_id"] = str(definition.id)
                    id = str(w["definition_id"])
                    if id not in definitions:
                        frozen = json.loads(
                            self._content_snapshot(r, course_id, {"works": [{"definition_id": id}]})
                        )
                        for field in (
                            "definitions",
                            "definition_topics",
                            "definition_skills",
                            "definition_problems",
                            "problem_snapshots",
                        ):
                            data.setdefault(field, []).extend(
                                v for v in frozen[field] if v not in data.get(field, [])
                            )
                        data.setdefault("definition_files", {}).update(frozen["definition_files"])
                        definitions.update({str(v["id"]): v for v in frozen["definitions"]})
                    data["works"].append(
                        dict(w, module_key=m["key"], course_semester=s["number"], sort_order=index)
                    )
        for field in ("seminar_material_ids", "literature_item_ids"):
            existing = {str(v["id"]): v for v in data.get(field + "_snapshots", [])}
            for id in data.get(field, []):
                if str(id) not in existing:
                    frozen = json.loads(self._content_snapshot(r, course_id, {field: [id]}))
                    data.setdefault(field + "_snapshots", []).extend(frozen[field + "_snapshots"])
                    for kind, values in frozen["material_files"].items():
                        data.setdefault("material_files", {}).setdefault(kind, {}).update(values)
        data["file_asset_ids"] = sorted(
            set(data.get("document_file_ids", data.get("file_asset_ids", [])))
            | q.snapshot_file_ids(
                {
                    "definition_files": data.get("definition_files", {}),
                    "problem_snapshots": data.get("problem_snapshots", []),
                    "material_files": data.get("material_files", {}),
                }
            )
        )
        # Definition/problem classifications also receive concrete frozen references.
        for kind in ("topic", "skill"):
            data[kind + "_ids"] = sorted(
                set(data.get(kind + "_ids", []))
                | {str(v[kind + "_id"]) for v in data.get("definition_" + kind + "s", [])}
                | {
                    str(id)
                    for p in data.get("problem_snapshots", [])
                    for id in p.get(kind + "_ids", [])
                }
            )
        self._annual_dependencies(r, course_id, data, publish=True)
        return data

    def publish_program_draft(self, original):
        with self._transaction() as r:
            draft = self._require(r.program_drafts, original.id)
            stale(draft, original.revision)
            program = self._require(r.course_programs, draft.course_program_id)
            incoming = json.loads(draft.content_json)
            incoming.pop("exchange_origin", None)
            incoming.pop("exchange_local_ids", None)
            data = self._freeze_annual(r, program.course_id, incoming)
            version = self._insert_annual_version(r, program, data)
            r.program_drafts.soft_delete(
                draft.id, expected_revision=draft.revision, at=self._clock()
            )
            return version

    def _insert_annual_version(self, r, program, data):
        versions = r.program_versions.for_owner(program.id, include_deleted=True)
        version = q.ProgramVersion(
            metadata=self._meta(),
            course_program_id=program.id,
            version_no=max((v.version_no for v in versions), default=0) + 1,
            label=data["annual"]["passport"]["label"],
            content_json=document(data),
        )
        r.program_versions.insert(version)
        self._version_references(r, version)
        by_code = {d.normalized_key: d for d in r.directions.list(include_deleted=True)}
        for spec in data["annual"]["passport"]["directions"]:
            code, normalized = q.direction_identity(spec["code"])
            direction = by_code.get(normalized)
            if direction is None:
                direction = q.Direction(
                    metadata=self._meta(), code=code, normalized_key=normalized, name=spec["name"]
                )
                r.directions.insert(direction)
                by_code[normalized] = direction
            # Snapshot retains incoming name; existing local directory is never overwritten.
            r.program_directions.insert(
                q.ProgramDirection(
                    metadata=self._meta(), program_version_id=version.id, direction_id=direction.id
                )
            )
        return version

    def program_usage(self, program_id):
        with self._transaction() as r:
            versions = {
                v.id: v for v in r.program_versions.for_owner(program_id, include_deleted=True)
            }
            result = []
            for plan in r.semester_plans.list():
                if plan.program_version_id in versions:
                    offering = self._require(r.offerings, plan.offering_id, historical=True)
                    result.append(
                        ProgramUsage(
                            versions[plan.program_version_id],
                            plan,
                            self._require(r.groups, offering.group_id, historical=True).number,
                            self._require(r.terms, offering.term_id, historical=True).name,
                        )
                    )
            return tuple(result)

    def planned_program_lessons(self, offering_id):
        plans = self._r.semester_plans.for_owner(offering_id)
        return tuple(self._r.plan_lessons.for_owner(plans[0].id)) if plans else ()

    def update_program_plan_lesson(self, original, *, week, topic_ids, reason):
        if not reason.strip():
            raise ValueError("Укажите причину изменения плана")
        with self._transaction() as r:
            current = self._require(r.plan_lessons, original.id)
            stale(current, original.revision)
            plan = self._require(r.semester_plans, current.semester_plan_id)
            self._context(r, plan.offering_id)
            if week is not None and (type(week) is not int or not 1 <= week <= plan.weeks):
                raise ValueError("Неделя за границами рабочего плана")
            offering = self._require(r.offerings, plan.offering_id)
            for id in topic_ids:
                if self._require(r.topics, EntityId(id)).course_id != offering.course_id:
                    raise ApplicationError("learning_course_mismatch")
            data = json.loads(current.current_json) | {
                "week": week,
                "topic_ids": list(map(str, topic_ids)),
            }
            result = self._update(r.plan_lessons, current, current_json=document(data))
            plan = self._update(r.semester_plans, plan)
            self._capture_plan(r, plan, reason)
            return result

    def bind_actual_program_lesson(self, original, lesson_id):
        """Explicit existing fact binding; actual LessonTopic remains separately editable."""
        with self._transaction() as r:
            current = self._require(r.plan_lessons, original.id)
            stale(current, original.revision)
            lesson = self._require(r.lessons, lesson_id)
            plan = self._require(r.semester_plans, current.semester_plan_id)
            if lesson.course_offering_id != plan.offering_id or current.lesson_id:
                raise ValueError("Занятие другой группы или факт уже связан")
            result = self._update(r.plan_lessons, current, lesson_id=lesson_id)
            plan = self._update(r.semester_plans, plan)
            self._capture_plan(
                r, plan, "Связано фактическое занятие; содержание программы сохранено"
            )
            return result

    def annual_version_content(self, version):
        data = json.loads(version.content_json)
        if "annual" not in data:
            with self._transaction() as r:
                program = self._require(
                    r.course_programs, version.course_program_id, historical=True
                )
                data["annual"] = self._legacy_annual(r, program, version, data)
        return data

    def attach_program_documents(self, original, paths):
        from dataclasses import asdict
        from pathlib import Path

        from studium.domain.entities import FileAsset

        storage = self._file_adapters()
        metadata = [self._meta() for _ in paths]
        with storage.import_files(
            [(Path(path), meta.id) for path, meta in zip(paths, metadata, strict=True)]
        ) as imported:
            with self._transaction() as r:
                current = self._require(r.program_drafts, original.id)
                stale(current, original.revision)
                data = json.loads(current.content_json)
                ids = list(data.get("file_asset_ids", []))
                documents = list(data.get("document_file_ids", []))
                for meta, info in zip(metadata, imported, strict=True):
                    asset = FileAsset(metadata=meta, **asdict(info))
                    r.file_assets.insert(asset)
                    ids.append(str(asset.id))
                    documents.append(str(asset.id))
                data["file_asset_ids"] = ids
                data["document_file_ids"] = documents
                result = self._update(r.program_drafts, current, content_json=document(data))
        return result

    def actual_program_lesson_choices(self, offering_id):
        return tuple(v for v in self._r.lessons.list() if v.course_offering_id == offering_id)

    def actual_program_lesson_content(self, planned):
        if not planned.lesson_id:
            return None, ()
        lesson = self._require(self._r.lessons, planned.lesson_id, historical=True)
        topics = tuple(
            self._require(self._r.topics, v.topic_id, historical=True)
            for v in self._r.lesson_topics.for_owner(lesson.id)
        )
        return lesson, topics

    def refresh_program_draft_sources(self, original):
        with self._transaction() as r:
            current = self._require(r.program_drafts, original.id)
            stale(current, original.revision)
            data = json.loads(current.content_json)
            source_files = q.snapshot_file_ids(
                {
                    name: data.get(name, {})
                    for name in ("definition_files", "problem_snapshots", "material_files")
                }
            )
            data.setdefault(
                "document_file_ids", sorted(set(data.get("file_asset_ids", [])) - source_files)
            )
            for field in (
                "definitions",
                "definition_topics",
                "definition_skills",
                "definition_problems",
                "problem_snapshots",
                "seminar_material_ids_snapshots",
                "literature_item_ids_snapshots",
            ):
                data.pop(field, None)
            data["definition_files"], data["material_files"] = {}, {}
            data["file_asset_ids"] = list(data["document_file_ids"])
            return self._update(r.program_drafts, current, content_json=document(data))
