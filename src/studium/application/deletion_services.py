"""Explicit, reversible removal from active work; never physical cascades."""

from dataclasses import dataclass

DELETE_REPOSITORIES = {
    "term": "terms",
    "course": "courses",
    "group": "groups",
    "student": "students",
    "assessment": "assessments",
    "work_program": "work_programs",
    "knowledge": "knowledge_entries",
    "ticket_set": "ticket_sets",
    "collection": "problem_collections",
    "module": "program_modules",
    "program_work": "program_works",
}


@dataclass(frozen=True)
class DeletionImpact:
    contexts: int = 0
    library_materials: int = 0
    dependents: int = 0


class DeletionService:
    def deletion_impact(self, kind, original):
        """Counts explain archived context without exposing database identifiers."""
        with self._transaction() as r:
            owner = {"term": "term_id", "course": "course_id", "group": "group_id"}.get(kind)
            contexts = (
                sum(getattr(o, owner) == original.id for o in r.offerings.list()) if owner else 0
            )
            materials = 0
            if kind == "course":
                materials = sum(
                    value.course_id == original.id
                    for name in (
                        "homework_definitions",
                        "homework_packs",
                        "problems",
                        "seminar_materials",
                        "literature_items",
                        "methodical_materials",
                    )
                    for value in getattr(r, name).list()
                )
            dependents = (
                sum(o.work_program_id == original.id for o in r.offerings.list())
                if kind == "work_program"
                else 0
            )
            return DeletionImpact(contexts, materials, dependents)

    def safe_delete(self, kind, original):
        repository = getattr(self._r, DELETE_REPOSITORIES[kind])
        repository.soft_delete(original.id, expected_revision=original.revision, at=self._clock())
        if kind == "term":
            active = self.active_term()
            if active:
                self.select_term(active.id)

    def get_course(self, id, *, historical=False):
        return self._require(self._r.courses, id, historical=historical)
