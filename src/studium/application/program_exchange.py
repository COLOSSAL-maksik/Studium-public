"""Portable program allowlists and import orchestration; no database/Qt coupling."""

import hashlib
import json
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from studium.application.qa_services import document, record
from studium.domain import annual_program as a
from studium.domain import content as c
from studium.domain import entities as e
from studium.domain import program as p
from studium.domain import qa as q
from studium.domain.enums import AssessmentType, LessonType
from studium.domain.value_objects import EntityId, EntityMetadata, UtcInstant

# These are program/library fields only. Metadata, facts and arbitrary extension JSON are excluded.
ENTITY_FIELDS = {
    "topics": ("id", "title", "parent_topic_id", "description", "sort_order"),
    "skills": ("id", "title", "description", "sort_order"),
    "definitions": (
        "id",
        "revision",
        "title",
        "label",
        "description",
        "type",
        "notes",
        "tags_json",
        "details_json",
    ),
    "problems": (
        "id",
        "revision",
        "title",
        "statement",
        "correct_answer",
        "solution",
        "difficulty",
        "notes",
        "tags_json",
        "details_json",
        "identifier",
        "purposes_json",
        "is_family",
        "family_id",
        "variant_code",
        "parameters",
    ),
    "seminars": (
        "id",
        "title",
        "notes",
        "tags_json",
        "details_json",
        "plan_text",
        "full_text",
        "type",
    ),
    "literature": ("id", "title", "notes", "tags_json", "details_json", "authors", "year", "type"),
}
ANNUAL_FIELDS = {
    "passport": ("title", "label", "academic_year", "notes", "academic_hour_minutes", "directions"),
    "semesters": ("key", "number", "title", "weeks", "modules"),
    "modules": ("key", "title", "start_week", "end_week", "lessons", "works"),
    "lessons": ("key", "kind", "title", "hours", "topic_ids", "week", "notes"),
    "works": ("key", "title", "category", "min_cents", "max_cents", "rules", "definition_id"),
    "outcomes": (
        "key",
        "category",
        "code",
        "text",
        "topic_ids",
        "skill_ids",
        "module_keys",
        "work_keys",
    ),
    "prerequisites": ("key", "discipline", "content"),
    "loads": ("key", "semester_key", "module_key", "kind", "hours", "notes"),
    "norms": ("key", "semester_key", "kind", "hours"),
    "budgets": ("key", "module_key", "category", "max_cents"),
    "directions": ("code", "name"),
}


def pick(value, names):
    return {k: deepcopy(value[k]) for k in names if k in value}


def annual_allowlist(annual):
    result = pick(annual, ("schema_version", "scoring", "not_applicable"))
    for name in ("passport", "semesters", "outcomes", "prerequisites", "loads", "norms", "budgets"):

        def visit(value, section):
            if isinstance(value, list):
                return [visit(v, section) for v in value]
            result = pick(value, ANNUAL_FIELDS[section])
            for child in ("directions", "modules", "lessons", "works"):
                if child in result:
                    result[child] = visit(result[child], child)
            return result

        result[name] = visit(annual[name], name)
    return result


def safe_entity(value, kind):
    result = pick(value, ENTITY_FIELDS[kind])
    if "details_json" in result:
        details = json.loads(result["details_json"])
        result["details_json"] = document(
            pick(details, ("structured_answers", "answer_template_snapshot"))
        )
        if "answer_template_snapshot" in details:
            snap = pick(details["answer_template_snapshot"], ("title", "schema"))
            result["details_json"] = document(
                pick(details, ("structured_answers",)) | {"answer_template_snapshot": snap}
            )
    return result


def snapshot_entity(cls, row, course_id, meta, **overrides):
    if "revision" in row and (type(row["revision"]) is not int or row["revision"] < 1):
        raise ValueError("Некорректная revision библиотечного снимка")
    values = {
        f.name: row[f.name]
        for f in fields(cls)
        if f.name in row and f.name not in {"metadata", "course_id"}
    }
    for name, enum in (
        (
            "type",
            AssessmentType
            if cls is c.HomeworkDefinition
            else LessonType
            if cls is c.SeminarMaterial
            else c.LiteratureType,
        ),
        ("role", c.MaterialFileRole),
    ):
        if name in values:
            values[name] = enum(values[name])
    if cls is c.Problem:
        values["family_id"] = EntityId(values["family_id"]) if values.get("family_id") else None
    if cls is e.Topic:
        values["parent_topic_id"] = (
            EntityId(values["parent_topic_id"]) if values.get("parent_topic_id") else None
        )
    for k in list(values):
        if k.endswith("_id") and values[k] is not None and not isinstance(values[k], EntityId):
            values[k] = EntityId(values[k])
    if any(f.name == "course_id" for f in fields(cls)):
        values["course_id"] = course_id
    if "id" in row:
        meta = replace(meta, id=EntityId(row["id"]))
    return cls(metadata=meta, **(values | overrides))


def remap_tree(value, mapping):
    if isinstance(value, dict):
        return {mapping.get(k, k): remap_tree(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [remap_tree(v, mapping) for v in value]
    return mapping.get(value, value) if isinstance(value, str) else value


def structural_ids(value):
    """Collect only declared identities/references; never rewrite free text matching an ID."""
    result = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k in {
                "id",
                "key",
                "parent_topic_id",
                "family_id",
                "module_key",
                "semester_key",
                "definition_id",
                "problem_id",
                "topic_id",
                "skill_id",
                "file_asset_id",
            }:
                if v:
                    result.add(v)
            elif k.endswith("_ids") or k in {"module_keys", "work_keys"}:
                result.update(v)
            if isinstance(v, (dict, list)):
                result.update(structural_ids(v))
            # File maps use dependency IDs as keys.
            try:
                EntityId(k)
            except (ValueError, TypeError):
                pass
            else:
                result.add(k)
    elif isinstance(value, list):
        for v in value:
            result.update(structural_ids(v))
    return result


def content_allowlist(data, *, include_files):
    result = {"annual": annual_allowlist(data["annual"])}
    for field, kind in (
        ("topic_ids_snapshots", "topics"),
        ("skill_ids_snapshots", "skills"),
        ("definitions", "definitions"),
        ("seminar_material_ids_snapshots", "seminars"),
        ("literature_item_ids_snapshots", "literature"),
    ):
        result[field] = [safe_entity(v, kind) for v in data.get(field, [])]
    for field in ("topic_ids", "skill_ids", "seminar_material_ids", "literature_item_ids"):
        result[field] = list(data.get(field, []))
    for field in ("definition_topics", "definition_skills", "definition_problems"):
        result[field] = [
            pick(v, ("definition_id", "topic_id", "skill_id", "problem_id", "sort_order"))
            for v in data.get(field, [])
        ]
    result["topic_skill_links"] = [
        pick(v, ("topic_id", "skill_id")) for v in data.get("topic_skill_links", [])
    ]
    result["problem_snapshots"] = []

    def files(values):
        return (
            [pick(v, ("file_asset_id", "role", "caption", "sort_order")) for v in values]
            if include_files
            else []
        )

    for v in data.get("problem_snapshots", []):
        result["problem_snapshots"].append(
            pick(v, ("title", "statement", "correct_answer", "solution", "topic_ids", "skill_ids"))
            | {
                "source": safe_entity(v["source"], "problems"),
                "family": safe_entity(v["family"], "problems") if v.get("family") else None,
                "details_json": safe_entity(
                    {"details_json": v.get("details_json", "{}")}, "problems"
                )["details_json"],
                "files": files(v.get("files", [])),
            }
        )
    result["definition_files"] = {k: files(v) for k, v in data.get("definition_files", {}).items()}
    result["material_files"] = {
        kind: {k: files(v) for k, v in values.items()}
        for kind, values in data.get("material_files", {}).items()
    }
    result["file_asset_ids"] = list(data.get("file_asset_ids", [])) if include_files else []
    result["document_file_ids"] = list(data.get("document_file_ids", [])) if include_files else []
    return result


def validate_portable(data):
    """Reject broken reference graphs before preview or a write transaction."""
    a.validate(data["annual"], ready=True)
    catalogs = {
        field: {str(v["id"]): v for v in data[field]}
        for field in (
            "topic_ids_snapshots",
            "skill_ids_snapshots",
            "definitions",
            "seminar_material_ids_snapshots",
            "literature_item_ids_snapshots",
        )
    }
    for field, values in catalogs.items():
        if len(values) != len(data[field]):
            raise ValueError("Повтор идентичности каталога")
        for id in values:
            EntityId(id)
    topics, skills, definitions = (
        set(catalogs[k]) for k in ("topic_ids_snapshots", "skill_ids_snapshots", "definitions")
    )
    problems = {v["source"]["id"] for v in data["problem_snapshots"]}
    for field, targets in (
        ("topic_ids", topics),
        ("skill_ids", skills),
        ("seminar_material_ids", set(catalogs["seminar_material_ids_snapshots"])),
        ("literature_item_ids", set(catalogs["literature_item_ids_snapshots"])),
    ):
        if set(data.get(field, [])) - targets:
            raise ValueError("Отсутствует обязательная зависимость программы")
    for id, topic in catalogs["topic_ids_snapshots"].items():
        seen = {id}
        parent = topic.get("parent_topic_id")
        while parent:
            if parent not in topics or parent in seen:
                raise ValueError("Повреждена иерархия тем")
            seen.add(parent)
            parent = catalogs["topic_ids_snapshots"][parent].get("parent_topic_id")
    for s in data["annual"]["semesters"]:
        for m in s["modules"]:
            for lesson in m["lessons"]:
                if set(lesson["topic_ids"]) - topics:
                    raise ValueError("Отсутствует тема занятия")
            for w in m["works"]:
                if w.get("definition_id") not in definitions:
                    raise ValueError("Отсутствует шаблон работы")
    for o in data["annual"]["outcomes"]:
        if set(o.get("topic_ids", [])) - topics or set(o.get("skill_ids", [])) - skills:
            raise ValueError("Отсутствует связь результата обучения")
    for field, target, choices in (
        ("definition_topics", "topic_id", topics),
        ("definition_skills", "skill_id", skills),
        ("definition_problems", "problem_id", problems),
    ):
        for v in data[field]:
            if v["definition_id"] not in definitions or v[target] not in choices:
                raise ValueError("Повреждена зависимость шаблона работы")
    for problem in data["problem_snapshots"]:
        if set(problem["topic_ids"]) - topics or set(problem["skill_ids"]) - skills:
            raise ValueError("Повреждена классификация задачи")
    for link in data.get("topic_skill_links", []):
        if link["topic_id"] not in topics or link["skill_id"] not in skills:
            raise ValueError("Повреждена связь темы и навыка")
    if set(data["definition_files"]) - definitions:
        raise ValueError("Файлы неизвестного шаблона")
    for name, catalog in (
        ("seminars", "seminar_material_ids_snapshots"),
        ("literature", "literature_item_ids_snapshots"),
    ):
        if set(data["material_files"].get(name, {})) - set(catalogs[catalog]):
            raise ValueError("Файлы неизвестного материала")
    if set(data["material_files"]) - {"seminars", "literature"}:
        raise ValueError("Неизвестный вид материала")
    files = set(data["file_asset_ids"])
    if set(data.get("document_file_ids", [])) - files:
        raise ValueError("Отсутствует документ программы")
    if q.snapshot_file_ids(data) - files:
        raise ValueError("Отсутствуют обязательные файлы")
    validate_library_values(data)


def validate_library_values(data):
    course_id = EntityId("00000000-0000-4000-8000-000000000000")
    meta = EntityMetadata.create(UtcInstant.now())

    def check(cls, row, **overrides):
        try:
            return snapshot_entity(cls, row, course_id, meta, **overrides)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ValueError("Некорректные поля библиотечной зависимости программы") from error

    for name, cls in (
        ("topic_ids_snapshots", e.Topic),
        ("skill_ids_snapshots", e.Skill),
        ("definitions", c.HomeworkDefinition),
        ("seminar_material_ids_snapshots", c.SeminarMaterial),
        ("literature_item_ids_snapshots", c.LiteratureItem),
    ):
        for row in data[name]:
            check(cls, row)
    for problem in data["problem_snapshots"]:
        check(c.Problem, problem["source"])
        if problem.get("family"):
            check(c.Problem, problem["family"])
        for name in ("title", "statement", "correct_answer", "solution"):
            if not isinstance(problem[name], str):
                raise ValueError("Некорректный текст снимка задачи")
    for name, cls in (
        ("definition_topics", p.DefinitionTopic),
        ("definition_skills", p.DefinitionSkill),
        ("definition_problems", p.DefinitionProblem),
        ("topic_skill_links", e.TopicSkill),
    ):
        for row in data.get(name, []):
            check(cls, row)
    for owner, links in data["definition_files"].items():
        for row in links:
            check(c.HomeworkAttachment, row, homework_definition_id=EntityId(owner))
    for problem in data["problem_snapshots"]:
        for row in problem["files"]:
            check(c.ProblemAttachment, row, problem_id=EntityId(problem["source"]["id"]))
    for kind, cls, fk in (
        ("seminars", c.SeminarAttachment, "seminar_material_id"),
        ("literature", c.LiteratureAttachment, "literature_item_id"),
    ):
        for owner, links in data["material_files"].get(kind, {}).items():
            for row in links:
                check(cls, row, **{fk: EntityId(owner)})


@dataclass(frozen=True)
class ProgramPackage:
    origin: str
    content_hash: str
    payload_json: str
    files: tuple[dict, ...]
    excluded_files: int
    archive_hash: str = ""


@dataclass(frozen=True)
class ProgramImportPreview:
    package: ProgramPackage
    path: Path
    matches: tuple
    warnings: tuple[str, ...]


def edition_fingerprint(package):
    return hashlib.sha256(
        (package.payload_json + document(list(package.files))).encode()
    ).hexdigest()


class ProgramExchangeService:
    def export_program(self, version_id, destination, *, include_files=False):
        version = self.get_program_version(version_id)
        original = json.loads(version.content_json)
        if "annual" not in original:
            raise ValueError("Сначала создайте и заполните годовую редакцию старой программы")
        program = self.get_course_program(version.course_program_id)
        course = self.get_course(program.course_id, historical=True)
        data = content_allowlist(original, include_files=include_files)
        origin = original.get("exchange_origin", "urn:uuid:" + str(version.id))
        recorded_ids = original.get("exchange_local_ids", {})
        mapping = {
            id: recorded_ids.get(id, str(uuid5(NAMESPACE_URL, origin + "/" + id)))
            for id in structural_ids(data)
        }
        data = remap_tree(data, mapping)

        def canonical_references(value):
            if isinstance(value, dict):
                return {
                    name: sorted(item)
                    if name.endswith("_ids") or name in {"module_keys", "work_keys"}
                    else canonical_references(item)
                    for name, item in value.items()
                }
            if isinstance(value, list):
                return [canonical_references(item) for item in value]
            return value

        data = canonical_references(data)
        validate_portable(data)
        file_values, sources = [], {}
        for id in original.get("file_asset_ids", []) if include_files else ():
            asset = self.get_file_asset(EntityId(id), include_deleted=True)
            entry = {
                "id": mapping[id],
                "name": asset.original_filename,
                "size": asset.size_bytes,
                "sha256": asset.sha256,
            }
            file_values.append(entry)
            sources[entry["id"]] = self.accessible_file_path(asset.id)
        payload = document(
            {
                "course": pick(record(course), ("name", "short_name", "description")),
                "edition": {
                    "number": original.get("exchange_version_no", version.version_no),
                    "label": version.label,
                },
                "content": data,
            }
        )
        package = ProgramPackage(
            origin,
            hashlib.sha256(payload.encode()).hexdigest(),
            payload,
            tuple(sorted(file_values, key=lambda entry: entry["id"])),
            0 if include_files else len(original.get("file_asset_ids", [])),
        )
        return self._program_exchange.write(package, Path(destination), sources)

    def preview_program_import(self, path):
        package = self._program_exchange.read(Path(path))
        data = json.loads(package.payload_json)["content"]
        validate_portable(data)
        matches = tuple(
            v
            for v in self._r.program_imports.list()
            if v.origin == package.origin and v.content_hash == edition_fingerprint(package)
        )
        warnings = []
        by_code = {d.normalized_key: d for d in self.list_directions()}
        for spec in data["annual"]["passport"]["directions"]:
            _, code = q.direction_identity(spec["code"])
            local = by_code.get(code)
            if local and local.name != spec["name"]:
                warnings.append(
                    f"Код {spec['code']}: локально «{local.name}», в пакете «{spec['name']}». Локальное название сохранится; входящее останется в снимке."
                )
        if package.excluded_files:
            warnings.append(f"Автор исключил файлов: {package.excluded_files}")
        if matches:
            warnings.append(
                "Эта редакция уже импортирована. Откройте её или явно создайте независимую копию."
            )
        return ProgramImportPreview(package, Path(path), matches, tuple(warnings))

    def commit_program_import(self, preview, *, course_id=None, independent_copy=False):
        # Re-read source and compare hash, never trust an old preview or mutable caller data.
        verified = self.preview_program_import(preview.path)
        if verified.package != preview.package:
            raise ValueError("Файл изменился после предварительного просмотра")
        with TemporaryDirectory(prefix="studium-program-import-") as folder:
            sources = self._program_exchange.stage(verified.package, preview.path, Path(folder))
            data = json.loads(verified.package.payload_json)
            ids = structural_ids(data["content"])
            mapping = {id: str(self._meta().id) for id in ids}
            imported_data = remap_tree(data["content"], mapping)
            file_meta = [(entry, self._meta()) for entry in verified.package.files]
            # Reuse the existing durable FileAsset journal. SQL commits inside the file boundary.
            pairs = [(sources[e["id"]], m.id) for e, m in file_meta]
            for entry, meta in file_meta:
                old = mapping[entry["id"]]
                imported_data = remap_tree(imported_data, {old: str(meta.id)})
                mapping[entry["id"]] = str(meta.id)
            storage = self._file_adapters()
            with storage.import_files(pairs) if pairs else nullcontext(()) as imported:
                with self._transaction() as r:
                    duplicate = [
                        v
                        for v in r.program_imports.list()
                        if v.origin == verified.package.origin
                        and v.content_hash == edition_fingerprint(verified.package)
                    ]
                    if duplicate and not independent_copy:
                        raise ValueError(
                            "Редакция уже импортирована: откройте существующую или выберите независимую копию"
                        )
                    if course_id is None:
                        course = e.Course(metadata=self._meta(), **data["course"])
                        r.courses.insert(course)
                        course_id = course.id
                    else:
                        self._require(r.courses, course_id)
                    for (_, meta), info in zip(file_meta, imported, strict=True):
                        r.file_assets.insert(e.FileAsset(metadata=meta, **asdict(info)))
                    self._hydrate_program_content(r, course_id, imported_data)
                    program = q.CourseProgram(
                        metadata=self._meta(),
                        course_id=course_id,
                        title=imported_data["annual"]["passport"]["title"],
                    )
                    r.course_programs.insert(program)
                    imported_data["exchange_origin"] = verified.package.origin
                    imported_data["exchange_version_no"] = data["edition"]["number"]
                    imported_data["exchange_local_ids"] = {
                        local: portable for portable, local in mapping.items()
                    }
                    frozen = self._freeze_annual(r, course_id, imported_data)
                    version = self._insert_annual_version(r, program, frozen)
                    r.program_imports.insert(
                        a.ProgramImport(
                            metadata=self._meta(),
                            program_version_id=version.id,
                            origin=verified.package.origin,
                            content_hash=edition_fingerprint(verified.package),
                        )
                    )
            return version

    def _hydrate_program_content(self, r, course_id, data):
        def insert(repo, cls, row, **overrides):
            value = snapshot_entity(cls, row, course_id, self._meta(), **overrides)
            repo.insert(value)
            if any(field.name == "course_id" for field in fields(cls)):
                row["course_id"] = str(course_id)
            return value

        pending = list(data["topic_ids_snapshots"])
        inserted = set()
        while pending:
            for row in list(pending):
                if not row.get("parent_topic_id") or row["parent_topic_id"] in inserted:
                    insert(r.topics, e.Topic, row)
                    inserted.add(row["id"])
                    pending.remove(row)
        for row in data["skill_ids_snapshots"]:
            insert(r.skills, e.Skill, row)
        for link in data.get("topic_skill_links", []):
            insert(r.topic_skills, e.TopicSkill, link)
        seen = set()
        for snapshot in data["problem_snapshots"]:
            for row in (snapshot.get("family"), snapshot["source"]):
                if row and row["id"] not in seen:
                    insert(r.problems, c.Problem, row, identifier="")
                    seen.add(row["id"])
        for field, repo, cls in (
            ("definitions", r.homework_definitions, c.HomeworkDefinition),
            ("seminar_material_ids_snapshots", r.seminar_materials, c.SeminarMaterial),
            ("literature_item_ids_snapshots", r.literature_items, c.LiteratureItem),
        ):
            for row in data[field]:
                insert(repo, cls, row)
        for field, cls in (
            ("definition_topics", p.DefinitionTopic),
            ("definition_skills", p.DefinitionSkill),
            ("definition_problems", p.DefinitionProblem),
        ):
            for row in data[field]:
                insert(getattr(r, field), cls, row)
        # Semantic links for problem dependencies and immutable attachment references.
        for snapshot in data["problem_snapshots"]:
            owner = snapshot["source"].get("family_id") or snapshot["source"]["id"]
            for field, cls, target in (
                ("problem_topics", p.ProblemTopic, "topic"),
                ("problem_skills", p.ProblemSkill, "skill"),
            ):
                for id in snapshot[target + "_ids"]:
                    if not any(
                        str(v.problem_id) == owner and str(getattr(v, target + "_id")) == id
                        for v in getattr(r, field).list()
                    ):
                        insert(getattr(r, field), cls, {"problem_id": owner, target + "_id": id})
        for field, owners in (("definition_files", data["definition_files"]),):
            for owner, links in owners.items():
                for link in links:
                    insert(
                        r.homework_attachments,
                        c.HomeworkAttachment,
                        link,
                        homework_definition_id=EntityId(owner),
                    )
        for snapshot in data["problem_snapshots"]:
            for link in snapshot["files"]:
                insert(
                    r.problem_attachments,
                    c.ProblemAttachment,
                    link,
                    problem_id=EntityId(snapshot["source"]["id"]),
                )
        for kind, repo, cls, fk in (
            ("seminars", r.seminar_attachments, c.SeminarAttachment, "seminar_material_id"),
            ("literature", r.literature_attachments, c.LiteratureAttachment, "literature_item_id"),
        ):
            for owner, links in data["material_files"].get(kind, {}).items():
                for link in links:
                    insert(repo, cls, link, **{fk: EntityId(owner)})
