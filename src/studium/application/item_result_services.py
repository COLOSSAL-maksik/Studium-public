"""Explicit teacher evaluation facts; analytics reads never write these records."""

from studium.application.errors import ApplicationError
from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.program import AttemptSkillResult


class ItemResultService:
    def create_attempt_item_result(
        self,
        attempt_id,
        assessment_item_id,
        *,
        outcome=None,
        score=None,
        max_score=None,
        teacher_comment=None,
        skill_results=(),
    ):
        if outcome is None and score is None:
            raise ApplicationError("item_result_empty")
        with self._transaction() as r:
            attempt = self._require(r.attempts, attempt_id)
            work = self._require(r.works, attempt.student_work_id)
            self._require(r.assessments, work.assessment_id)
            item = self._require(r.items, assessment_item_id)
            if item.assessment_id != work.assessment_id:
                raise ApplicationError("item_result_context_mismatch")
            if any(
                value.assessment_item_id == item.id
                for value in r.item_results.for_attempt(attempt_id)
            ):
                raise ApplicationError("item_result_exists")
            value = AttemptItemResult(
                metadata=self._meta(),
                attempt_id=attempt_id,
                assessment_item_id=assessment_item_id,
                outcome=outcome,
                score=score,
                max_score=max_score,
                teacher_comment=teacher_comment,
            )
            r.item_results.insert(value)
            for skill_id, skill_outcome, comment in skill_results:
                r.attempt_skill_results.insert(
                    AttemptSkillResult(
                        metadata=self._meta(),
                        attempt_item_result_id=value.id,
                        skill_id=skill_id,
                        outcome=skill_outcome,
                        comment=comment,
                    )
                )
            return value

    def list_attempt_item_results(self, attempt_id, *, include_deleted=False):
        with self._transaction() as r:
            self._require(r.attempts, attempt_id, historical=True)
            return tuple(r.item_results.for_attempt(attempt_id, include_deleted=include_deleted))

    def archive_attempt_item_result(self, original):
        with self._transaction() as r:
            self._require(r.item_results, original.id)
            r.item_results.soft_delete(
                original.id, expected_revision=original.revision, at=self._clock()
            )
