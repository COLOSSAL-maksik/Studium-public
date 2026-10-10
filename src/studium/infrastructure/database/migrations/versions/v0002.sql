-- Immutable production v2 snapshot; generated once and reviewed.


CREATE TABLE topics (
	id TEXT NOT NULL,
	course_id TEXT NOT NULL,
	parent_topic_id TEXT,
	title TEXT NOT NULL,
	description TEXT DEFAULT '' NOT NULL,
	sort_order INTEGER DEFAULT 0 NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (length(trim(title)) > 0),
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0),
	CHECK (parent_topic_id IS NULL OR parent_topic_id != id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT,
	FOREIGN KEY(parent_topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX topics_lookup ON topics (course_id, parent_topic_id, sort_order);

CREATE TRIGGER topics_metadata_update BEFORE UPDATE ON topics
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER topics_preserve_history BEFORE DELETE ON topics
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE skills (
	id TEXT NOT NULL,
	course_id TEXT NOT NULL,
	title TEXT NOT NULL,
	description TEXT DEFAULT '' NOT NULL,
	sort_order INTEGER DEFAULT 0 NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (length(trim(title)) > 0),
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
);

CREATE INDEX skills_lookup ON skills (course_id, sort_order);

CREATE TRIGGER skills_metadata_update BEFORE UPDATE ON skills
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER skills_preserve_history BEFORE DELETE ON skills
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE lessons (
	id TEXT NOT NULL,
	course_offering_id TEXT NOT NULL,
	lesson_date TEXT NOT NULL,
	title TEXT DEFAULT '' NOT NULL,
	notes TEXT DEFAULT '' NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (length(lesson_date) = 10 AND lesson_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(lesson_date, 1, 4) != '0000' AND date(lesson_date, '+0 days') IS NOT NULL AND date(lesson_date, '+0 days') = lesson_date),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(course_offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT
);

CREATE INDEX lessons_lookup ON lessons (course_offering_id, lesson_date);

CREATE TRIGGER lessons_metadata_update BEFORE UPDATE ON lessons
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER lessons_preserve_history BEFORE DELETE ON lessons
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE attendance (
	id TEXT NOT NULL,
	lesson_id TEXT NOT NULL,
	enrollment_id TEXT NOT NULL,
	status TEXT NOT NULL,
	comment TEXT DEFAULT '' NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (lesson_id, enrollment_id),
	CHECK (status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED', 'UNKNOWN')),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE RESTRICT,
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE RESTRICT
);

CREATE INDEX attendance_lookup ON attendance (enrollment_id);

CREATE TRIGGER attendance_metadata_update BEFORE UPDATE ON attendance
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER attendance_preserve_history BEFORE DELETE ON attendance
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE assessment_items (
	id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	title TEXT NOT NULL,
	description TEXT DEFAULT '' NOT NULL,
	sort_order INTEGER DEFAULT 0 NOT NULL,
	max_score REAL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (length(trim(title)) > 0),
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0),
	CHECK (max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
);

CREATE INDEX assessment_items_lookup ON assessment_items (assessment_id, sort_order);

CREATE TRIGGER assessment_items_metadata_update BEFORE UPDATE ON assessment_items
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER assessment_items_preserve_history BEFORE DELETE ON assessment_items
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE topic_skills (
	id TEXT NOT NULL,
	topic_id TEXT NOT NULL,
	skill_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (topic_id, skill_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT,
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX topic_skills_lookup ON topic_skills (skill_id);

CREATE TRIGGER topic_skills_metadata_update BEFORE UPDATE ON topic_skills
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER topic_skills_preserve_history BEFORE DELETE ON topic_skills
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE lesson_topics (
	id TEXT NOT NULL,
	lesson_id TEXT NOT NULL,
	topic_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (lesson_id, topic_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE RESTRICT,
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX lesson_topics_lookup ON lesson_topics (topic_id);

CREATE TRIGGER lesson_topics_metadata_update BEFORE UPDATE ON lesson_topics
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER lesson_topics_preserve_history BEFORE DELETE ON lesson_topics
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE assessment_topics (
	id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	topic_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (assessment_id, topic_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT,
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX assessment_topics_lookup ON assessment_topics (topic_id);

CREATE TRIGGER assessment_topics_metadata_update BEFORE UPDATE ON assessment_topics
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER assessment_topics_preserve_history BEFORE DELETE ON assessment_topics
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE assessment_skills (
	id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	skill_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (assessment_id, skill_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT,
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX assessment_skills_lookup ON assessment_skills (skill_id);

CREATE TRIGGER assessment_skills_metadata_update BEFORE UPDATE ON assessment_skills
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER assessment_skills_preserve_history BEFORE DELETE ON assessment_skills
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE assessment_item_topics (
	id TEXT NOT NULL,
	assessment_item_id TEXT NOT NULL,
	topic_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (assessment_item_id, topic_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(assessment_item_id) REFERENCES assessment_items (id) ON DELETE RESTRICT,
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX assessment_item_topics_lookup ON assessment_item_topics (topic_id);

CREATE TRIGGER assessment_item_topics_metadata_update BEFORE UPDATE ON assessment_item_topics
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER assessment_item_topics_preserve_history BEFORE DELETE ON assessment_item_topics
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TABLE assessment_item_skills (
	id TEXT NOT NULL,
	assessment_item_id TEXT NOT NULL,
	skill_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (assessment_item_id, skill_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(assessment_item_id) REFERENCES assessment_items (id) ON DELETE RESTRICT,
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX assessment_item_skills_lookup ON assessment_item_skills (skill_id);

CREATE TRIGGER assessment_item_skills_metadata_update BEFORE UPDATE ON assessment_item_skills
WHEN NEW.id != OLD.id OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'metadata requires stable identity and next revision'); END;

CREATE TRIGGER assessment_item_skills_preserve_history BEFORE DELETE ON assessment_item_skills
BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER topics_identity_update BEFORE UPDATE ON topics
WHEN NEW.course_id IS NOT OLD.course_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER skills_identity_update BEFORE UPDATE ON skills
WHEN NEW.course_id IS NOT OLD.course_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER lessons_identity_update BEFORE UPDATE ON lessons
WHEN NEW.course_offering_id IS NOT OLD.course_offering_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER assessment_items_identity_update BEFORE UPDATE ON assessment_items
WHEN NEW.assessment_id IS NOT OLD.assessment_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER attendance_identity_update BEFORE UPDATE ON attendance
WHEN NEW.lesson_id IS NOT OLD.lesson_id OR NEW.enrollment_id IS NOT OLD.enrollment_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER topics_course_insert BEFORE INSERT ON topics
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM courses WHERE id=NEW.course_id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'record requires active course'); END;

CREATE TRIGGER topics_course_update BEFORE UPDATE ON topics
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM courses WHERE id=NEW.course_id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'record requires active course'); END;

CREATE TRIGGER skills_course_insert BEFORE INSERT ON skills
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM courses WHERE id=NEW.course_id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'record requires active course'); END;

CREATE TRIGGER skills_course_update BEFORE UPDATE ON skills
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM courses WHERE id=NEW.course_id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'record requires active course'); END;

CREATE TRIGGER topics_parent_insert BEFORE INSERT ON topics
WHEN NEW.parent_topic_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM topics p WHERE p.id=NEW.parent_topic_id AND p.course_id=NEW.course_id AND (NEW.deleted_at IS NOT NULL OR p.deleted_at IS NULL))
BEGIN SELECT RAISE(ABORT, 'topic requires parent in same course'); END;

CREATE TRIGGER topics_parent_update BEFORE UPDATE ON topics
WHEN NEW.parent_topic_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM topics p WHERE p.id=NEW.parent_topic_id AND p.course_id=NEW.course_id AND (NEW.deleted_at IS NOT NULL OR p.deleted_at IS NULL))
BEGIN SELECT RAISE(ABORT, 'topic requires parent in same course'); END;

CREATE TRIGGER topics_cycle_insert BEFORE INSERT ON topics
WHEN NEW.parent_topic_id IS NOT NULL AND EXISTS(WITH RECURSIVE ancestors(id,parent_topic_id) AS (SELECT id,parent_topic_id FROM topics WHERE id=NEW.parent_topic_id UNION SELECT p.id,p.parent_topic_id FROM topics p JOIN ancestors a ON p.id=a.parent_topic_id) SELECT 1 FROM ancestors WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT, 'cyclic topic hierarchy'); END;

CREATE TRIGGER topics_cycle_update BEFORE UPDATE ON topics
WHEN NEW.parent_topic_id IS NOT NULL AND EXISTS(WITH RECURSIVE ancestors(id,parent_topic_id) AS (SELECT id,parent_topic_id FROM topics WHERE id=NEW.parent_topic_id UNION SELECT p.id,p.parent_topic_id FROM topics p JOIN ancestors a ON p.id=a.parent_topic_id) SELECT 1 FROM ancestors WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT, 'cyclic topic hierarchy'); END;

CREATE TRIGGER lessons_offering_insert BEFORE INSERT ON lessons
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM course_offerings o JOIN courses c ON c.id=o.course_id JOIN student_groups g ON g.id=o.group_id JOIN academic_terms t ON t.id=o.term_id WHERE o.id=NEW.course_offering_id AND o.deleted_at IS NULL AND c.deleted_at IS NULL AND g.deleted_at IS NULL AND t.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'lesson requires active offering'); END;

CREATE TRIGGER lessons_offering_update BEFORE UPDATE ON lessons
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM course_offerings o JOIN courses c ON c.id=o.course_id JOIN student_groups g ON g.id=o.group_id JOIN academic_terms t ON t.id=o.term_id WHERE o.id=NEW.course_offering_id AND o.deleted_at IS NULL AND c.deleted_at IS NULL AND g.deleted_at IS NULL AND t.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'lesson requires active offering'); END;

CREATE TRIGGER assessment_items_assessment_insert BEFORE INSERT ON assessment_items
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM assessments a JOIN course_offerings o ON o.id=a.offering_id JOIN courses c ON c.id=o.course_id JOIN student_groups g ON g.id=o.group_id JOIN academic_terms t ON t.id=o.term_id WHERE a.id=NEW.assessment_id AND a.deleted_at IS NULL AND o.deleted_at IS NULL AND c.deleted_at IS NULL AND g.deleted_at IS NULL AND t.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'item requires active assessment'); END;

CREATE TRIGGER assessment_items_assessment_update BEFORE UPDATE ON assessment_items
WHEN NEW.deleted_at IS NULL AND NOT EXISTS(SELECT 1 FROM assessments a JOIN course_offerings o ON o.id=a.offering_id JOIN courses c ON c.id=o.course_id JOIN student_groups g ON g.id=o.group_id JOIN academic_terms t ON t.id=o.term_id WHERE a.id=NEW.assessment_id AND a.deleted_at IS NULL AND o.deleted_at IS NULL AND c.deleted_at IS NULL AND g.deleted_at IS NULL AND t.deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'item requires active assessment'); END;

CREATE TRIGGER attendance_context_insert BEFORE INSERT ON attendance
WHEN NOT EXISTS(SELECT 1 FROM lessons l JOIN enrollments e ON e.offering_id=l.course_offering_id WHERE l.id=NEW.lesson_id AND e.id=NEW.enrollment_id AND (NEW.deleted_at IS NOT NULL OR (l.deleted_at IS NULL AND e.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'attendance requires enrollment in lesson offering'); END;

CREATE TRIGGER attendance_context_update BEFORE UPDATE ON attendance
WHEN NOT EXISTS(SELECT 1 FROM lessons l JOIN enrollments e ON e.offering_id=l.course_offering_id WHERE l.id=NEW.lesson_id AND e.id=NEW.enrollment_id AND (NEW.deleted_at IS NOT NULL OR (l.deleted_at IS NULL AND e.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'attendance requires enrollment in lesson offering'); END;

CREATE TRIGGER attendance_one_student_insert BEFORE INSERT ON attendance
WHEN EXISTS(SELECT 1 FROM attendance a JOIN enrollments e ON e.id=a.enrollment_id JOIN enrollments n ON n.student_id=e.student_id WHERE a.lesson_id=NEW.lesson_id AND n.id=NEW.enrollment_id AND a.id != NEW.id)
BEGIN SELECT RAISE(ABORT, 'unique attendance per lesson student'); END;

CREATE TRIGGER attendance_one_student_update BEFORE UPDATE ON attendance
WHEN EXISTS(SELECT 1 FROM attendance a JOIN enrollments e ON e.id=a.enrollment_id JOIN enrollments n ON n.student_id=e.student_id WHERE a.lesson_id=NEW.lesson_id AND n.id=NEW.enrollment_id AND a.id != NEW.id)
BEGIN SELECT RAISE(ABORT, 'unique attendance per lesson student'); END;

CREATE TRIGGER topic_skills_identity_update BEFORE UPDATE ON topic_skills
WHEN NEW.topic_id IS NOT OLD.topic_id OR NEW.skill_id IS NOT OLD.skill_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER topic_skills_context_insert BEFORE INSERT ON topic_skills
WHEN NOT EXISTS(SELECT 1 FROM topics owner JOIN skills target ON target.course_id=owner.course_id WHERE owner.id=NEW.topic_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER topic_skills_context_update BEFORE UPDATE ON topic_skills
WHEN NOT EXISTS(SELECT 1 FROM topics owner JOIN skills target ON target.course_id=owner.course_id WHERE owner.id=NEW.topic_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER lesson_topics_identity_update BEFORE UPDATE ON lesson_topics
WHEN NEW.lesson_id IS NOT OLD.lesson_id OR NEW.topic_id IS NOT OLD.topic_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER lesson_topics_context_insert BEFORE INSERT ON lesson_topics
WHEN NOT EXISTS(SELECT 1 FROM lessons owner JOIN topics target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.course_offering_id) WHERE owner.id=NEW.lesson_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER lesson_topics_context_update BEFORE UPDATE ON lesson_topics
WHEN NOT EXISTS(SELECT 1 FROM lessons owner JOIN topics target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.course_offering_id) WHERE owner.id=NEW.lesson_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_topics_identity_update BEFORE UPDATE ON assessment_topics
WHEN NEW.assessment_id IS NOT OLD.assessment_id OR NEW.topic_id IS NOT OLD.topic_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER assessment_topics_context_insert BEFORE INSERT ON assessment_topics
WHEN NOT EXISTS(SELECT 1 FROM assessments owner JOIN topics target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.offering_id) WHERE owner.id=NEW.assessment_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_topics_context_update BEFORE UPDATE ON assessment_topics
WHEN NOT EXISTS(SELECT 1 FROM assessments owner JOIN topics target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.offering_id) WHERE owner.id=NEW.assessment_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_skills_identity_update BEFORE UPDATE ON assessment_skills
WHEN NEW.assessment_id IS NOT OLD.assessment_id OR NEW.skill_id IS NOT OLD.skill_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER assessment_skills_context_insert BEFORE INSERT ON assessment_skills
WHEN NOT EXISTS(SELECT 1 FROM assessments owner JOIN skills target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.offering_id) WHERE owner.id=NEW.assessment_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_skills_context_update BEFORE UPDATE ON assessment_skills
WHEN NOT EXISTS(SELECT 1 FROM assessments owner JOIN skills target ON target.course_id=(SELECT course_id FROM course_offerings WHERE id=owner.offering_id) WHERE owner.id=NEW.assessment_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_item_topics_identity_update BEFORE UPDATE ON assessment_item_topics
WHEN NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.topic_id IS NOT OLD.topic_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER assessment_item_topics_context_insert BEFORE INSERT ON assessment_item_topics
WHEN NOT EXISTS(SELECT 1 FROM assessment_items owner JOIN topics target ON target.course_id=(SELECT o.course_id FROM assessments a JOIN course_offerings o ON o.id=a.offering_id WHERE a.id=owner.assessment_id) WHERE owner.id=NEW.assessment_item_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_item_topics_context_update BEFORE UPDATE ON assessment_item_topics
WHEN NOT EXISTS(SELECT 1 FROM assessment_items owner JOIN topics target ON target.course_id=(SELECT o.course_id FROM assessments a JOIN course_offerings o ON o.id=a.offering_id WHERE a.id=owner.assessment_id) WHERE owner.id=NEW.assessment_item_id AND target.id=NEW.topic_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_item_skills_identity_update BEFORE UPDATE ON assessment_item_skills
WHEN NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.skill_id IS NOT OLD.skill_id
BEGIN SELECT RAISE(ABORT, 'learning ownership is immutable'); END;

CREATE TRIGGER assessment_item_skills_context_insert BEFORE INSERT ON assessment_item_skills
WHEN NOT EXISTS(SELECT 1 FROM assessment_items owner JOIN skills target ON target.course_id=(SELECT o.course_id FROM assessments a JOIN course_offerings o ON o.id=a.offering_id WHERE a.id=owner.assessment_id) WHERE owner.id=NEW.assessment_item_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

CREATE TRIGGER assessment_item_skills_context_update BEFORE UPDATE ON assessment_item_skills
WHEN NOT EXISTS(SELECT 1 FROM assessment_items owner JOIN skills target ON target.course_id=(SELECT o.course_id FROM assessments a JOIN course_offerings o ON o.id=a.offering_id WHERE a.id=owner.assessment_id) WHERE owner.id=NEW.assessment_item_id AND target.id=NEW.skill_id AND (NEW.deleted_at IS NOT NULL OR (owner.deleted_at IS NULL AND target.deleted_at IS NULL)))
BEGIN SELECT RAISE(ABORT, 'link requires endpoints in same course'); END;

-- Active topic trees cannot acquire an archived parent through a raw write.
CREATE TRIGGER topics_archive_children BEFORE UPDATE OF deleted_at ON topics
WHEN NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL
 AND EXISTS(SELECT 1 FROM topics WHERE parent_topic_id=OLD.id AND deleted_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'topic archive requires archived children'); END;
