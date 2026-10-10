-- Phase 5 additive frozen snapshot; v1/v2/v3 are unchanged.

CREATE TABLE question_cases (
	id TEXT NOT NULL,
	student_id TEXT NOT NULL,
	course_offering_id TEXT,
	title TEXT,
	opened_at INTEGER NOT NULL,
	closed_at INTEGER,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (title IS NULL OR length(trim(title)) > 0),
	CHECK (typeof(opened_at) = 'integer'),
	CHECK (closed_at IS NULL OR (typeof(closed_at) = 'integer' AND closed_at >= opened_at)),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT,
	FOREIGN KEY(course_offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT
);

CREATE INDEX question_cases_offering ON question_cases (course_offering_id);

CREATE INDEX question_cases_student ON question_cases (student_id, opened_at);

CREATE TRIGGER question_cases_metadata_update BEFORE UPDATE ON question_cases
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER question_cases_no_delete BEFORE DELETE ON question_cases
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE messages (
	id TEXT NOT NULL,
	question_case_id TEXT NOT NULL,
	author_role TEXT NOT NULL,
	channel TEXT NOT NULL,
	sent_at INTEGER NOT NULL,
	body TEXT NOT NULL,
	external_system TEXT,
	external_account_key TEXT,
	external_thread_id TEXT,
	external_message_id TEXT,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (author_role IN ('STUDENT', 'TEACHER')),
	CHECK (channel IN ('MANUAL', 'EMAIL', 'TELEGRAM', 'OTHER')),
	CHECK (typeof(sent_at) = 'integer'),
	CHECK (length(trim(body, char(9) || char(10) || char(13) || ' ')) > 0),
	CHECK ((external_system IS NULL AND external_account_key IS NULL AND external_thread_id IS NULL AND external_message_id IS NULL) OR (channel != 'MANUAL' AND external_system IS NOT NULL AND length(trim(external_system)) > 0 AND external_account_key IS NOT NULL AND length(trim(external_account_key)) > 0 AND external_thread_id IS NOT NULL AND length(trim(external_thread_id)) > 0 AND external_message_id IS NOT NULL AND length(trim(external_message_id)) > 0)),
	UNIQUE (external_system, external_account_key, external_thread_id, external_message_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT
);

CREATE INDEX messages_history ON messages (question_case_id, sent_at, created_at, id);

CREATE TRIGGER messages_metadata_update BEFORE UPDATE ON messages
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER messages_no_delete BEFORE DELETE ON messages
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE message_attachments (
	id TEXT NOT NULL,
	message_id TEXT NOT NULL,
	file_asset_id TEXT NOT NULL,
	caption TEXT,
	sort_order INTEGER DEFAULT 0 NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0),
	UNIQUE (message_id, file_asset_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE RESTRICT,
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
);

CREATE INDEX message_attachments_asset ON message_attachments (file_asset_id);

CREATE INDEX message_attachments_order ON message_attachments (message_id, sort_order);

CREATE TRIGGER message_attachments_metadata_update BEFORE UPDATE ON message_attachments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER message_attachments_no_delete BEFORE DELETE ON message_attachments
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE question_case_assessments (
	id TEXT NOT NULL,
	question_case_id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (question_case_id, assessment_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT,
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
);

CREATE INDEX question_case_assessments_target ON question_case_assessments (assessment_id);

CREATE TRIGGER question_case_assessments_metadata_update BEFORE UPDATE ON question_case_assessments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER question_case_assessments_no_delete BEFORE DELETE ON question_case_assessments
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE question_case_attempts (
	id TEXT NOT NULL,
	question_case_id TEXT NOT NULL,
	attempt_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (question_case_id, attempt_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT,
	FOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE RESTRICT
);

CREATE INDEX question_case_attempts_target ON question_case_attempts (attempt_id);

CREATE TRIGGER question_case_attempts_metadata_update BEFORE UPDATE ON question_case_attempts
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER question_case_attempts_no_delete BEFORE DELETE ON question_case_attempts
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE question_case_topics (
	id TEXT NOT NULL,
	question_case_id TEXT NOT NULL,
	topic_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (question_case_id, topic_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT,
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX question_case_topics_target ON question_case_topics (topic_id);

CREATE TRIGGER question_case_topics_metadata_update BEFORE UPDATE ON question_case_topics
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER question_case_topics_no_delete BEFORE DELETE ON question_case_topics
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TABLE question_case_skills (
	id TEXT NOT NULL,
	question_case_id TEXT NOT NULL,
	skill_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (question_case_id, skill_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT,
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX question_case_skills_target ON question_case_skills (skill_id);

CREATE TRIGGER question_case_skills_metadata_update BEFORE UPDATE ON question_case_skills
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER question_case_skills_no_delete BEFORE DELETE ON question_case_skills
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TRIGGER question_cases_immutable BEFORE UPDATE ON question_cases
WHEN NEW.student_id IS NOT OLD.student_id OR NEW.course_offering_id IS NOT OLD.course_offering_id OR NEW.opened_at IS NOT OLD.opened_at OR OLD.deleted_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'immutable question ownership or archived history'); END;

CREATE TRIGGER question_cases_active_insert BEFORE INSERT ON question_cases
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM students WHERE id=NEW.student_id AND deleted_at IS NULL) OR (NEW.course_offering_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM course_offerings WHERE id=NEW.course_offering_id AND deleted_at IS NULL))
BEGIN SELECT RAISE(ABORT, 'question requires active student and offering'); END;

CREATE TRIGGER question_cases_close_date BEFORE UPDATE ON question_cases
WHEN NEW.closed_at IS NOT NULL AND EXISTS(SELECT 1 FROM messages WHERE question_case_id=OLD.id AND deleted_at IS NULL AND sent_at > NEW.closed_at)
BEGIN SELECT RAISE(ABORT, 'question requires close after last message'); END;

CREATE TRIGGER messages_immutable BEFORE UPDATE ON messages
WHEN NEW.question_case_id IS NOT OLD.question_case_id OR NEW.author_role IS NOT OLD.author_role OR NEW.channel IS NOT OLD.channel OR NEW.sent_at IS NOT OLD.sent_at OR NEW.body IS NOT OLD.body OR NEW.external_system IS NOT OLD.external_system OR NEW.external_account_key IS NOT OLD.external_account_key OR NEW.external_thread_id IS NOT OLD.external_thread_id OR NEW.external_message_id IS NOT OLD.external_message_id OR OLD.deleted_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'immutable message facts or archived history'); END;

CREATE TRIGGER messages_active_insert BEFORE INSERT ON messages
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM question_cases q JOIN students s ON s.id=q.student_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.closed_at IS NULL AND s.deleted_at IS NULL AND NEW.sent_at >= q.opened_at)
BEGIN SELECT RAISE(ABORT, 'message requires open question and valid date'); END;

CREATE TRIGGER message_attachments_immutable BEFORE UPDATE ON message_attachments
WHEN NEW.message_id IS NOT OLD.message_id OR NEW.file_asset_id IS NOT OLD.file_asset_id OR OLD.deleted_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'immutable attachment ownership or detached history'); END;

CREATE TRIGGER message_attachments_active_insert BEFORE INSERT ON message_attachments
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM messages m JOIN question_cases q ON q.id=m.question_case_id JOIN students s ON s.id=q.student_id WHERE m.id=NEW.message_id AND m.deleted_at IS NULL AND q.deleted_at IS NULL AND s.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'attachment requires active file and message context'); END;

CREATE TRIGGER file_assets_archive_message_in_use BEFORE UPDATE OF deleted_at ON file_assets
WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM message_attachments WHERE file_asset_id=OLD.id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'file requires no active message attachments before archive'); END;

CREATE TRIGGER question_case_assessments_immutable BEFORE UPDATE ON question_case_assessments
WHEN NEW.question_case_id IS NOT OLD.question_case_id OR NEW.assessment_id IS NOT OLD.assessment_id
BEGIN SELECT RAISE(ABORT, 'immutable context endpoints'); END;

CREATE TRIGGER question_case_assessments_context_insert BEFORE INSERT ON question_case_assessments
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM question_cases q JOIN assessments t ON t.id=NEW.assessment_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.offering_id=q.course_offering_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_assessments_context_restore BEFORE UPDATE ON question_case_assessments
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM question_cases q JOIN assessments t ON t.id=NEW.assessment_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.offering_id=q.course_offering_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_attempts_immutable BEFORE UPDATE ON question_case_attempts
WHEN NEW.question_case_id IS NOT OLD.question_case_id OR NEW.attempt_id IS NOT OLD.attempt_id
BEGIN SELECT RAISE(ABORT, 'immutable context endpoints'); END;

CREATE TRIGGER question_case_attempts_context_insert BEFORE INSERT ON question_case_attempts
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM question_cases q JOIN attempts t ON t.id=NEW.attempt_id JOIN student_works w ON w.id=t.student_work_id JOIN assessments a ON a.id=w.assessment_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND w.student_id=q.student_id AND a.offering_id=q.course_offering_id AND w.deleted_at IS NULL AND a.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_attempts_context_restore BEFORE UPDATE ON question_case_attempts
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM question_cases q JOIN attempts t ON t.id=NEW.attempt_id JOIN student_works w ON w.id=t.student_work_id JOIN assessments a ON a.id=w.assessment_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND w.student_id=q.student_id AND a.offering_id=q.course_offering_id AND w.deleted_at IS NULL AND a.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_topics_immutable BEFORE UPDATE ON question_case_topics
WHEN NEW.question_case_id IS NOT OLD.question_case_id OR NEW.topic_id IS NOT OLD.topic_id
BEGIN SELECT RAISE(ABORT, 'immutable context endpoints'); END;

CREATE TRIGGER question_case_topics_context_insert BEFORE INSERT ON question_case_topics
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM question_cases q JOIN topics t ON t.id=NEW.topic_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.course_id=o.course_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_topics_context_restore BEFORE UPDATE ON question_case_topics
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM question_cases q JOIN topics t ON t.id=NEW.topic_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.course_id=o.course_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_skills_immutable BEFORE UPDATE ON question_case_skills
WHEN NEW.question_case_id IS NOT OLD.question_case_id OR NEW.skill_id IS NOT OLD.skill_id
BEGIN SELECT RAISE(ABORT, 'immutable context endpoints'); END;

CREATE TRIGGER question_case_skills_context_insert BEFORE INSERT ON question_case_skills
WHEN NEW.deleted_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM question_cases q JOIN skills t ON t.id=NEW.skill_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.course_id=o.course_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;

CREATE TRIGGER question_case_skills_context_restore BEFORE UPDATE ON question_case_skills
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM question_cases q JOIN skills t ON t.id=NEW.skill_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE q.id=NEW.question_case_id AND q.deleted_at IS NULL AND q.course_offering_id IS NOT NULL AND t.deleted_at IS NULL AND t.course_id=o.course_id)
BEGIN SELECT RAISE(ABORT, 'context requires matching active question and target'); END;
