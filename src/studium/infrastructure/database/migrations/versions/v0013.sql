CREATE TABLE program_drafts (
	id TEXT NOT NULL,
	course_program_id TEXT NOT NULL,
	base_version_id TEXT,
	content_json TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (json_valid(content_json) AND json_type(content_json)='object'),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(course_program_id) REFERENCES course_programs (id) ON DELETE RESTRICT,
	FOREIGN KEY(base_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT
);

CREATE INDEX program_drafts_base_version_id_qa_idx ON program_drafts (base_version_id);

CREATE INDEX program_drafts_course_program_id_qa_idx ON program_drafts (course_program_id);

CREATE TRIGGER program_drafts_revision BEFORE UPDATE ON program_drafts
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER program_drafts_no_delete BEFORE DELETE ON program_drafts BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER program_drafts_immutable BEFORE UPDATE ON program_drafts WHEN NEW.course_program_id IS NOT OLD.course_program_id OR NEW.base_version_id IS NOT OLD.base_version_id BEGIN SELECT RAISE(ABORT,'immutable source'); END;

CREATE TABLE program_imports (
	id TEXT NOT NULL,
	program_version_id TEXT NOT NULL,
	origin TEXT NOT NULL,
	content_hash TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (program_version_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT
);

CREATE INDEX program_imports_program_version_id_qa_idx ON program_imports (program_version_id);

CREATE TRIGGER program_imports_revision BEFORE UPDATE ON program_imports
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER program_imports_no_delete BEFORE DELETE ON program_imports BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER program_imports_immutable BEFORE UPDATE ON program_imports WHEN NEW.program_version_id IS NOT OLD.program_version_id OR NEW.origin IS NOT OLD.origin OR NEW.content_hash IS NOT OLD.content_hash BEGIN SELECT RAISE(ABORT,'immutable source'); END;

CREATE TABLE plan_lessons (
	id TEXT NOT NULL,
	semester_plan_id TEXT NOT NULL,
	plan_module_id TEXT NOT NULL,
	program_version_id TEXT NOT NULL,
	lesson_id TEXT,
	source_key TEXT NOT NULL,
	baseline_json TEXT NOT NULL,
	current_json TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (json_valid(baseline_json) AND json_type(baseline_json)='object'),
	CHECK (json_valid(current_json) AND json_type(current_json)='object'),
	UNIQUE (semester_plan_id, program_version_id, source_key),
	UNIQUE (lesson_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(semester_plan_id) REFERENCES semester_plans (id) ON DELETE RESTRICT,
	FOREIGN KEY(plan_module_id) REFERENCES plan_modules (id) ON DELETE RESTRICT,
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT,
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE RESTRICT
);

CREATE INDEX plan_lessons_lesson_id_qa_idx ON plan_lessons (lesson_id);

CREATE INDEX plan_lessons_plan_module_id_qa_idx ON plan_lessons (plan_module_id);

CREATE INDEX plan_lessons_program_version_id_qa_idx ON plan_lessons (program_version_id);

CREATE INDEX plan_lessons_semester_plan_id_qa_idx ON plan_lessons (semester_plan_id);

CREATE TRIGGER plan_lessons_revision BEFORE UPDATE ON plan_lessons
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER plan_lessons_no_delete BEFORE DELETE ON plan_lessons BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER plan_lessons_immutable BEFORE UPDATE ON plan_lessons WHEN NEW.semester_plan_id IS NOT OLD.semester_plan_id OR NEW.plan_module_id IS NOT OLD.plan_module_id OR NEW.program_version_id IS NOT OLD.program_version_id OR NEW.source_key IS NOT OLD.source_key OR NEW.baseline_json IS NOT OLD.baseline_json BEGIN SELECT RAISE(ABORT,'immutable source'); END;

CREATE TRIGGER program_drafts_scope BEFORE INSERT ON program_drafts WHEN NEW.base_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_versions WHERE id=NEW.base_version_id AND course_program_id=NEW.course_program_id) BEGIN SELECT RAISE(ABORT,'draft source scope'); END;

CREATE TRIGGER plan_lessons_scope_insert BEFORE INSERT ON plan_lessons WHEN NOT EXISTS(
    SELECT 1 FROM semester_plans p JOIN plan_modules m ON m.semester_plan_id=p.id JOIN course_offerings o ON o.id=p.offering_id JOIN program_versions v ON v.id=NEW.program_version_id JOIN course_programs c ON c.id=v.course_program_id
    WHERE p.id=NEW.semester_plan_id AND m.id=NEW.plan_module_id AND c.course_id=o.course_id
    AND (NEW.lesson_id IS NULL OR EXISTS(SELECT 1 FROM lessons l WHERE l.id=NEW.lesson_id AND l.course_offering_id=p.offering_id)))
    BEGIN SELECT RAISE(ABORT,'planned lesson scope'); END;

CREATE TRIGGER plan_lessons_scope_update BEFORE UPDATE ON plan_lessons WHEN NOT EXISTS(
    SELECT 1 FROM semester_plans p JOIN plan_modules m ON m.semester_plan_id=p.id JOIN course_offerings o ON o.id=p.offering_id JOIN program_versions v ON v.id=NEW.program_version_id JOIN course_programs c ON c.id=v.course_program_id
    WHERE p.id=NEW.semester_plan_id AND m.id=NEW.plan_module_id AND c.course_id=o.course_id
    AND (NEW.lesson_id IS NULL OR EXISTS(SELECT 1 FROM lessons l WHERE l.id=NEW.lesson_id AND l.course_offering_id=p.offering_id)))
    BEGIN SELECT RAISE(ABORT,'planned lesson scope'); END;

CREATE TRIGGER plan_lessons_actual_binding BEFORE UPDATE ON plan_lessons
WHEN OLD.lesson_id IS NOT NULL AND NEW.lesson_id IS NOT OLD.lesson_id
BEGIN SELECT RAISE(ABORT,'immutable actual lesson binding'); END;

CREATE TRIGGER plan_lessons_source BEFORE INSERT ON plan_lessons
WHEN NOT EXISTS (
 SELECT 1 FROM program_versions v,
 json_each(v.content_json,'$.annual.semesters') s,
 json_each(s.value,'$.modules') m,
 json_each(m.value,'$.lessons') l,
 plan_content_sources source
 WHERE v.id=NEW.program_version_id AND json_extract(l.value,'$.key')=NEW.source_key
 AND source.plan_module_id=NEW.plan_module_id AND source.program_version_id=v.id
 AND json_extract(source.snapshot_json,'$.module.key')=json_extract(m.value,'$.key')
)
BEGIN SELECT RAISE(ABORT,'unknown source lesson'); END;
