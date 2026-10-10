-- Studium local core v1. Production Alembic revision 0001_local_core SQL snapshot.
-- Do not edit v1 after release; introduce a versioned migration instead.
-- Timestamps: UTC epoch microseconds. Calendar dates: YYYY-MM-DD text.
-- PRAGMA foreign_keys = ON must run before every connection starts a transaction.

CREATE TABLE academic_terms (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  starts_on TEXT NOT NULL CHECK (length(starts_on) = 10 AND starts_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(starts_on, 1, 4) != '0000' AND date(starts_on, '+0 days') IS NOT NULL AND date(starts_on, '+0 days') = starts_on),
  ends_on TEXT NOT NULL CHECK (length(ends_on) = 10 AND ends_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(ends_on, 1, 4) != '0000' AND date(ends_on, '+0 days') IS NOT NULL AND date(ends_on, '+0 days') = ends_on),
  archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  CHECK (ends_on >= starts_on)
);

CREATE TRIGGER academic_terms_metadata_update
BEFORE UPDATE ON academic_terms
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE courses (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  short_name TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at))
);

CREATE TRIGGER courses_metadata_update
BEFORE UPDATE ON courses
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE student_groups (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  number TEXT NOT NULL CHECK (length(trim(number)) > 0),
  department TEXT NOT NULL DEFAULT '',
  faculty TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at))
);

CREATE TRIGGER student_groups_metadata_update
BEFORE UPDATE ON student_groups
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE course_offerings (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  term_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  FOREIGN KEY (term_id) REFERENCES academic_terms(id) ON DELETE RESTRICT,
  FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE RESTRICT,
  FOREIGN KEY (group_id) REFERENCES student_groups(id) ON DELETE RESTRICT
);

CREATE TRIGGER course_offerings_metadata_update
BEFORE UPDATE ON course_offerings
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE students (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
  preferred_name TEXT CHECK (preferred_name IS NULL OR length(trim(preferred_name)) > 0),
  notes TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at))
);

CREATE TRIGGER students_metadata_update
BEFORE UPDATE ON students
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE enrollments (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  student_id TEXT NOT NULL,
  offering_id TEXT NOT NULL,
  enrolled_at INTEGER NOT NULL CHECK (typeof(enrolled_at) = 'integer'),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'WITHDRAWN', 'COMPLETED')),
  ended_at INTEGER CHECK (ended_at IS NULL OR typeof(ended_at) = 'integer'),
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  CHECK ((status = 'ACTIVE' AND ended_at IS NULL) OR (status != 'ACTIVE' AND ended_at IS NOT NULL)),
  CHECK (ended_at IS NULL OR ended_at >= enrolled_at),
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE RESTRICT,
  FOREIGN KEY (offering_id) REFERENCES course_offerings(id) ON DELETE RESTRICT
);

CREATE TRIGGER enrollments_metadata_update
BEFORE UPDATE ON enrollments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE assessments (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  offering_id TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('HOMEWORK', 'TEST', 'CONTROL_WORK', 'DEFENSE', 'LAB', 'EXAM', 'OTHER')),
  number TEXT,
  title TEXT NOT NULL CHECK (length(trim(title)) > 0),
  description TEXT NOT NULL DEFAULT '',
  issued_at INTEGER NOT NULL CHECK (typeof(issued_at) = 'integer'),
  due_at INTEGER CHECK (due_at IS NULL OR typeof(due_at) = 'integer'),
  max_score REAL CHECK (max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)),
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  CHECK (due_at IS NULL OR due_at >= issued_at),
  FOREIGN KEY (offering_id) REFERENCES course_offerings(id) ON DELETE RESTRICT
);

CREATE TRIGGER assessments_metadata_update
BEFORE UPDATE ON assessments
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE student_works (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  assessment_id TEXT NOT NULL,
  student_id TEXT NOT NULL,
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  UNIQUE (student_id, assessment_id),
  FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE RESTRICT,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE RESTRICT
);

CREATE TRIGGER student_works_metadata_update
BEFORE UPDATE ON student_works
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE attempts (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  student_work_id TEXT NOT NULL,
  attempt_no INTEGER NOT NULL CHECK (typeof(attempt_no) = 'integer' AND attempt_no >= 1),
  occurred_at INTEGER NOT NULL CHECK (typeof(occurred_at) = 'integer'),
  result TEXT NOT NULL CHECK (result IN ('PRESENTED', 'NEEDS_REVISION', 'ACCEPTED', 'SCORED', 'REJECTED', 'COMMENT_ONLY')),
  comment TEXT NOT NULL DEFAULT '',
  score REAL CHECK (score IS NULL OR (score >= 0 AND score <= 1.7976931348623157e308)),
  max_score REAL CHECK (max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)),
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  UNIQUE (student_work_id, attempt_no),
  CHECK (score IS NULL OR max_score IS NULL OR score <= max_score),
  CHECK (result != 'SCORED' OR score IS NOT NULL),
  FOREIGN KEY (student_work_id) REFERENCES student_works(id) ON DELETE RESTRICT
);

CREATE TRIGGER attempts_metadata_update
BEFORE UPDATE ON attempts
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE TABLE grades (
  id TEXT NOT NULL PRIMARY KEY CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
  attempt_id TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK (kind IN ('PASS_FAIL', 'NUMERIC', 'TRADITIONAL')),
  passed INTEGER CHECK (passed IS NULL OR passed IN (0, 1)),
  score REAL CHECK (score IS NULL OR (score >= 0 AND score <= 1.7976931348623157e308)),
  max_score REAL CHECK (max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)),
  label TEXT,
  created_at INTEGER NOT NULL CHECK (typeof(created_at) = 'integer'),
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (typeof(revision) = 'integer' AND revision >= 1),
  deleted_at INTEGER CHECK (deleted_at IS NULL OR typeof(deleted_at) = 'integer'),
  CHECK (updated_at >= created_at),
  CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)),
  CHECK (score IS NULL OR max_score IS NULL OR score <= max_score),
  CHECK ((kind = 'PASS_FAIL' AND passed IS NOT NULL AND score IS NULL AND max_score IS NULL AND label IS NULL) OR (kind = 'NUMERIC' AND passed IS NULL AND score IS NOT NULL AND label IS NULL) OR (kind = 'TRADITIONAL' AND passed IS NULL AND score IS NULL AND max_score IS NULL AND label IS NOT NULL AND length(trim(label)) > 0)),
  FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE RESTRICT
);

CREATE TRIGGER grades_metadata_update
BEFORE UPDATE ON grades
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
  OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN
  SELECT RAISE(ABORT, 'metadata requires stable identity and next revision');
END;

CREATE UNIQUE INDEX enrollments_active_membership
ON enrollments (student_id, offering_id)
WHERE deleted_at IS NULL AND status = 'ACTIVE';

CREATE INDEX enrollments_offering ON enrollments (offering_id);
CREATE INDEX student_works_assessment ON student_works (assessment_id);
CREATE INDEX attempts_history ON attempts (student_work_id, attempt_no);
CREATE INDEX assessments_offering ON assessments (offering_id);

CREATE TRIGGER course_offerings_active_parents
BEFORE INSERT ON course_offerings
WHEN NOT EXISTS (SELECT 1 FROM academic_terms WHERE id = NEW.term_id AND deleted_at IS NULL)
  OR NOT EXISTS (SELECT 1 FROM courses WHERE id = NEW.course_id AND deleted_at IS NULL)
  OR NOT EXISTS (SELECT 1 FROM student_groups WHERE id = NEW.group_id AND deleted_at IS NULL)
BEGIN
  SELECT RAISE(ABORT, 'offering requires active parents');
END;

CREATE TRIGGER course_offerings_context_immutable
BEFORE UPDATE ON course_offerings
WHEN NEW.term_id IS NOT OLD.term_id OR NEW.course_id IS NOT OLD.course_id
  OR NEW.group_id IS NOT OLD.group_id
BEGIN
  SELECT RAISE(ABORT, 'offering historical context is immutable');
END;

CREATE TRIGGER enrollments_active_parents
BEFORE INSERT ON enrollments
WHEN NOT EXISTS (SELECT 1 FROM students WHERE id = NEW.student_id AND deleted_at IS NULL AND active = 1)
  OR NOT EXISTS (SELECT 1 FROM course_offerings WHERE id = NEW.offering_id AND deleted_at IS NULL)
BEGIN
  SELECT RAISE(ABORT, 'enrollment requires active student and offering');
END;

CREATE TRIGGER enrollments_identity_immutable
BEFORE UPDATE ON enrollments
WHEN NEW.student_id IS NOT OLD.student_id OR NEW.offering_id IS NOT OLD.offering_id
  OR NEW.enrolled_at IS NOT OLD.enrolled_at
BEGIN
  SELECT RAISE(ABORT, 'membership identity and start are immutable');
END;

CREATE TRIGGER enrollments_interval_insert
BEFORE INSERT ON enrollments
WHEN NEW.deleted_at IS NULL AND EXISTS (
  SELECT 1 FROM enrollments e
  WHERE e.student_id = NEW.student_id AND e.offering_id = NEW.offering_id
    AND e.deleted_at IS NULL
    AND NEW.enrolled_at < coalesce(e.ended_at, 9223372036854775807)
    AND e.enrolled_at < coalesce(NEW.ended_at, 9223372036854775807)
)
BEGIN
  SELECT RAISE(ABORT, 'membership intervals must not overlap');
END;

CREATE TRIGGER enrollments_interval_update
BEFORE UPDATE ON enrollments
WHEN NEW.deleted_at IS NULL AND EXISTS (
  SELECT 1 FROM enrollments e
  WHERE e.id != NEW.id AND e.student_id = NEW.student_id AND e.offering_id = NEW.offering_id
    AND e.deleted_at IS NULL
    AND NEW.enrolled_at < coalesce(e.ended_at, 9223372036854775807)
    AND e.enrolled_at < coalesce(NEW.ended_at, 9223372036854775807)
)
BEGIN
  SELECT RAISE(ABORT, 'membership intervals must not overlap');
END;

CREATE TRIGGER assessments_active_offering
BEFORE INSERT ON assessments
WHEN NOT EXISTS (SELECT 1 FROM course_offerings WHERE id = NEW.offering_id AND deleted_at IS NULL)
BEGIN
  SELECT RAISE(ABORT, 'assessment requires active offering');
END;

CREATE TRIGGER assessments_offering_immutable
BEFORE UPDATE ON assessments
WHEN NEW.offering_id IS NOT OLD.offering_id
BEGIN
  SELECT RAISE(ABORT, 'assessment offering is immutable');
END;

CREATE TRIGGER student_works_active_membership
BEFORE INSERT ON student_works
WHEN NOT EXISTS (
  SELECT 1 FROM assessments a
  JOIN course_offerings o ON o.id = a.offering_id
  JOIN enrollments e ON e.offering_id = o.id AND e.student_id = NEW.student_id
  JOIN students s ON s.id = e.student_id
  WHERE a.id = NEW.assessment_id AND a.deleted_at IS NULL AND o.deleted_at IS NULL
    AND e.deleted_at IS NULL AND e.status = 'ACTIVE' AND s.deleted_at IS NULL AND s.active = 1
)
BEGIN
  SELECT RAISE(ABORT, 'student work requires assessment and active membership in its offering');
END;

CREATE TRIGGER student_works_identity_immutable
BEFORE UPDATE ON student_works
WHEN NEW.student_id IS NOT OLD.student_id OR NEW.assessment_id IS NOT OLD.assessment_id
BEGIN
  SELECT RAISE(ABORT, 'student work identity is immutable');
END;

CREATE TRIGGER attempts_active_work
BEFORE INSERT ON attempts
WHEN NOT EXISTS (
  SELECT 1 FROM student_works w JOIN assessments a ON a.id = w.assessment_id
  WHERE w.id = NEW.student_work_id AND w.deleted_at IS NULL AND a.deleted_at IS NULL
)
BEGIN
  SELECT RAISE(ABORT, 'attempt requires active work and assessment');
END;

CREATE TRIGGER attempts_increasing_number
BEFORE INSERT ON attempts
WHEN NEW.attempt_no <= coalesce(
  (SELECT max(attempt_no) FROM attempts WHERE student_work_id = NEW.student_work_id), 0
)
BEGIN
  SELECT RAISE(ABORT, 'attempt number must increase including deleted history');
END;

CREATE TRIGGER attempts_facts_immutable
BEFORE UPDATE ON attempts
WHEN NEW.student_work_id IS NOT OLD.student_work_id OR NEW.attempt_no IS NOT OLD.attempt_no
  OR NEW.occurred_at IS NOT OLD.occurred_at OR NEW.result IS NOT OLD.result
  OR NEW.comment IS NOT OLD.comment OR NEW.score IS NOT OLD.score OR NEW.max_score IS NOT OLD.max_score
BEGIN
  SELECT RAISE(ABORT, 'attempt primary facts are immutable');
END;

CREATE TRIGGER grades_consistent_attempt
BEFORE INSERT ON grades
WHEN NOT EXISTS (
  SELECT 1 FROM attempts a WHERE a.id = NEW.attempt_id AND a.deleted_at IS NULL
    AND (
      (NEW.kind = 'NUMERIC' AND a.score IS NEW.score AND a.max_score IS NEW.max_score)
      OR (NEW.kind = 'PASS_FAIL' AND (
        (NEW.passed = 1 AND a.result = 'ACCEPTED')
        OR (NEW.passed = 0 AND a.result IN ('NEEDS_REVISION', 'REJECTED'))
      ))
      OR NEW.kind = 'TRADITIONAL'
    )
)
BEGIN
  SELECT RAISE(ABORT, 'grade must preserve and agree with attempt primary facts');
END;

CREATE TRIGGER grades_facts_immutable
BEFORE UPDATE ON grades
WHEN NEW.attempt_id IS NOT OLD.attempt_id OR NEW.kind IS NOT OLD.kind
  OR NEW.passed IS NOT OLD.passed OR NEW.score IS NOT OLD.score
  OR NEW.max_score IS NOT OLD.max_score OR NEW.label IS NOT OLD.label
BEGIN
  SELECT RAISE(ABORT, 'grade facts are immutable');
END;

CREATE TRIGGER student_works_preserve_history
BEFORE DELETE ON student_works
BEGIN
  SELECT RAISE(ABORT, 'student work must be soft deleted');
END;

CREATE TRIGGER attempts_preserve_history
BEFORE DELETE ON attempts
BEGIN
  SELECT RAISE(ABORT, 'attempt must be soft deleted');
END;

CREATE TRIGGER grades_preserve_history
BEFORE DELETE ON grades
BEGIN
  SELECT RAISE(ABORT, 'grade must be soft deleted');
END;
