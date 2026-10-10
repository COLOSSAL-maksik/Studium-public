"""v3 metadata: bytes and cache remain outside SQLite."""

from sqlalchemy import CheckConstraint, Column, Index, Integer, Text, UniqueConstraint, text

from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.learning import order, record, reference


class FileAssetRow(Base):
    __table__ = record(
        "file_assets",
        Column("original_filename", Text, nullable=False),
        Column("storage_key", Text, nullable=False),
        Column("mime_type", Text, nullable=False),
        Column("size_bytes", Integer, nullable=False),
        Column("sha256", Text, nullable=False),
        UniqueConstraint("storage_key"),
        CheckConstraint(
            "length(trim(original_filename)) > 0 AND instr(original_filename, '/') = 0 AND instr(original_filename, char(92)) = 0 AND instr(original_filename, ':') = 0"
        ),
        CheckConstraint("length(trim(mime_type)) > 0"),
        CheckConstraint("typeof(size_bytes) = 'integer' AND size_bytes >= 0"),
        CheckConstraint("length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'"),
        CheckConstraint(
            "length(storage_key) BETWEEN 47 AND 54 AND substr(storage_key, 1, 6) = 'files/' AND substr(storage_key, 7, 2) = substr(id, 1, 2) AND substr(storage_key, 9, 1) = '/' AND substr(storage_key, 10, 36) = id AND substr(storage_key, 46, 1) = '.' AND substr(storage_key, 47) IN ('jpg','jpeg','png','webp','gif','bmp','tif','tiff','pdf','txt','md','csv','tsv','rtf','doc','docx','xlsx','pptx','odt','ods','odp','zip','7z','bin')"
        ),
    )


class AttemptAttachmentRow(Base):
    __table__ = record(
        "attempt_attachments",
        reference("attempt_id", "attempts"),
        reference("file_asset_id", "file_assets"),
        Column("caption", Text),
        *order(),
        Column("details_json", Text, nullable=False, server_default=text("'{}'")),
        CheckConstraint("json_valid(details_json) AND json_type(details_json) = 'object'"),
        UniqueConstraint("attempt_id", "file_asset_id"),
    )


Index("file_assets_hash", FileAssetRow.sha256)
Index("attempt_attachments_order", AttemptAttachmentRow.attempt_id, AttemptAttachmentRow.sort_order)
Index("attempt_attachments_asset", AttemptAttachmentRow.file_asset_id)
