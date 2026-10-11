"""Local curriculum, manual knowledge reuse and factual task/skill evaluation."""

import json
from collections import defaultdict
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime, timedelta, timezone

from studium.application.errors import ApplicationError
from studium.domain import entities as e
from studium.domain import program as p
from studium.domain.enums import AssessmentType
from studium.domain.value_objects import EntityId, LocalDate, UtcInstant


@dataclass(frozen=True)
class PlannedWork:
    link: p.ProgramWork
    definition: e.StudiumEntity
    assessment: e.Assessment | None


@dataclass(frozen=True)
class KnowledgeOccurrences:
    count: int
    first: UtcInstant | None
    last: UtcInstant | None
    cases: tuple


CONTENT_LINKS = {
    "seminar_problems": (
        "seminar_materials",
        "problems",
        p.SeminarProblem,
        "seminar_material_id",
        "problem_id",
    ),
    "module_topics": ("program_modules", "topics", p.ProgramModuleTopic, "module_id", "topic_id"),
    "program_topics": ("work_programs", "topics", p.ProgramTopic, "work_program_id", "topic_id"),
    "program_skills": ("work_programs", "skills", p.ProgramSkill, "work_program_id", "skill_id"),
    "program_materials": (
        "work_programs",
        "seminar_materials",
        p.ProgramMaterial,
        "work_program_id",
        "seminar_material_id",
    ),
    "program_literature": (
        "work_programs",
        "literature_items",
        p.ProgramLiterature,
        "work_program_id",
        "literature_item_id",
    ),
    "problem_topics": ("problems", "topics", p.ProblemTopic, "problem_id", "topic_id"),
    "problem_skills": ("problems", "skills", p.ProblemSkill, "problem_id", "skill_id"),
    "definition_topics": (
        "homework_definitions",
        "topics",
        p.DefinitionTopic,
        "definition_id",
        "topic_id",
    ),
    "definition_skills": (
        "homework_definitions",
        "skills",
        p.DefinitionSkill,
        "definition_id",
        "skill_id",
    ),
    "definition_problems": (
        "homework_definitions",
        "problems",
        p.DefinitionProblem,
        "definition_id",
        "problem_id",
    ),
    "homework_pack_works": (
        "homework_packs",
        "homework_definitions",
        p.HomeworkPackWork,
        "homework_pack_id",
        "definition_id",
    ),
    "methodical_topics": (
        "methodical_materials",
        "topics",
        p.MethodicalTopic,
        "methodical_material_id",
        "topic_id",
    ),
    "methodical_skills": (
        "methodical_materials",
        "skills",
        p.MethodicalSkill,
        "methodical_material_id",
        "skill_id",
    ),
    "knowledge_topics": (
        "knowledge_entries",
        "topics",
        p.KnowledgeTopic,
        "knowledge_entry_id",
        "topic_id",
    ),
    "knowledge_skills": (
        "knowledge_entries",
        "skills",
        p.KnowledgeSkill,
        "knowledge_entry_id",
        "skill_id",
    ),
    "knowledge_materials": (
        "knowledge_entries",
        "methodical_materials",
        p.KnowledgeMaterial,
        "knowledge_entry_id",
        "methodical_material_id",
    ),
}


class ProgramService:
    def move_presentation_item(self, kind, original, direction):
        """Reorder a sibling list atomically using existing revisioned order fields."""
        owner = {
            "topics": "course_id",
            "skills": "course_id",
            "program_modules": "work_program_id",
            "program_works": "work_program_id",
        }[kind]
        if direction not in (-1, 1):
            raise ValueError("Expected adjacent move")
        with self._transaction() as r:
            repository = getattr(r, kind)
            rows = [
                v
                for v in repository.list()
                if getattr(v, owner) == getattr(original, owner)
                and (kind != "topics" or v.parent_topic_id == original.parent_topic_id)
            ]
            rows.sort(
                key=lambda v: (
                    v.sort_order,
                    getattr(v, "start_week", 0),
                    getattr(v, "title", ""),
                    v.id,
                )
            )
            index = next(i for i, row in enumerate(rows) if row.id == original.id)
            if not 0 <= index + direction < len(rows):
                return
            rows[index] = original  # compare-and-swap rejects stale selection.
            rows[index], rows[index + direction] = rows[index + direction], rows[index]
            for order, row in enumerate(rows):
                self._update(repository, row, sort_order=order)

    def sidebar_state(self):
        return getattr(self._preferences, "sidebar_state", lambda: ())()

    def save_sidebar_state(self, state):
        setter = getattr(self._preferences, "save_sidebar_state", None)
        if setter:
            setter(state)

    def recent_course_ids(self):
        return getattr(self._preferences, "recent_courses", lambda: ())()

    def remember_course(self, id):
        setter = getattr(self._preferences, "select_course", None)
        if setter:
            setter(id)

    def preferred_theme(self):
        return getattr(self._preferences, "theme", lambda: "light")()

    def select_theme(self, theme):
        setter = getattr(self._preferences, "select_theme", None)
        if setter:
            setter(theme)

    def recent_offering_id(self):
        return getattr(self._preferences, "recent_offering", lambda: None)()

    def recent_offering_ids(self):
        return getattr(self._preferences, "recent_offerings", lambda: ())()

    def remember_offering(self, id):
        setter = getattr(self._preferences, "select_offering", None)
        if setter:
            setter(id)

    def list_work_programs(self, course_id=None, *, include_archived=False):
        return tuple(
            sorted(
                (
                    v
                    for v in self._r.work_programs.list(include_deleted=include_archived)
                    if course_id is None or v.course_id == course_id
                ),
                key=lambda v: (v.title.casefold(), v.id),
            )
        )

    def get_work_program(self, id, *, historical=False):
        return self._require(self._r.work_programs, id, historical=historical)

    def create_work_program(self, course_id, term_id, title, first_week_start, **values):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            self._require(r.terms, term_id)
            value = p.WorkProgram(
                metadata=self._meta(),
                course_id=course_id,
                term_id=term_id,
                title=title.strip(),
                first_week_start=first_week_start,
                **values,
            )
            r.work_programs.insert(value)
            return value

    def update_work_program(self, original, **values):
        if (
            values.get("course_id", original.course_id) != original.course_id
            or values.get("term_id", original.term_id) != original.term_id
        ):
            raise ApplicationError("learning_owner_immutable")
        return self._update(self._r.work_programs, original, **values)

    def _default_program(self, r, term, course, group):
        program = p.WorkProgram(
            metadata=self._meta(),
            course_id=course.id,
            term_id=term.id,
            title=f"{course.name} · {group.number} · {term.name}",
            first_week_start=term.starts_on,
            semester=p.SemesterType.SPRING if term.starts_on.month <= 6 else p.SemesterType.AUTUMN,
            week_utc_offset_minutes=term.week_utc_offset_minutes,
            version=str(term.starts_on.year),
        )
        r.work_programs.insert(program)
        return program

    def program_for_offering(self, offering_id):
        offering = self._require(self._r.offerings, offering_id, historical=True)
        return (
            self.get_work_program(offering.work_program_id, historical=True)
            if offering.work_program_id
            else None
        )

    def current_program_week(self, offering_id):
        program = self.program_for_offering(offering_id)
        if program is None:
            return None
        today = (
            self._clock()
            .value.astimezone(timezone(timedelta(minutes=program.week_utc_offset_minutes)))
            .date()
        )
        return program.week_for_date(LocalDate.parse(today.isoformat()))

    def set_offering_program(self, offering, program_id):
        with self._transaction() as r:
            program = self._require(r.work_programs, program_id)
            if program.course_id != offering.course_id or program.term_id != offering.term_id:
                raise ApplicationError("learning_course_mismatch")
            if r.assessments.for_offering(offering.id) or r.lessons.for_offering(offering.id):
                raise ApplicationError("program_context_has_facts")
            return self._update(r.offerings, offering, work_program_id=program_id)

    def list_program_modules(self, program_id):
        return tuple(
            sorted(
                self._r.program_modules.for_owner(program_id),
                key=lambda m: (m.sort_order, m.start_week, m.id),
            )
        )

    def create_program_module(self, program_id, title, start_week, end_week, sort_order=0):
        with self._transaction() as r:
            program = self._require(r.work_programs, program_id)
            program.week_dates(end_week)
            value = p.ProgramModule(
                metadata=self._meta(),
                work_program_id=program_id,
                title=title,
                start_week=start_week,
                end_week=end_week,
                sort_order=sort_order,
            )
            r.program_modules.insert(value)
            return value

    def update_program_module(self, original, **values):
        return self._update(self._r.program_modules, original, **values)

    def create_work_definition(self, course_id, title, type=AssessmentType.HOMEWORK, **values):
        return self.create_material(
            "homework", course_id=course_id, title=title, type=type, **values
        )

    def list_work_definitions(self, course_id=None, type=None):
        return tuple(
            v
            for v in self.list_materials("homework", course_id=course_id)
            if type is None or v.type == type
        )

    def add_program_work(self, program_id, definition_id, **values):
        with self._transaction() as r:
            program = self._require(r.work_programs, program_id)
            definition = self._require(r.homework_definitions, definition_id)
            if definition.course_id != program.course_id:
                raise ApplicationError("learning_course_mismatch")
            candidate = p.ProgramWork(
                metadata=self._meta(),
                work_program_id=program_id,
                definition_id=definition_id,
                **values,
            )
            program.validate_week_date(candidate.planned_issue_week, candidate.issue_date)
            program.validate_week_date(candidate.planned_due_week, candidate.due_date)
            existing = r.program_works.find_pair(program_id, definition_id)
            if existing:
                if existing.deleted_at:
                    return self._restore_content_link(r.program_works, existing, **values)
                return self._update(r.program_works, existing, **values)
            r.program_works.insert(candidate)
            return candidate

    def update_program_work(self, original, **values):
        program = self.get_work_program(original.work_program_id)
        candidate = replace(original, **values)
        program.validate_week_date(candidate.planned_issue_week, candidate.issue_date)
        program.validate_week_date(candidate.planned_due_week, candidate.due_date)
        return self._update(self._r.program_works, original, **values)

    def planned_works(self, offering_id):
        with self._transaction() as r:
            offering = self._require(r.offerings, offering_id)
            if not offering.work_program_id:
                return ()
            definitions = {d.id: d for d in r.homework_definitions.list(include_deleted=True)}
            actual = {
                a.program_work_id: a
                for a in r.assessments.for_offering(offering_id)
                if a.program_work_id
            }
            return tuple(
                PlannedWork(w, definitions[w.definition_id], actual.get(w.id))
                for w in sorted(
                    r.program_works.for_owner(offering.work_program_id),
                    key=lambda w: (
                        w.sort_order,
                        w.planned_due_week.value if w.planned_due_week else 105,
                        w.id,
                    ),
                )
                if w.definition_id in definitions
            )

    def program_work_definitions(self, program_id):
        with self._transaction() as r:
            definitions = {v.id: v for v in r.homework_definitions.list(include_deleted=True)}
            return tuple(
                (link, definitions[link.definition_id])
                for link in sorted(
                    r.program_works.for_owner(program_id),
                    key=lambda w: (
                        w.sort_order,
                        w.planned_due_week.value if w.planned_due_week else 105,
                        w.id,
                    ),
                )
                if link.definition_id in definitions
            )

    @staticmethod
    def _program_instant(program, day, *, end=False):
        if day is None:
            return None
        local = datetime(
            day.year,
            day.month,
            day.day,
            tzinfo=timezone(timedelta(minutes=program.week_utc_offset_minutes)),
        )
        if end:
            local += timedelta(days=1, microseconds=-1)
        return UtcInstant(local.astimezone(UTC))

    def issue_program_work(self, offering_id, program_work_id):
        """Idempotent planned-cell action. Creates structure; never fictional attempts."""
        with self._transaction() as r:
            offering = self._require(r.offerings, offering_id)
            link = self._require(r.program_works, program_work_id)
            if link.work_program_id != offering.work_program_id:
                raise ApplicationError("learning_course_mismatch")
            existing = next(
                (
                    a
                    for a in r.assessments.for_offering(offering_id)
                    if a.program_work_id == link.id
                ),
                None,
            )
            if existing:
                return existing
            definition = self._require(r.homework_definitions, link.definition_id)
            program = self._require(r.work_programs, offering.work_program_id)
            assessment = e.Assessment(
                metadata=self._meta(),
                offering_id=offering_id,
                type=definition.type,
                title=definition.title,
                number=definition.label or None,
                description=definition.description,
                issued_at=self._program_instant(program, link.issue_date) or self._clock(),
                due_at=self._program_instant(program, link.due_date, end=True),
                planned_issue_week=link.planned_issue_week,
                planned_due_week=link.planned_due_week,
                homework_definition_id=definition.id,
                program_work_id=link.id,
            )
            r.assessments.insert(assessment)
            for links_name, targets_name, cls, target in (
                ("definition_topics", "assessment_topics", e.AssessmentTopic, "topic_id"),
                ("definition_skills", "assessment_skills", e.AssessmentSkill, "skill_id"),
            ):
                for source in getattr(r, links_name).for_owner(definition.id):
                    getattr(r, targets_name).insert(
                        cls(
                            metadata=self._meta(),
                            assessment_id=assessment.id,
                            **{target: getattr(source, target)},
                        )
                    )
            for source in sorted(
                r.definition_problems.for_owner(definition.id), key=lambda x: (x.sort_order, x.id)
            ):
                self._add_assessment_problem(r, assessment, source.problem_id, source.sort_order)
            return assessment

    def content_targets(self, kind, owner_id):
        _, targets, _, _, target = CONTENT_LINKS[kind]
        repository = getattr(self._r, targets)
        return tuple(
            self._require(repository, getattr(link, target), historical=True)
            for link in getattr(self._r, kind).for_owner(owner_id)
        )

    def place_topic_in_module(self, topic_id, module_id, course_id):
        return self.set_topic_modules(topic_id, (module_id,) if module_id else (), course_id)

    def set_topic_modules(self, topic_id, module_ids, course_id):
        with self._transaction() as r:
            topic = self._require(r.topics, topic_id)
            if topic.course_id != course_id:
                raise ApplicationError("learning_course_mismatch")
            programs = {p.id for p in r.work_programs.list() if p.course_id == course_id}
            modules = {m.id for m in r.program_modules.list() if m.work_program_id in programs}
            module_ids = set(module_ids)
            if not module_ids.issubset(modules):
                raise ApplicationError("learning_course_mismatch")
            links = [
                link
                for link in r.module_topics.list(include_deleted=True)
                if link.topic_id == topic_id and link.module_id in modules
            ]
            for module_id in module_ids:
                desired = next((link for link in links if link.module_id == module_id), None)
                if desired is None:
                    r.module_topics.insert(
                        p.ProgramModuleTopic(
                            metadata=self._meta(), module_id=module_id, topic_id=topic_id
                        )
                    )
                elif desired.deleted_at:
                    self._restore_content_link(r.module_topics, desired)
            for link in links:
                if link.module_id not in module_ids and link.deleted_at is None:
                    r.module_topics.soft_delete(
                        link.id, expected_revision=link.revision, at=self._clock()
                    )

    def set_content_links(self, kind, owner_id, ids, **values):
        owners, targets, cls, owner, target = CONTENT_LINKS[kind]
        with self._transaction() as r:
            owner_value = self._require(getattr(r, owners), owner_id)
            owner_course = (
                self._require(r.work_programs, owner_value.work_program_id).course_id
                if kind == "module_topics"
                else owner_value.course_id
            )
            if kind in {"problem_topics", "problem_skills"} and owner_value.family_id:
                raise ApplicationError("problem_variant_inherits_classification")
            repository = getattr(r, kind)
            desired = set(ids)
            existing = {
                getattr(v, target): v for v in repository.for_owner(owner_id, include_deleted=True)
            }
            for id in desired:
                target_value = self._require(getattr(r, targets), id)
                if target_value.course_id is not None and target_value.course_id != owner_course:
                    raise ApplicationError("learning_course_mismatch")
                if id in existing:
                    if existing[id].deleted_at:
                        self._restore_content_link(repository, existing[id], **values)
                else:
                    repository.insert(
                        cls(metadata=self._meta(), **{owner: owner_id, target: id}, **values)
                    )
            for id, link in existing.items():
                if id not in desired and link.deleted_at is None:
                    repository.soft_delete(
                        link.id, expected_revision=link.revision, at=self._clock()
                    )

    def homework_files(self, definition_id):
        """Shared pack assets resolve through links, never copy bytes per homework."""
        entries = list(self.list_material_files("homework", definition_id))
        for link in self._r.homework_pack_works.list():
            if link.definition_id == definition_id:
                entries.extend(self.list_material_files("packs", link.homework_pack_id))
        return tuple({entry.asset.id: entry for entry in entries}.values())

    def definition_for_assessment(self, assessment):
        data = self._assessment_content(self._r, assessment.id)
        if data and assessment.homework_definition_id:
            source = next(
                (
                    d
                    for d in data.get("definitions", [])
                    if d["id"] == str(assessment.homework_definition_id)
                ),
                None,
            )
            if source:
                current = self._require(
                    self._r.homework_definitions, assessment.homework_definition_id, historical=True
                )
                content_fields = {f.name for f in fields(current) if f.name != "metadata"}
                values = {name: value for name, value in source.items() if name in content_fields}
                values["course_id"] = EntityId(values["course_id"])
                values["type"] = AssessmentType(values["type"])
                return replace(current, **values)
        if assessment.homework_definition_id:
            return self.get_material("homework", assessment.homework_definition_id, historical=True)
        if assessment.program_work_id:
            link = self._require(self._r.program_works, assessment.program_work_id, historical=True)
            return self.get_material("homework", link.definition_id, historical=True)
        return None

    def assessment_shared_files(self, assessment):
        data = self._assessment_content(self._r, assessment.id)
        if data is not None and "definition_files" in data:
            return self.list_material_files("assessment_files", assessment.id)
        # Pre-v11 shared files had no historical snapshot. Preserve their tagged
        # compatibility view; do not reinterpret an empty snapshot as lost files.
        definition = self.definition_for_assessment(assessment)
        return self.homework_files(definition.id) if definition else ()

    def pack_ids_for_definition(self, definition_id):
        return tuple(
            link.homework_pack_id
            for link in self._r.homework_pack_works.list()
            if link.definition_id == definition_id
        )

    def set_definition_packs(self, definition_id, pack_ids):
        definition = self.get_material("homework", definition_id)
        selected = set(pack_ids)
        for pack in self.list_materials("packs", course_id=definition.course_id):
            ids = {v.id for v in self.content_targets("homework_pack_works", pack.id)}
            ids.add(definition_id) if pack.id in selected else ids.discard(definition_id)
            self.set_content_links("homework_pack_works", pack.id, ids)

    def create_knowledge_from_case(self, case_id, title, answer="", **values):
        with self._transaction() as r:
            case = self._require(r.question_cases, case_id)
            if not case.course_offering_id:
                raise ApplicationError("knowledge_requires_discipline")
            offering = self._require(r.offerings, case.course_offering_id, historical=True)
            entry = p.KnowledgeEntry(
                metadata=self._meta(),
                course_id=offering.course_id,
                title=title.strip(),
                answer=answer,
                draft=True,
                **values,
            )
            r.knowledge_entries.insert(entry)
            r.knowledge_sources.insert(
                p.KnowledgeSource(
                    metadata=self._meta(), knowledge_entry_id=entry.id, question_case_id=case_id
                )
            )
            return entry

    def link_knowledge_case(self, entry_id, case_id):
        with self._transaction() as r:
            entry = self._require(r.knowledge_entries, entry_id)
            case = self._require(r.question_cases, case_id, historical=True)
            offering = (
                self._require(r.offerings, case.course_offering_id, historical=True)
                if case.course_offering_id
                else None
            )
            if not offering or offering.course_id != entry.course_id:
                raise ApplicationError("learning_course_mismatch")
            existing = r.knowledge_sources.find_pair(entry_id, case_id)
            if existing:
                return (
                    self._restore_content_link(r.knowledge_sources, existing)
                    if existing.deleted_at
                    else existing
                )
            link = p.KnowledgeSource(
                metadata=self._meta(), knowledge_entry_id=entry_id, question_case_id=case_id
            )
            r.knowledge_sources.insert(link)
            return link

    def list_knowledge_entries(self, course_id=None, search=""):
        return tuple(
            v
            for v in self._r.knowledge_entries.list()
            if (course_id is None or v.course_id == course_id)
            and search.casefold() in (v.title + " " + v.answer).casefold()
        )

    def update_knowledge_entry(self, original, **values):
        return self._update(self._r.knowledge_entries, original, **values)

    def knowledge_occurrences(self, entry_id):
        links = self._r.knowledge_sources.for_owner(entry_id)
        cases = tuple(
            self._require(self._r.question_cases, v.question_case_id, historical=True)
            for v in links
        )
        dates = [v.opened_at for v in cases]
        return KnowledgeOccurrences(
            len(cases), min(dates) if dates else None, max(dates) if dates else None, cases
        )

    def _add_assessment_problem(self, r, assessment, problem_id, order=0, *, snapshot=None):
        problem = (
            None if snapshot else self._effective_problem(r, self._require(r.problems, problem_id))
        )
        offering = self._require(r.offerings, assessment.offering_id)
        if (
            EntityId(snapshot["source"]["course_id"]) if snapshot else problem.course_id
        ) != offering.course_id:
            raise ApplicationError("learning_course_mismatch")
        if r.content_locks.assessment_locked(assessment.id):
            raise ApplicationError("assessment_content_locked")
        item = e.AssessmentItem(
            metadata=self._meta(),
            assessment_id=assessment.id,
            title=snapshot["title"] if snapshot else problem.title,
            description=snapshot["statement"] if snapshot else problem.statement,
            sort_order=order,
        )
        r.items.insert(item)
        r.assessment_problems.insert(
            p.AssessmentProblem(
                metadata=self._meta(),
                assessment_item_id=item.id,
                problem_id=problem_id,
                source_revision=snapshot["source"]["revision"] if snapshot else problem.revision,
                statement_snapshot=snapshot["statement"] if snapshot else problem.statement,
            )
        )
        for name, dest, cls, target in (
            ("problem_topics", "item_topics", e.AssessmentItemTopic, "topic_id"),
            ("problem_skills", "item_skills", e.AssessmentItemSkill, "skill_id"),
        ):
            targets = (
                [EntityId(id) for id in snapshot.get(target.replace("_id", "_ids"), [])]
                if snapshot
                else [
                    getattr(v, target)
                    for v in getattr(r, name).for_owner(problem.family_id or problem.id)
                ]
            )
            for target_id in targets:
                getattr(r, dest).insert(
                    cls(
                        metadata=self._meta(),
                        assessment_item_id=item.id,
                        **{target: target_id},
                    )
                )
        return item

    def add_control_problem(self, assessment_id, problem_id, sort_order=0):
        with self._transaction() as r:
            assessment = self._require(r.assessments, assessment_id)
            if assessment.type != AssessmentType.CONTROL_WORK:
                raise ApplicationError("control_work_required")
            return self._add_assessment_problem(r, assessment, problem_id, sort_order)

    def assign_student_problem(self, student_id, assessment_item_id, problem_id):
        item = self._require(self._r.items, assessment_item_id)
        with self._transaction() as r:
            assessment = self._require(r.assessments, item.assessment_id)
            offering = self._require(r.offerings, assessment.offering_id)
            work = r.works.find_for_student(student_id, item.assessment_id, include_deleted=True)
            create_work = work is None
            if create_work:
                self._context(r, assessment.offering_id)
                student = self._require(r.students, student_id)
                if not student.active:
                    raise ApplicationError("inactive_student")
                work = e.StudentWork(
                    metadata=self._meta(), student_id=student_id, assessment_id=item.assessment_id
                )
            elif work.deleted_at is not None:
                raise ApplicationError("hidden_work")
            frozen = self._frozen_assessment_problem(r, assessment.id, problem_id)
            problem = (
                None
                if frozen
                else self._effective_problem(r, self._require(r.problems, problem_id))
            )
            if (
                EntityId(frozen["source"]["course_id"]) if frozen else problem.course_id
            ) != offering.course_id:
                raise ApplicationError("learning_course_mismatch")
            previous = r.student_problem_assignments.find_pair(work.id, item.id)
            if previous:
                if previous.problem_id == problem_id:
                    return previous
                raise ApplicationError("problem_assignment_has_snapshot")
            if r.attempts.for_works((work.id,)):
                raise ApplicationError("problem_assignment_has_snapshot")
            value = p.StudentProblemAssignment(
                metadata=self._meta(),
                student_work_id=work.id,
                assessment_item_id=item.id,
                problem_id=problem_id,
                source_revision=frozen["source"]["revision"] if frozen else problem.revision,
                title_snapshot=frozen["title"] if frozen else problem.title,
                statement_snapshot=frozen["statement"] if frozen else problem.statement,
                teacher_snapshot_json=json.dumps(
                    dict(
                        answer=frozen["correct_answer"] if frozen else problem.correct_answer,
                        solution=frozen["solution"] if frozen else problem.solution,
                        answer_schema=json.loads(
                            frozen["details_json"] if frozen else problem.details_json
                        ),
                        source_snapshot=frozen["source"] if frozen else None,
                        family_snapshot=frozen["family"] if frozen else None,
                        topic_ids=frozen["topic_ids"]
                        if frozen
                        else [
                            str(link.topic_id)
                            for link in r.problem_topics.for_owner(problem.family_id or problem.id)
                        ],
                        skill_ids=frozen["skill_ids"]
                        if frozen
                        else [
                            str(link.skill_id)
                            for link in r.problem_skills.for_owner(problem.family_id or problem.id)
                        ],
                    ),
                    ensure_ascii=False,
                ),
            )
            self._assert_saved_taxonomy_live(r, json.loads(value.teacher_snapshot_json))
            if create_work:
                r.works.insert(work)
            r.student_problem_assignments.insert(value)
            self._copy_assignment_files(
                r, value, frozen["files"] if frozen else self._problem_files(r, problem)
            )
            return value

    def _copy_assignment_files(self, repositories, assignment, sources):
        from studium.domain.content import MaterialFileRole

        for source in sources:
            repositories.student_problem_files.insert(
                p.StudentProblemFile(
                    metadata=self._meta(),
                    student_problem_assignment_id=assignment.id,
                    file_asset_id=EntityId(source["file_asset_id"])
                    if isinstance(source, dict)
                    else source.file_asset_id,
                    role=MaterialFileRole(source["role"])
                    if isinstance(source, dict)
                    else source.role,
                    sort_order=source["sort_order"]
                    if isinstance(source, dict)
                    else source.sort_order,
                    caption=source.get("caption", "")
                    if isinstance(source, dict)
                    else getattr(source, "caption", ""),
                )
            )

    def assigned_task_files(self, assignment_id):
        return self.list_material_files("assigned_tasks", assignment_id)

    def list_student_problem_assignments(self, work_id):
        return tuple(self._r.student_problem_assignments.for_owner(work_id))

    def assignment_skills(self, assignment):
        from studium.domain.value_objects import EntityId

        ids = json.loads(assignment.teacher_snapshot_json).get("skill_ids", [])
        return tuple(self._require(self._r.skills, EntityId(id), historical=True) for id in ids)

    def _snapshot_problem_skills(self, repositories):
        result = defaultdict(list)
        for link in repositories.problem_skills.list():
            result[link.problem_id].append(str(link.skill_id))
        return result

    def apply_ticket_set_for_evaluation(self, ticket_set_id):
        """Attach saved ticket snapshots to RK slots without changing issued facts."""
        with self._transaction() as r:
            ticket_set = self._require(r.ticket_sets, ticket_set_id)
            if not ticket_set.assessment_id:
                raise ApplicationError("ticket_control_required")
            assessment = self._require(r.assessments, ticket_set.assessment_id)
            if assessment.type != AssessmentType.CONTROL_WORK:
                raise ApplicationError("control_work_required")
            tickets = {t.id: t for t in r.tickets.for_owner(ticket_set_id)}
            tasks = defaultdict(list)
            for task in r.ticket_problems.list():
                if task.ticket_id in tickets:
                    tasks[task.ticket_id].append(task)
            length = max((len(v) for v in tasks.values()), default=0)
            items = sorted(
                r.items.for_assessment(assessment.id), key=lambda i: (i.sort_order, str(i.id))
            )
            if not items:
                self._assert_assessment_unlocked(r, assessment.id)
                for position in range(length):
                    item = e.AssessmentItem(
                        metadata=self._meta(),
                        assessment_id=assessment.id,
                        title=f"Задача {position + 1}",
                        sort_order=position,
                    )
                    r.items.insert(item)
                    items.append(item)
            if len(items) != length:
                raise ApplicationError("ticket_task_count_mismatch")
            result = []
            for link in r.ticket_assignments.for_owner(ticket_set_id):
                enrollment = self._require(r.enrollments, link.enrollment_id, historical=True)
                work = r.works.find_for_student(enrollment.student_id, assessment.id)
                if work is None:
                    work = e.StudentWork(
                        metadata=self._meta(),
                        student_id=enrollment.student_id,
                        assessment_id=assessment.id,
                    )
                    r.works.insert(work)
                for item, task in zip(
                    items, sorted(tasks[link.ticket_id], key=lambda t: t.position), strict=True
                ):
                    existing = r.student_problem_assignments.find_pair(work.id, item.id)
                    if existing:
                        if (
                            existing.problem_id != task.problem_id
                            or existing.statement_snapshot != task.statement_snapshot
                        ):
                            raise ApplicationError("problem_assignment_has_snapshot")
                        result.append(existing)
                        continue
                    assignment = p.StudentProblemAssignment(
                        metadata=self._meta(),
                        student_work_id=work.id,
                        assessment_item_id=item.id,
                        problem_id=task.problem_id,
                        source_revision=task.source_revision,
                        title_snapshot=task.title_snapshot,
                        statement_snapshot=task.statement_snapshot,
                        teacher_snapshot_json=task.teacher_snapshot_json,
                    )
                    r.student_problem_assignments.insert(assignment)
                    self._copy_assignment_files(
                        r, assignment, r.ticket_problem_files.for_owner(task.id)
                    )
                    result.append(assignment)
            return tuple(result)

    def record_item_skill_result(self, item_result_id, skill_id, outcome, comment=""):
        with self._transaction() as r:
            self._require(r.item_results, item_result_id)
            self._require(r.skills, skill_id)
            if any(
                v.skill_id == skill_id for v in r.attempt_skill_results.for_owner(item_result_id)
            ):
                raise ApplicationError("item_result_exists")
            value = p.AttemptSkillResult(
                metadata=self._meta(),
                attempt_item_result_id=item_result_id,
                skill_id=skill_id,
                outcome=outcome,
                comment=comment,
            )
            r.attempt_skill_results.insert(value)
            return value

    def list_item_skill_results(self, item_result_id):
        return tuple(self._r.attempt_skill_results.for_owner(item_result_id))

    def skill_outcome_counts(self, offering_id, student_id=None, *, module_id=None):
        with self._transaction() as r:
            allowed = (
                {w.id for w in r.program_works.list() if w.module_id == module_id}
                if module_id
                else None
            )
            assessments = {
                a.id
                for a in r.assessments.for_offering(offering_id)
                if allowed is None or a.program_work_id in allowed
            }
            works = {
                w.id
                for w in r.works.for_assessments(assessments)
                if student_id is None or w.student_id == student_id
            }
            attempts = {a.id for a in r.attempts.for_works(works)}
            results = {v.id for v in r.item_results.list() if v.attempt_id in attempts}
            counts = defaultdict(lambda: defaultdict(int))
            for value in r.attempt_skill_results.list():
                if value.attempt_item_result_id in results:
                    counts[value.skill_id][value.outcome] += 1
            return {id: dict(values) for id, values in counts.items()}

    def cancel_lesson(self, original, reason=""):
        return self._update(self._r.lessons, original, cancelled=True, cancellation_reason=reason)

    def transfer_lesson(self, original, new_date):
        return self._update(
            self._r.lessons,
            original,
            lesson_date=new_date,
            planned_date=original.planned_date or original.lesson_date,
            cancelled=False,
        )
