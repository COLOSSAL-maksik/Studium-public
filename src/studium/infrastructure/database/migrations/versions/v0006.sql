-- Phase 6.6 additive schema; historical v1-v5 objects retained.



CREATE TABLE homework_definitions (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
	label TEXT DEFAULT '' NOT NULL, 
	description TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (json_valid(tags_json) AND json_type(tags_json) = 'array'), 
	CHECK (json_valid(details_json) AND json_type(details_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
)

;

CREATE INDEX homework_definitions_course_id ON homework_definitions (course_id);

CREATE TRIGGER homework_definitions_metadata_update BEFORE UPDATE ON homework_definitions
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER homework_definitions_no_delete BEFORE DELETE ON homework_definitions
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER homework_definitions_identity_update BEFORE UPDATE ON homework_definitions WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;

CREATE TRIGGER homework_definitions_tags_insert BEFORE INSERT ON homework_definitions WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;

CREATE TRIGGER homework_definitions_tags_update BEFORE UPDATE ON homework_definitions WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;


CREATE TABLE problems (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
	statement TEXT DEFAULT '' NOT NULL, 
	correct_answer TEXT DEFAULT '' NOT NULL, 
	solution TEXT DEFAULT '' NOT NULL, 
	difficulty TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (json_valid(tags_json) AND json_type(tags_json) = 'array'), 
	CHECK (json_valid(details_json) AND json_type(details_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
)

;

CREATE INDEX problems_course_id ON problems (course_id);

CREATE TRIGGER problems_metadata_update BEFORE UPDATE ON problems
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problems_no_delete BEFORE DELETE ON problems
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problems_identity_update BEFORE UPDATE ON problems WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;

CREATE TRIGGER problems_tags_insert BEFORE INSERT ON problems WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;

CREATE TRIGGER problems_tags_update BEFORE UPDATE ON problems WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;


CREATE TABLE problem_collections (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
)

;

CREATE INDEX problem_collections_course_id ON problem_collections (course_id);

CREATE TRIGGER problem_collections_metadata_update BEFORE UPDATE ON problem_collections
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problem_collections_no_delete BEFORE DELETE ON problem_collections
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problem_collections_identity_update BEFORE UPDATE ON problem_collections WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE problem_collection_members (
	id TEXT NOT NULL, 
	collection_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (collection_id, problem_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(collection_id) REFERENCES problem_collections (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
)

;

CREATE INDEX problem_collection_members_collection_id ON problem_collection_members (collection_id);

CREATE INDEX problem_collection_members_problem_id ON problem_collection_members (problem_id);

CREATE TRIGGER problem_collection_members_metadata_update BEFORE UPDATE ON problem_collection_members
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problem_collection_members_no_delete BEFORE DELETE ON problem_collection_members
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problem_collection_members_identity_update BEFORE UPDATE ON problem_collection_members WHEN NEW.collection_id IS NOT OLD.collection_id OR NEW.problem_id IS NOT OLD.problem_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE seminar_materials (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
	planned_week INTEGER, 
	plan_text TEXT DEFAULT '' NOT NULL, 
	full_text TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1)), 
	CHECK (length(trim(title)) > 0), 
	CHECK (json_valid(tags_json) AND json_type(tags_json) = 'array'), 
	CHECK (json_valid(details_json) AND json_type(details_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
)

;

CREATE INDEX seminar_materials_course_id ON seminar_materials (course_id);

CREATE TRIGGER seminar_materials_metadata_update BEFORE UPDATE ON seminar_materials
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER seminar_materials_no_delete BEFORE DELETE ON seminar_materials
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER seminar_materials_identity_update BEFORE UPDATE ON seminar_materials WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;

CREATE TRIGGER seminar_materials_tags_insert BEFORE INSERT ON seminar_materials WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;

CREATE TRIGGER seminar_materials_tags_update BEFORE UPDATE ON seminar_materials WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;


CREATE TABLE seminar_material_topics (
	id TEXT NOT NULL, 
	seminar_material_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (seminar_material_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(seminar_material_id) REFERENCES seminar_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX seminar_material_topics_seminar_material_id ON seminar_material_topics (seminar_material_id);

CREATE INDEX seminar_material_topics_topic_id ON seminar_material_topics (topic_id);

CREATE TRIGGER seminar_material_topics_metadata_update BEFORE UPDATE ON seminar_material_topics
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER seminar_material_topics_no_delete BEFORE DELETE ON seminar_material_topics
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER seminar_material_topics_identity_update BEFORE UPDATE ON seminar_material_topics WHEN NEW.seminar_material_id IS NOT OLD.seminar_material_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE literature_items (
	id TEXT NOT NULL, 
	course_id TEXT, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
	authors TEXT DEFAULT '' NOT NULL, 
	year INTEGER, 
	type TEXT DEFAULT 'OTHER' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (year IS NULL OR (typeof(year) = 'integer' AND year BETWEEN 1 AND 9999)), 
	CHECK (type IN ('TEXTBOOK','STUDY_GUIDE','METHOD_GUIDE','ARTICLE','OTHER')), 
	CHECK (length(trim(title)) > 0), 
	CHECK (json_valid(tags_json) AND json_type(tags_json) = 'array'), 
	CHECK (json_valid(details_json) AND json_type(details_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
)

;

CREATE INDEX literature_items_course_id ON literature_items (course_id);

CREATE TRIGGER literature_items_metadata_update BEFORE UPDATE ON literature_items
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER literature_items_no_delete BEFORE DELETE ON literature_items
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER literature_items_identity_update BEFORE UPDATE ON literature_items WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;

CREATE TRIGGER literature_items_tags_insert BEFORE INSERT ON literature_items WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;

CREATE TRIGGER literature_items_tags_update BEFORE UPDATE ON literature_items WHEN EXISTS(SELECT 1 FROM json_each(NEW.tags_json) WHERE type != 'text' OR length(trim(value))=0) BEGIN SELECT RAISE(ABORT, 'invalid tags'); END;


CREATE TABLE homework_attachments (
	id TEXT NOT NULL, 
	homework_definition_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	caption TEXT DEFAULT '' NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	role TEXT DEFAULT 'STATEMENT' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (role IN ('STATEMENT','REFERENCE','SOLUTION')), 
	UNIQUE (homework_definition_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(homework_definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX homework_attachments_file_asset_id ON homework_attachments (file_asset_id);

CREATE INDEX homework_attachments_homework_definition_id ON homework_attachments (homework_definition_id);

CREATE TRIGGER homework_attachments_metadata_update BEFORE UPDATE ON homework_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER homework_attachments_no_delete BEFORE DELETE ON homework_attachments
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER homework_attachments_identity_update BEFORE UPDATE ON homework_attachments WHEN NEW.homework_definition_id IS NOT OLD.homework_definition_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE problem_attachments (
	id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	caption TEXT DEFAULT '' NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	role TEXT DEFAULT 'STATEMENT' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (role IN ('STATEMENT','REFERENCE','SOLUTION')), 
	UNIQUE (problem_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX problem_attachments_file_asset_id ON problem_attachments (file_asset_id);

CREATE INDEX problem_attachments_problem_id ON problem_attachments (problem_id);

CREATE TRIGGER problem_attachments_metadata_update BEFORE UPDATE ON problem_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problem_attachments_no_delete BEFORE DELETE ON problem_attachments
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problem_attachments_identity_update BEFORE UPDATE ON problem_attachments WHEN NEW.problem_id IS NOT OLD.problem_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE seminar_attachments (
	id TEXT NOT NULL, 
	seminar_material_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	caption TEXT DEFAULT '' NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	role TEXT DEFAULT 'STATEMENT' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (role IN ('STATEMENT','REFERENCE','SOLUTION')), 
	UNIQUE (seminar_material_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(seminar_material_id) REFERENCES seminar_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX seminar_attachments_file_asset_id ON seminar_attachments (file_asset_id);

CREATE INDEX seminar_attachments_seminar_material_id ON seminar_attachments (seminar_material_id);

CREATE TRIGGER seminar_attachments_metadata_update BEFORE UPDATE ON seminar_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER seminar_attachments_no_delete BEFORE DELETE ON seminar_attachments
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER seminar_attachments_identity_update BEFORE UPDATE ON seminar_attachments WHEN NEW.seminar_material_id IS NOT OLD.seminar_material_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE literature_attachments (
	id TEXT NOT NULL, 
	literature_item_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	caption TEXT DEFAULT '' NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	role TEXT DEFAULT 'STATEMENT' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (role IN ('STATEMENT','REFERENCE','SOLUTION')), 
	UNIQUE (literature_item_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(literature_item_id) REFERENCES literature_items (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX literature_attachments_file_asset_id ON literature_attachments (file_asset_id);

CREATE INDEX literature_attachments_literature_item_id ON literature_attachments (literature_item_id);

CREATE TRIGGER literature_attachments_metadata_update BEFORE UPDATE ON literature_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER literature_attachments_no_delete BEFORE DELETE ON literature_attachments
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER literature_attachments_identity_update BEFORE UPDATE ON literature_attachments WHEN NEW.literature_item_id IS NOT OLD.literature_item_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE ticket_sets (
	id TEXT NOT NULL, 
	course_offering_id TEXT NOT NULL, 
	assessment_id TEXT, 
	title TEXT NOT NULL, 
	criteria_json TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (json_valid(criteria_json) AND json_type(criteria_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
)

;

CREATE INDEX ticket_sets_assessment_id ON ticket_sets (assessment_id);

CREATE INDEX ticket_sets_course_offering_id ON ticket_sets (course_offering_id);

CREATE TRIGGER ticket_sets_metadata_update BEFORE UPDATE ON ticket_sets
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER ticket_sets_no_delete BEFORE DELETE ON ticket_sets
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER ticket_sets_identity_update BEFORE UPDATE ON ticket_sets WHEN NEW.course_offering_id IS NOT OLD.course_offering_id OR NEW.assessment_id IS NOT OLD.assessment_id OR NEW.title IS NOT OLD.title OR NEW.criteria_json IS NOT OLD.criteria_json BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE tickets (
	id TEXT NOT NULL, 
	ticket_set_id TEXT NOT NULL, 
	number INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(number) = 'integer' AND number >= 1), 
	UNIQUE (ticket_set_id, number), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(ticket_set_id) REFERENCES ticket_sets (id) ON DELETE RESTRICT
)

;

CREATE INDEX tickets_ticket_set_id ON tickets (ticket_set_id);

CREATE TRIGGER tickets_metadata_update BEFORE UPDATE ON tickets
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER tickets_no_delete BEFORE DELETE ON tickets
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER tickets_identity_update BEFORE UPDATE ON tickets WHEN NEW.ticket_set_id IS NOT OLD.ticket_set_id OR NEW.number IS NOT OLD.number BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE ticket_problems (
	id TEXT NOT NULL, 
	ticket_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	position INTEGER NOT NULL, 
	source_revision INTEGER NOT NULL, 
	title_snapshot TEXT DEFAULT '' NOT NULL, 
	statement_snapshot TEXT DEFAULT '' NOT NULL, 
	teacher_snapshot_json TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(position) = 'integer' AND position >= 1), 
	CHECK (typeof(source_revision) = 'integer' AND source_revision >= 1), 
	CHECK (length(trim(title_snapshot)) > 0), 
	CHECK (json_valid(teacher_snapshot_json) AND json_type(teacher_snapshot_json) = 'object'), 
	UNIQUE (ticket_id, position), 
	UNIQUE (ticket_id, problem_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
)

;

CREATE INDEX ticket_problems_problem_id ON ticket_problems (problem_id);

CREATE INDEX ticket_problems_ticket_id ON ticket_problems (ticket_id);

CREATE TRIGGER ticket_problems_metadata_update BEFORE UPDATE ON ticket_problems
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER ticket_problems_no_delete BEFORE DELETE ON ticket_problems
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER ticket_problems_identity_update BEFORE UPDATE ON ticket_problems WHEN NEW.ticket_id IS NOT OLD.ticket_id OR NEW.problem_id IS NOT OLD.problem_id OR NEW.position IS NOT OLD.position OR NEW.source_revision IS NOT OLD.source_revision OR NEW.title_snapshot IS NOT OLD.title_snapshot OR NEW.statement_snapshot IS NOT OLD.statement_snapshot OR NEW.teacher_snapshot_json IS NOT OLD.teacher_snapshot_json BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE ticket_problem_files (
	id TEXT NOT NULL, 
	ticket_problem_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	role TEXT NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (role IN ('STATEMENT','REFERENCE','SOLUTION')), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	UNIQUE (ticket_problem_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(ticket_problem_id) REFERENCES ticket_problems (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX ticket_problem_files_file_asset_id ON ticket_problem_files (file_asset_id);

CREATE INDEX ticket_problem_files_ticket_problem_id ON ticket_problem_files (ticket_problem_id);

CREATE TRIGGER ticket_problem_files_metadata_update BEFORE UPDATE ON ticket_problem_files
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER ticket_problem_files_no_delete BEFORE DELETE ON ticket_problem_files
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER ticket_problem_files_identity_update BEFORE UPDATE ON ticket_problem_files WHEN NEW.ticket_problem_id IS NOT OLD.ticket_problem_id OR NEW.file_asset_id IS NOT OLD.file_asset_id OR NEW.role IS NOT OLD.role OR NEW.sort_order IS NOT OLD.sort_order BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;


CREATE TABLE ticket_assignments (
	id TEXT NOT NULL, 
	ticket_set_id TEXT NOT NULL, 
	ticket_id TEXT NOT NULL, 
	enrollment_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (ticket_set_id, enrollment_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(ticket_set_id) REFERENCES ticket_sets (id) ON DELETE RESTRICT, 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE RESTRICT, 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE RESTRICT
)

;

CREATE INDEX ticket_assignments_enrollment_id ON ticket_assignments (enrollment_id);

CREATE INDEX ticket_assignments_ticket_id ON ticket_assignments (ticket_id);

CREATE INDEX ticket_assignments_ticket_set_id ON ticket_assignments (ticket_set_id);

CREATE TRIGGER ticket_assignments_metadata_update BEFORE UPDATE ON ticket_assignments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
 OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER ticket_assignments_no_delete BEFORE DELETE ON ticket_assignments
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER ticket_assignments_identity_update BEFORE UPDATE ON ticket_assignments WHEN NEW.ticket_set_id IS NOT OLD.ticket_set_id OR NEW.enrollment_id IS NOT OLD.enrollment_id BEGIN SELECT RAISE(ABORT, 'immutable content ownership or snapshot'); END;

ALTER TABLE assessments ADD COLUMN planned_issue_week INTEGER
 CHECK(planned_issue_week IS NULL OR (typeof(planned_issue_week) = 'integer' AND planned_issue_week >= 1));

ALTER TABLE assessments ADD COLUMN planned_due_week INTEGER
 CHECK(planned_due_week IS NULL OR (typeof(planned_due_week) = 'integer' AND planned_due_week >= 1))
 CHECK(planned_issue_week IS NULL OR planned_due_week IS NULL OR planned_due_week >= planned_issue_week);

ALTER TABLE assessments ADD COLUMN homework_definition_id TEXT REFERENCES homework_definitions(id) ON DELETE NO ACTION;

ALTER TABLE lessons ADD COLUMN type TEXT NOT NULL DEFAULT 'SEMINAR' CHECK(type IN ('SEMINAR','LECTURE'));

CREATE INDEX assessments_homework_definition ON assessments(homework_definition_id);

CREATE TRIGGER assessments_homework_lock BEFORE UPDATE OF homework_definition_id ON assessments
WHEN NEW.homework_definition_id IS NOT OLD.homework_definition_id AND EXISTS(SELECT 1 FROM analytics_locked_assessments WHERE id=OLD.id)
BEGIN SELECT RAISE(ABORT, 'immutable assessment semantics after first attempt'); END;

ALTER TABLE academic_terms ADD COLUMN week_utc_offset_minutes INTEGER NOT NULL DEFAULT 180 CHECK(typeof(week_utc_offset_minutes) = 'integer' AND week_utc_offset_minutes BETWEEN -840 AND 840);

CREATE TRIGGER academic_terms_week_calendar_lock BEFORE UPDATE ON academic_terms WHEN (NEW.starts_on IS NOT OLD.starts_on OR NEW.week_utc_offset_minutes IS NOT OLD.week_utc_offset_minutes) AND EXISTS(SELECT 1 FROM course_offerings o JOIN assessments a ON a.offering_id=o.id JOIN analytics_locked_assessments l ON l.id=a.id WHERE o.term_id=OLD.id AND (a.planned_issue_week IS NOT NULL OR a.planned_due_week IS NOT NULL)) BEGIN SELECT RAISE(ABORT, 'immutable historical academic week calendar'); END;

CREATE TRIGGER problem_collection_members_content_context_insert BEFORE INSERT ON problem_collection_members WHEN NOT EXISTS(SELECT 1 FROM problems p JOIN problem_collections c ON c.course_id=p.course_id WHERE p.id=NEW.problem_id AND c.id=NEW.collection_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER problem_collection_members_content_context_update BEFORE UPDATE ON problem_collection_members WHEN NOT EXISTS(SELECT 1 FROM problems p JOIN problem_collections c ON c.course_id=p.course_id WHERE p.id=NEW.problem_id AND c.id=NEW.collection_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER seminar_material_topics_content_context_insert BEFORE INSERT ON seminar_material_topics WHEN NOT EXISTS(SELECT 1 FROM seminar_materials m JOIN topics t ON t.course_id=m.course_id WHERE m.id=NEW.seminar_material_id AND t.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER seminar_material_topics_content_context_update BEFORE UPDATE ON seminar_material_topics WHEN NOT EXISTS(SELECT 1 FROM seminar_materials m JOIN topics t ON t.course_id=m.course_id WHERE m.id=NEW.seminar_material_id AND t.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER assessments_content_context_insert BEFORE INSERT ON assessments WHEN NEW.homework_definition_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM homework_definitions h JOIN course_offerings o ON o.course_id=h.course_id WHERE h.id=NEW.homework_definition_id AND o.id=NEW.offering_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER assessments_content_context_update BEFORE UPDATE ON assessments WHEN NEW.homework_definition_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM homework_definitions h JOIN course_offerings o ON o.course_id=h.course_id WHERE h.id=NEW.homework_definition_id AND o.id=NEW.offering_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_sets_content_context_insert BEFORE INSERT ON ticket_sets WHEN NEW.assessment_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM assessments a WHERE a.id=NEW.assessment_id AND a.offering_id=NEW.course_offering_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_sets_content_context_update BEFORE UPDATE ON ticket_sets WHEN NEW.assessment_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM assessments a WHERE a.id=NEW.assessment_id AND a.offering_id=NEW.course_offering_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_problems_content_context_insert BEFORE INSERT ON ticket_problems WHEN NOT EXISTS(SELECT 1 FROM tickets t JOIN ticket_sets s ON s.id=t.ticket_set_id JOIN course_offerings o ON o.id=s.course_offering_id JOIN problems p ON p.course_id=o.course_id WHERE t.id=NEW.ticket_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_problems_content_context_update BEFORE UPDATE ON ticket_problems WHEN NOT EXISTS(SELECT 1 FROM tickets t JOIN ticket_sets s ON s.id=t.ticket_set_id JOIN course_offerings o ON o.id=s.course_offering_id JOIN problems p ON p.course_id=o.course_id WHERE t.id=NEW.ticket_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_assignments_content_context_insert BEFORE INSERT ON ticket_assignments WHEN NOT EXISTS(SELECT 1 FROM tickets t JOIN ticket_sets s ON s.id=t.ticket_set_id JOIN enrollments e ON e.offering_id=s.course_offering_id WHERE t.id=NEW.ticket_id AND s.id=NEW.ticket_set_id AND e.id=NEW.enrollment_id) OR (NEW.deleted_at IS NULL AND EXISTS(SELECT 1 FROM ticket_assignments a JOIN enrollments e ON e.id=a.enrollment_id JOIN enrollments n ON n.student_id=e.student_id WHERE n.id=NEW.enrollment_id AND a.ticket_set_id=NEW.ticket_set_id AND a.deleted_at IS NULL AND a.id != NEW.id)) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER ticket_assignments_content_context_update BEFORE UPDATE ON ticket_assignments WHEN NOT EXISTS(SELECT 1 FROM tickets t JOIN ticket_sets s ON s.id=t.ticket_set_id JOIN enrollments e ON e.offering_id=s.course_offering_id WHERE t.id=NEW.ticket_id AND s.id=NEW.ticket_set_id AND e.id=NEW.enrollment_id) OR (NEW.deleted_at IS NULL AND EXISTS(SELECT 1 FROM ticket_assignments a JOIN enrollments e ON e.id=a.enrollment_id JOIN enrollments n ON n.student_id=e.student_id WHERE n.id=NEW.enrollment_id AND a.ticket_set_id=NEW.ticket_set_id AND a.deleted_at IS NULL AND a.id != NEW.id)) BEGIN SELECT RAISE(ABORT, 'content link requires matching course/offering'); END;

CREATE TRIGGER homework_attachments_active_insert BEFORE INSERT ON homework_attachments WHEN NOT EXISTS(SELECT 1 FROM homework_definitions WHERE id=NEW.homework_definition_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'attachment requires active endpoints'); END;

CREATE TRIGGER file_assets_homework_attachments_insert BEFORE INSERT ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM homework_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_homework_attachments_update BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM homework_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER problem_attachments_active_insert BEFORE INSERT ON problem_attachments WHEN NOT EXISTS(SELECT 1 FROM problems WHERE id=NEW.problem_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'attachment requires active endpoints'); END;

CREATE TRIGGER file_assets_problem_attachments_insert BEFORE INSERT ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM problem_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_problem_attachments_update BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM problem_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER seminar_attachments_active_insert BEFORE INSERT ON seminar_attachments WHEN NOT EXISTS(SELECT 1 FROM seminar_materials WHERE id=NEW.seminar_material_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'attachment requires active endpoints'); END;

CREATE TRIGGER file_assets_seminar_attachments_insert BEFORE INSERT ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM seminar_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_seminar_attachments_update BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM seminar_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER literature_attachments_active_insert BEFORE INSERT ON literature_attachments WHEN NOT EXISTS(SELECT 1 FROM literature_items WHERE id=NEW.literature_item_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'attachment requires active endpoints'); END;

CREATE TRIGGER file_assets_literature_attachments_insert BEFORE INSERT ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM literature_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_literature_attachments_update BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM literature_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_ticket_snapshot BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM ticket_problem_files WHERE file_asset_id=NEW.id) BEGIN SELECT RAISE(ABORT, 'asset belongs to immutable ticket snapshot'); END;
