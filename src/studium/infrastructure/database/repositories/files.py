from sqlalchemy import select

from studium.domain.entities import AttemptAttachment, FileAsset
from studium.infrastructure.database import models as m
from studium.infrastructure.database.models.files import AttemptAttachmentRow, FileAssetRow
from studium.infrastructure.database.repositories import (
    SqlAlchemyMutableRepository,
    SqlAlchemySoftDeleteRepository,
    domain_value,
)


class FileAssetRepository(SqlAlchemySoftDeleteRepository[FileAsset]):
    entity_type, row_type = FileAsset, FileAssetRow

    def insert(self, entity):
        with self._transaction() as session:
            self._insert(session, entity)


class AttemptAttachmentRepository(SqlAlchemyMutableRepository[AttemptAttachment]):
    entity_type, row_type = AttemptAttachment, AttemptAttachmentRow

    def for_attempt(self, attempt_id, *, include_deleted=False):
        query = select(self.row_type).where(self.row_type.attempt_id == attempt_id.value)
        return self._query_links(query, include_deleted)

    def for_student(self, student_id, *, include_deleted=False):
        query = (
            select(self.row_type)
            .join(m.AttemptRow, m.AttemptRow.id == self.row_type.attempt_id)
            .join(m.StudentWorkRow, m.StudentWorkRow.id == m.AttemptRow.student_work_id)
            .where(m.StudentWorkRow.student_id == student_id.value)
        )
        # Archived academic parents do not erase attachment history.
        return self._query_links(query, include_deleted)

    def for_asset(self, asset_id):
        return self._matching(self.row_type.file_asset_id, asset_id)

    def _query_links(self, query, include_deleted):
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        query = query.order_by(self.row_type.sort_order, self.row_type.created_at, self.row_type.id)
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]


ADAPTERS = {"file_assets": FileAssetRepository, "attempt_attachments": AttemptAttachmentRepository}
