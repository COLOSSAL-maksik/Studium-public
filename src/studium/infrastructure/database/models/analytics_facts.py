"""v5 mappings; historical evidence is protected by additive SQL triggers."""

from sqlalchemy import REAL, CheckConstraint, Column, Index, Text, text

from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.learning import record, reference


class AttemptItemResultRow(Base):
    __table__ = record(
        "attempt_item_results",
        reference("attempt_id", "attempts"),
        reference("assessment_item_id", "assessment_items"),
        Column("outcome", Text),
        Column("score", REAL),
        Column("max_score", REAL),
        Column("teacher_comment", Text),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('CORRECT', 'PARTIAL', 'INCORRECT', 'NOT_EVALUATED')"
        ),
        CheckConstraint("outcome IS NOT NULL OR score IS NOT NULL"),
        CheckConstraint(
            "score IS NULL OR (typeof(score) IN ('real', 'integer') AND score >= 0 AND score <= 1.7976931348623157e308)"
        ),
        CheckConstraint(
            "max_score IS NULL OR (typeof(max_score) IN ('real', 'integer') AND max_score > 0 AND max_score <= 1.7976931348623157e308)"
        ),
        CheckConstraint("score IS NULL OR max_score IS NULL OR score <= max_score"),
    )


Index(
    "attempt_item_results_active_pair",
    AttemptItemResultRow.__table__.c.attempt_id,
    AttemptItemResultRow.__table__.c.assessment_item_id,
    unique=True,
    sqlite_where=text("deleted_at IS NULL"),
)
Index("attempt_item_results_item", AttemptItemResultRow.__table__.c.assessment_item_id)
