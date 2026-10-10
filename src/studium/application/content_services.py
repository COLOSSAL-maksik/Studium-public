"""Library CRUD, existing file pipeline and reviewable offline variant workflow."""

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.application.program_services import CONTENT_LINKS
from studium.domain import content as c
from studium.domain import program as p
from studium.domain.entities import FileAsset
from studium.domain.repositories import RepositoryError, RepositoryFailure

LIBRARIES = {
    "assigned_tasks": (
        "student_problem_assignments",
        None,
        "student_problem_files",
        p.StudentProblemFile,
        "student_problem_assignment_id",
    ),
    "packs": (
        "homework_packs",
        p.HomeworkPack,
        "homework_pack_attachments",
        p.HomeworkPackAttachment,
        "homework_pack_id",
    ),
    "methodical": (
        "methodical_materials",
        p.MethodicalMaterial,
        "methodical_attachments",
        p.MethodicalAttachment,
        "methodical_material_id",
    ),
    "programs": (
        "work_programs",
        p.WorkProgram,
        "program_attachments",
        p.ProgramAttachment,
        "work_program_id",
    ),
    "assessment_files": (
        "assessments",
        None,
        "assessment_attachments",
        p.AssessmentAttachment,
        "assessment_id",
    ),
    "homework": (
        "homework_definitions",
        c.HomeworkDefinition,
        "homework_attachments",
        c.HomeworkAttachment,
        "homework_definition_id",
    ),
    "problems": ("problems", c.Problem, "problem_attachments", c.ProblemAttachment, "problem_id"),
    "seminars": (
        "seminar_materials",
        c.SeminarMaterial,
        "seminar_attachments",
        c.SeminarAttachment,
        "seminar_material_id",
    ),
    "literature": (
        "literature_items",
        c.LiteratureItem,
        "literature_attachments",
        c.LiteratureAttachment,
        "literature_item_id",
    ),
}


@dataclass(frozen=True)
class MaterialFileEntry:
    attachment: c.MaterialAttachment
    asset: FileAsset
    material: c.TeachingContent
    integrity: FileIntegrity


@dataclass(frozen=True)
class TicketDraft:
    criteria: c.GenerationCriteria
    variants: tuple[tuple[c.Problem, ...], ...]


@dataclass(frozen=True)
class TicketView:
    ticket: c.Ticket
    problems: tuple[c.TicketProblem, ...]
    assignments: tuple[c.TicketAssignment, ...]


@dataclass(frozen=True)
class StudentTicketProblem:
    title: str
    statement: str
    file_asset_ids: tuple


@dataclass(frozen=True)
class ResolvedProblem:
    """Reviewable variant plus its current parent; no shared text is stored twice."""

    source: c.Problem
    family: c.Problem

    def __getattr__(self, name):
        return getattr(self.source, name)

    @property
    def title(self):
        return f"{self.family.title} · вариант {self.source.variant_code}"

    @property
    def statement(self):
        return self.family.statement + (
            f"\nПараметры: {self.source.parameters}" if self.source.parameters else ""
        )

    @property
    def tags(self):
        return self.family.tags

    @property
    def purposes(self):
        return self.family.purposes

    @property
    def identifier(self):
        return f"{self.family.identifier} / {self.source.variant_code}"


class ContentService:
    def _restore_content_link(self, repository, original, **values):
        metadata = replace(original.metadata.touch(self._clock()), deleted_at=None)
        updated = replace(original, metadata=metadata, **values)
        repository.update(updated, expected_revision=original.revision)
        return updated

    def list_materials(
        self,
        kind,
        *,
        course_id=None,
        search="",
        tags=(),
        collection_id=None,
        week=None,
        topic_id=None,
        skill_id=None,
        literature_type=None,
        purpose=None,
        material_type=None,
        include_archived=False,
    ):
        name = LIBRARIES[kind][0]
        wanted = {t.strip().casefold() for t in tags if t.strip()}
        with self._transaction() as r:
            values = getattr(r, name).list(include_deleted=include_archived)
            members = (
                {m.problem_id for m in r.problem_collection_members.for_owner(collection_id)}
                if collection_id
                else None
            )
            seminars = (
                {
                    m.seminar_material_id
                    for m in r.seminar_material_topics.list()
                    if m.topic_id == topic_id
                }
                if topic_id and kind == "seminars"
                else None
            )
            scope_ids = None
            prefix = {
                "problems": "problem",
                "homework": "definition",
                "methodical": "methodical",
            }.get(kind)
            if prefix:
                for suffix, id in (("topics", topic_id), ("skills", skill_id)):
                    if id:
                        _, _, _, owner, target = CONTENT_LINKS[prefix + "_" + suffix]
                        ids = {
                            getattr(link, owner)
                            for link in getattr(r, prefix + "_" + suffix).list()
                            if getattr(link, target) == id
                        }
                        scope_ids = ids if scope_ids is None else scope_ids & ids
            return tuple(
                sorted(
                    (
                        value
                        for value in values
                        if (course_id is None or value.course_id == course_id)
                        and wanted.issubset({t.casefold() for t in value.tags})
                        and (kind != "problems" or value.family_id is None)
                        and (purpose is None or purpose in value.purposes)
                        and (members is None or value.id in members)
                        and (seminars is None or value.id in seminars)
                        and (scope_ids is None or value.id in scope_ids)
                        and (week is None or getattr(value, "planned_week", None) == week)
                        and (
                            literature_type is None
                            or getattr(value, "type", None) == literature_type
                        )
                        and (material_type is None or getattr(value, "type", None) == material_type)
                        and search.casefold()
                        in " ".join(
                            str(getattr(value, f, ""))
                            for f in (
                                "title",
                                "notes",
                                "description",
                                "statement",
                                "authors",
                                "plan_text",
                                "full_text",
                                "tags_json",
                                "identifier",
                            )
                        ).casefold()
                    ),
                    key=lambda value: (value.title.casefold(), value.id),
                )
            )

    def get_material(self, kind, id, *, historical=False):
        return self._require(getattr(self._r, LIBRARIES[kind][0]), id, historical=historical)

    def create_material(self, kind, *, tags=(), topic_ids=(), problem_ids=(), **values):
        name, cls, *_ = LIBRARIES[kind]
        with self._transaction() as r:
            if values.get("course_id"):
                self._require(r.courses, values["course_id"])
            if kind == "problems":
                values["purposes_json"] = c.purpose_document(values.pop("purposes", ()))
                if values.get("family_id"):
                    family = self._require(r.problems, values["family_id"])
                    if not family.is_family or family.course_id != values["course_id"]:
                        raise ApplicationError("learning_course_mismatch")
            value = cls(metadata=self._meta(), tags_json=c.tag_document(tags), **values)
            getattr(r, name).insert(value)
            if kind == "seminars":
                self._set_seminar_topics(r, value, topic_ids)
                if problem_ids:
                    self._set_seminar_problems(r, value, problem_ids)
            return value

    def update_material(
        self, kind, original, *, tags=None, topic_ids=None, problem_ids=None, **values
    ):
        if values.get("course_id", original.course_id) != original.course_id:
            raise ApplicationError("learning_owner_immutable")
        with self._transaction() as r:
            repository = getattr(r, LIBRARIES[kind][0])
            self._require(repository, original.id)
            if tags is not None:
                values["tags_json"] = c.tag_document(tags)
            if kind == "problems" and "purposes" in values:
                values["purposes_json"] = c.purpose_document(values.pop("purposes"))
            value = self._update(repository, original, **values)
            if kind == "seminars" and topic_ids is not None:
                self._set_seminar_topics(r, value, topic_ids)
            if kind == "seminars" and problem_ids is not None:
                self._set_seminar_problems(r, value, problem_ids)
            return value

    def archive_material(self, kind, original):
        getattr(self._r, LIBRARIES[kind][0]).soft_delete(
            original.id, expected_revision=original.revision, at=self._clock()
        )

    def list_problem_variants(self, family_id):
        return tuple(
            sorted(
                (p for p in self._r.problems.list() if p.family_id == family_id),
                key=lambda p: (p.variant_code, p.id),
            )
        )

    def problem_preview_files(self, problem_id):
        problem = self.get_material("problems", problem_id, historical=True)
        owners = (problem.family_id, problem.id) if problem.family_id else (problem.id,)
        return tuple(
            entry
            for owner in owners
            for entry in self.list_material_files("problems", owner)
            if entry.attachment.role == c.MaterialFileRole.STATEMENT
        )

    def _effective_problem(self, r, problem):
        if problem.is_family:
            raise ApplicationError("problem_variant_required")
        if problem.family_id:
            return ResolvedProblem(problem, self._require(r.problems, problem.family_id))
        return problem

    def _problem_files(self, r, problem):
        owners = (problem.family_id, problem.id) if problem.family_id else (problem.id,)
        links = {}
        for owner in owners:
            for link in r.problem_attachments.for_owner(owner):
                links[link.file_asset_id] = link
        return tuple(links.values())

    def problem_pool(self, criteria):
        parents = self.list_materials(
            "problems",
            course_id=criteria.course_id,
            tags=criteria.tags,
            collection_id=criteria.collection_id,
            purpose=criteria.purpose,
        )
        eligible = {
            p.id: p for p in parents if not criteria.problem_ids or p.id in criteria.problem_ids
        }
        pool = [p for p in eligible.values() if not p.is_family]
        if any(p.is_family for p in eligible.values()):
            for variant in self._r.problems.list():
                if variant.family_id in eligible:
                    pool.append(ResolvedProblem(variant, eligible[variant.family_id]))
        return tuple(pool)

    def _set_seminar_topics(self, r, seminar, topic_ids):
        target_ids = set(topic_ids)
        existing = {
            m.topic_id: m
            for m in r.seminar_material_topics.for_owner(seminar.id, include_deleted=True)
        }
        for id in target_ids:
            topic = self._require(r.topics, id)
            if topic.course_id != seminar.course_id:
                raise ApplicationError("learning_course_mismatch")
            if id not in existing:
                r.seminar_material_topics.insert(
                    c.SeminarMaterialTopic(
                        metadata=self._meta(), seminar_material_id=seminar.id, topic_id=id
                    )
                )
            elif existing[id].deleted_at:
                self._restore_content_link(r.seminar_material_topics, existing[id])
        for id, link in existing.items():
            if id not in target_ids and link.deleted_at is None:
                r.seminar_material_topics.soft_delete(
                    link.id, expected_revision=link.revision, at=self._clock()
                )

    def seminar_topic_ids(self, seminar_id):
        return tuple(m.topic_id for m in self._r.seminar_material_topics.for_owner(seminar_id))

    def _set_seminar_problems(self, r, seminar, problem_ids):
        desired = set(problem_ids)
        existing = {
            v.problem_id: v for v in r.seminar_problems.for_owner(seminar.id, include_deleted=True)
        }
        for id in desired:
            problem = self._require(r.problems, id, historical=id in existing)
            if problem.course_id != seminar.course_id:
                raise ApplicationError("learning_course_mismatch")
            if id not in existing:
                r.seminar_problems.insert(
                    p.SeminarProblem(
                        metadata=self._meta(), seminar_material_id=seminar.id, problem_id=id
                    )
                )
            elif existing[id].deleted_at:
                self._restore_content_link(r.seminar_problems, existing[id])
        for id, link in existing.items():
            if id not in desired and link.deleted_at is None:
                r.seminar_problems.soft_delete(
                    link.id, expected_revision=link.revision, at=self._clock()
                )

    def list_problem_collections(self, course_id=None):
        return tuple(
            c
            for c in self._r.problem_collections.list()
            if course_id is None or c.course_id == course_id
        )

    def create_problem_collection(self, course_id, title, notes=""):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            value = c.ProblemCollection(
                metadata=self._meta(), course_id=course_id, title=title.strip(), notes=notes
            )
            r.problem_collections.insert(value)
            return value

    def set_problem_collection(self, collection_id, problem_id, *, included=True):
        with self._transaction() as r:
            collection = self._require(r.problem_collections, collection_id)
            problem = self._require(r.problems, problem_id)
            if problem.family_id:
                raise ApplicationError("problem_variant_inherits_classification")
            if collection.course_id != problem.course_id:
                raise ApplicationError("learning_course_mismatch")
            existing = r.problem_collection_members.find_pair(collection_id, problem_id)
            if included:
                if existing and existing.deleted_at:
                    return self._restore_content_link(r.problem_collection_members, existing)
                if existing:
                    return existing
                value = c.ProblemCollectionMember(
                    metadata=self._meta(), collection_id=collection_id, problem_id=problem_id
                )
                r.problem_collection_members.insert(value)
                return value
            if existing and existing.deleted_at is None:
                r.problem_collection_members.soft_delete(
                    existing.id, expected_revision=existing.revision, at=self._clock()
                )

    def problem_collection_ids(self, problem_id):
        return tuple(
            link.collection_id
            for link in self._r.problem_collection_members.list()
            if link.problem_id == problem_id
        )

    def import_file_for_material(
        self, kind, owner_id, source, *, role=c.MaterialFileRole.STATEMENT, caption=""
    ):
        name, _, links_name, link_cls, owner_field = LIBRARIES[kind]
        self.get_material(kind, owner_id)
        meta = self._meta()
        with self._file_adapters().import_file(Path(source), meta.id) as imported:
            asset = FileAsset(metadata=meta, **asdict(imported))
            with self._transaction() as r:
                self._require(getattr(r, name), owner_id)
                links = getattr(r, links_name)
                order = (
                    max(
                        (
                            link.sort_order
                            for link in links.for_owner(owner_id, include_deleted=True)
                        ),
                        default=-1,
                    )
                    + 1
                )
                link = link_cls(
                    metadata=self._meta(),
                    file_asset_id=asset.id,
                    sort_order=order,
                    role=role,
                    caption=caption,
                    **{owner_field: owner_id},
                )
                r.file_assets.insert(asset)
                links.insert(link)
        return link

    def list_material_files(self, kind, owner_id):
        material = self.get_material(kind, owner_id, historical=True)
        with self._transaction() as r:
            links = getattr(r, LIBRARIES[kind][2]).for_owner(owner_id)
            return tuple(
                MaterialFileEntry(
                    link,
                    self._require(r.file_assets, link.file_asset_id, historical=True),
                    material,
                    self.verify_file_integrity(link.file_asset_id),
                )
                for link in sorted(links, key=lambda link: (link.sort_order, link.id))
            )

    def detach_material_file(self, kind, original):
        getattr(self._r, LIBRARIES[kind][2]).soft_delete(
            original.id, expected_revision=original.revision, at=self._clock()
        )

    def generate_ticket_draft(self, criteria):
        if criteria.collection_id:
            collection = self._require(self._r.problem_collections, criteria.collection_id)
            if collection.course_id != criteria.course_id:
                raise ApplicationError("learning_course_mismatch")
        pool = self.problem_pool(criteria)
        try:
            return TicketDraft(criteria, c.generate_variants(pool, criteria))
        except ValueError as error:
            if str(error) == "insufficient_problem_pool":
                raise ApplicationError("insufficient_problem_pool") from None
            raise

    def replace_draft_problem(self, draft, variant_index, problem_index, problem_id):
        pool = {p.id: p for p in self.problem_pool(draft.criteria)}
        if problem_id not in pool:
            raise ApplicationError("problem_not_eligible")
        variants = [list(v) for v in draft.variants]
        variants[variant_index][problem_index] = pool[problem_id]
        keys = [tuple(sorted(p.id for p in variant)) for variant in variants]
        if any(len(set(key)) != len(key) for key in keys) or len(set(keys)) != len(keys):
            raise ApplicationError("duplicate_variant")
        return TicketDraft(draft.criteria, tuple(tuple(v) for v in variants))

    def save_ticket_set(
        self,
        offering_id,
        draft,
        *,
        title="Набор вариантов",
        assessment_id=None,
        assign_students=False,
    ):
        with self._transaction() as r:
            context = self._context(r, offering_id)
            if context.course.id != draft.criteria.course_id:
                raise ApplicationError("learning_course_mismatch")
            if (
                assessment_id
                and self._require(r.assessments, assessment_id).offering_id != offering_id
            ):
                raise ApplicationError("item_result_context_mismatch")
            roster = self._roster(r, offering_id)
            if assign_students and len(roster) != len(draft.variants):
                raise ApplicationError("variant_roster_count_mismatch")
            criteria = draft.criteria
            snapshot = {
                "course_id": str(criteria.course_id),
                "tags": criteria.tags,
                "collection_id": str(criteria.collection_id) if criteria.collection_id else None,
                "seed": criteria.seed,
                "variants": criteria.variants,
                "problems_per_variant": criteria.problems_per_variant,
                "purpose": criteria.purpose,
                "problem_ids": [str(id) for id in criteria.problem_ids],
            }
            if len(draft.variants) != criteria.variants or any(
                len(v) != criteria.problems_per_variant for v in draft.variants
            ):
                raise ApplicationError("invalid_ticket_draft")
            keys = [tuple(sorted(p.id for p in v)) for v in draft.variants]
            if len(set(keys)) != len(keys) or any(len(set(key)) != len(key) for key in keys):
                raise ApplicationError("duplicate_variant")
            eligible = {p.id for p in self.problem_pool(criteria)}
            value = c.TicketSet(
                metadata=self._meta(),
                course_offering_id=offering_id,
                title=title.strip(),
                assessment_id=assessment_id,
                criteria_json=json.dumps(snapshot, ensure_ascii=False),
            )
            r.ticket_sets.insert(value)
            skill_ids = self._snapshot_problem_skills(r)
            for i, variant in enumerate(draft.variants, 1):
                ticket = c.Ticket(metadata=self._meta(), ticket_set_id=value.id, number=i)
                r.tickets.insert(ticket)
                for position, problem in enumerate(variant, 1):
                    current = self._effective_problem(r, self._require(r.problems, problem.id))
                    if current != problem or problem.id not in eligible:
                        raise RepositoryError(
                            RepositoryFailure.REVISION_CONFLICT, "Problem changed after review"
                        )
                    fact = c.TicketProblem(
                        metadata=self._meta(),
                        ticket_id=ticket.id,
                        problem_id=problem.id,
                        position=position,
                        source_revision=problem.revision,
                        title_snapshot=problem.title,
                        statement_snapshot=problem.statement,
                        teacher_snapshot_json=json.dumps(
                            {
                                "correct_answer": problem.correct_answer,
                                "solution": problem.solution,
                                "notes": problem.notes,
                                "skill_ids": skill_ids.get(problem.family_id or problem.id, []),
                                "family_id": str(problem.family_id) if problem.family_id else None,
                                "family_revision": problem.family.revision
                                if isinstance(problem, ResolvedProblem)
                                else None,
                            },
                            ensure_ascii=False,
                        ),
                    )
                    r.ticket_problems.insert(fact)
                    for link in self._problem_files(r, problem):
                        self._require(r.file_assets, link.file_asset_id)
                        r.ticket_problem_files.insert(
                            c.TicketProblemFile(
                                metadata=self._meta(),
                                ticket_problem_id=fact.id,
                                file_asset_id=link.file_asset_id,
                                role=link.role,
                                sort_order=link.sort_order,
                            )
                        )
                if assign_students:
                    r.ticket_assignments.insert(
                        c.TicketAssignment(
                            metadata=self._meta(),
                            ticket_set_id=value.id,
                            ticket_id=ticket.id,
                            enrollment_id=roster[i - 1].enrollment.id,
                        )
                    )
            return value

    def list_ticket_sets(self, offering_id):
        return tuple(s for s in self._r.ticket_sets.list() if s.course_offering_id == offering_id)

    def ticket_set_details(self, ticket_set_id):
        with self._transaction() as r:
            self._require(r.ticket_sets, ticket_set_id, historical=True)
            tickets = sorted(r.tickets.for_owner(ticket_set_id), key=lambda t: t.number)
            problems = r.ticket_problems.list()
            assignments = r.ticket_assignments.for_owner(ticket_set_id)
            return tuple(
                TicketView(
                    t,
                    tuple(
                        sorted(
                            (p for p in problems if p.ticket_id == t.id), key=lambda p: p.position
                        )
                    ),
                    tuple(a for a in assignments if a.ticket_id == t.id),
                )
                for t in tickets
            )

    def assign_ticket(self, ticket_set_id, enrollment_id, ticket_id, *, original=None):
        with self._transaction() as r:
            ticket_set = self._require(r.ticket_sets, ticket_set_id)
            enrollment = self._require(r.enrollments, enrollment_id)
            active = {
                entry.enrollment.id for entry in self._roster(r, ticket_set.course_offering_id)
            }
            if enrollment.id not in active:
                raise ApplicationError("attendance_context_mismatch")
            ticket = self._require(r.tickets, ticket_id)
            if ticket.ticket_set_id != ticket_set_id:
                raise ApplicationError("attendance_context_mismatch")
            existing = r.ticket_assignments.find_pair(ticket_set_id, enrollment_id)
            if existing:
                if original is None and existing.deleted_at is not None:
                    original = existing
                if original is None or original != existing:
                    raise RepositoryError(RepositoryFailure.REVISION_CONFLICT, "Assignment changed")
                return self._restore_content_link(
                    r.ticket_assignments, original, ticket_id=ticket_id
                )
            value = c.TicketAssignment(
                metadata=self._meta(),
                ticket_set_id=ticket_set_id,
                ticket_id=ticket_id,
                enrollment_id=enrollment_id,
            )
            r.ticket_assignments.insert(value)
            return value

    def unassign_ticket(self, original):
        self._r.ticket_assignments.soft_delete(
            original.id, expected_revision=original.revision, at=self._clock()
        )

    def list_ticket_files(self, ticket_id):
        with self._transaction() as r:
            facts = {p.id: p for p in r.ticket_problems.for_owner(ticket_id)}
            return tuple(
                MaterialFileEntry(
                    link,
                    self._require(r.file_assets, link.file_asset_id, historical=True),
                    facts[link.ticket_problem_id],
                    self.verify_file_integrity(link.file_asset_id),
                )
                for link in r.ticket_problem_files.list()
                if link.ticket_problem_id in facts
            )

    def student_ticket_content(self, ticket_id):
        """Whitelisted student output cannot contain answer, solution or reference files."""
        with self._transaction() as r:
            ticket = self._require(r.tickets, ticket_id, historical=True)
            facts = sorted(r.ticket_problems.for_owner(ticket.id), key=lambda p: p.position)
            files = r.ticket_problem_files.list()
            return tuple(
                StudentTicketProblem(
                    p.title_snapshot,
                    p.statement_snapshot,
                    tuple(
                        f.file_asset_id
                        for f in sorted(files, key=lambda f: f.sort_order)
                        if f.ticket_problem_id == p.id and f.role == c.MaterialFileRole.STATEMENT
                    ),
                )
                for p in facts
            )
