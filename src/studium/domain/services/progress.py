from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from studium.domain.entities import Attempt
from studium.domain.enums import AttemptResult, StudentWorkStatus
from studium.domain.value_objects import EntityId


@dataclass(frozen=True)
class StudentWorkProgress:
    status: StudentWorkStatus
    final_score: float | Decimal | None
    attempt_count: int

    @classmethod
    def from_history(
        cls, student_work_id: EntityId, history: Iterable[Attempt]
    ) -> "StudentWorkProgress":
        all_attempts = list(history)
        if (
            any(a.student_work_id != student_work_id for a in all_attempts)
            or len({a.id for a in all_attempts}) != len(all_attempts)
            or len({a.attempt_no for a in all_attempts}) != len(all_attempts)
        ):
            raise ValueError("History contains a foreign or duplicate attempt")
        attempts = sorted(
            (a for a in all_attempts if a.deleted_at is None), key=lambda a: a.attempt_no
        )
        status = StudentWorkStatus.NOT_STARTED
        score = None
        transitions = {
            AttemptResult.PRESENTED: StudentWorkStatus.SUBMITTED,
            AttemptResult.NEEDS_REVISION: StudentWorkStatus.REVISION_REQUIRED,
            AttemptResult.ACCEPTED: StudentWorkStatus.ACCEPTED,
        }
        for attempt in attempts:
            if attempt.result in transitions:
                status, score = transitions[attempt.result], attempt.score
            elif attempt.result == AttemptResult.SCORED:
                if status == StudentWorkStatus.NOT_STARTED:
                    status = StudentWorkStatus.SUBMITTED
                score = attempt.score
        return cls(status, score, len(attempts))
