-- Phase 4 additive snapshot. Historical v1/v2 are unchanged.

CREATE TABLE file_assets (
	id TEXT NOT NULL,
	original_filename TEXT NOT NULL,
	storage_key TEXT NOT NULL,
	mime_type TEXT NOT NULL,
	size_bytes INTEGER NOT NULL,
	sha256 TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (storage_key),
	CHECK (length(trim(original_filename)) > 0 AND instr(original_filename, '/') = 0 AND instr(original_filename, char(92)) = 0 AND instr(original_filename, ':') = 0),
	CHECK (length(trim(mime_type)) > 0),
	CHECK (typeof(size_bytes) = 'integer' AND size_bytes >= 0),
	CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
	CHECK (length(storage_key) BETWEEN 47 AND 54 AND substr(storage_key, 1, 6) = 'files/' AND substr(storage_key, 7, 2) = substr(id, 1, 2) AND substr(storage_key, 9, 1) = '/' AND substr(storage_key, 10, 36) = id AND substr(storage_key, 46, 1) = '.' AND substr(storage_key, 47) IN ('jpg','jpeg','png','webp','gif','bmp','tif','tiff','pdf','txt','md','csv','tsv','rtf','docx','xlsx','pptx','odt','ods','odp','zip','7z','bin')),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at))
);

CREATE INDEX file_assets_hash ON file_assets (sha256);

CREATE TRIGGER file_assets_metadata_update BEFORE UPDATE ON file_assets
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER file_assets_no_delete BEFORE DELETE ON file_assets
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE attempt_attachments (
	id TEXT NOT NULL,
	attempt_id TEXT NOT NULL,
	file_asset_id TEXT NOT NULL,
	caption TEXT,
	sort_order INTEGER DEFAULT 0 NOT NULL,
	details_json TEXT DEFAULT '{}' NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0),
	CHECK (json_valid(details_json) AND json_type(details_json) = 'object'),
	UNIQUE (attempt_id, file_asset_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE RESTRICT,
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
);

CREATE INDEX attempt_attachments_asset ON attempt_attachments (file_asset_id);

CREATE INDEX attempt_attachments_order ON attempt_attachments (attempt_id, sort_order);

CREATE TRIGGER attempt_attachments_metadata_update BEFORE UPDATE ON attempt_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER attempt_attachments_no_delete BEFORE DELETE ON attempt_attachments
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TRIGGER file_assets_immutable BEFORE UPDATE ON file_assets
WHEN NEW.original_filename IS NOT OLD.original_filename OR NEW.storage_key IS NOT OLD.storage_key
 OR NEW.mime_type IS NOT OLD.mime_type OR NEW.size_bytes IS NOT OLD.size_bytes OR NEW.sha256 IS NOT OLD.sha256
 OR (OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'immutable file asset'); END;

CREATE TRIGGER file_assets_archive_in_use BEFORE UPDATE OF deleted_at ON file_assets
WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM attempt_attachments WHERE file_asset_id = OLD.id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'file requires no active attachments before archive'); END;

CREATE TRIGGER attempt_attachments_immutable BEFORE UPDATE ON attempt_attachments
WHEN NEW.attempt_id IS NOT OLD.attempt_id OR NEW.file_asset_id IS NOT OLD.file_asset_id
 OR OLD.deleted_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'immutable attachment owner or detached history'); END;

CREATE TRIGGER attempt_attachments_active_insert BEFORE INSERT ON attempt_attachments
WHEN NEW.deleted_at IS NOT NULL
 OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id = NEW.file_asset_id AND deleted_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM attempts a JOIN student_works w ON w.id = a.student_work_id
 JOIN students s ON s.id = w.student_id JOIN assessments t ON t.id = w.assessment_id
 WHERE a.id = NEW.attempt_id AND a.deleted_at IS NULL AND w.deleted_at IS NULL AND s.deleted_at IS NULL AND t.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'attachment requires active file and attempt context'); END;
