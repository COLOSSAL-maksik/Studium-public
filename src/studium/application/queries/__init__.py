from dataclasses import dataclass

from studium.domain.repositories import StudentWorkRepository
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import EntityId


@dataclass(frozen=True)
class GetStudentWorkProgress:
    repository: StudentWorkRepository

    def execute(self, id: EntityId) -> StudentWorkProgress:
        return self.repository.progress(id)
