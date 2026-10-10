from dataclasses import dataclass

from studium.domain.entities import Attempt, Grade
from studium.domain.repositories import AttemptRepository


@dataclass(frozen=True)
class RecordAttempt:
    repository: AttemptRepository

    def execute(self, attempt: Attempt, *, grade: Grade | None = None) -> None:
        self.repository.append(attempt, grade=grade)
