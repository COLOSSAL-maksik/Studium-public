-- User-authorized Phase 6 sections 4-6: immutable item results, additive migration,
-- strategy A (semantic lock after first Attempt) protects old analytics meaning.
-- This adds no destructive conversion and changes none of the v1-v4 migrations.

CREATE TABLE attempt_item_results (
    id TEXT NOT NULL PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    assessment_item_id TEXT NOT NULL,
    outcome TEXT,
    score REAL,
    max_score REAL,
    teacher_comment TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    deleted_at INTEGER,
    CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
    CHECK (outcome IS NULL OR outcome IN ('CORRECT', 'PARTIAL', 'INCORRECT', 'NOT_EVALUATED')),
    CHECK (outcome IS NOT NULL OR score IS NOT NULL),
    CHECK (score IS NULL OR (typeof(score) IN ('real', 'integer') AND score >= 0 AND score <= 1.7976931348623157e308)),
    CHECK (max_score IS NULL OR (typeof(max_score) IN ('real', 'integer') AND max_score > 0 AND max_score <= 1.7976931348623157e308)),
    CHECK (score IS NULL OR max_score IS NULL OR score <= max_score),
    CHECK (typeof(created_at) = 'integer'),
    CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE RESTRICT,
    FOREIGN KEY (assessment_item_id) REFERENCES assessment_items(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX attempt_item_results_active_pair
ON attempt_item_results(attempt_id, assessment_item_id) WHERE deleted_at IS NULL;
CREATE INDEX attempt_item_results_item ON attempt_item_results(assessment_item_id);

CREATE TRIGGER attempt_item_results_metadata_update BEFORE UPDATE ON attempt_item_results
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at
OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER attempt_item_results_no_delete BEFORE DELETE ON attempt_item_results
BEGIN SELECT RAISE(ABORT, 'must be soft deleted'); END;

CREATE TRIGGER attempt_item_results_immutable BEFORE UPDATE ON attempt_item_results
WHEN NEW.attempt_id IS NOT OLD.attempt_id OR NEW.assessment_item_id IS NOT OLD.assessment_item_id
OR NEW.outcome IS NOT OLD.outcome OR NEW.score IS NOT OLD.score
OR NEW.max_score IS NOT OLD.max_score OR NEW.teacher_comment IS NOT OLD.teacher_comment
OR OLD.deleted_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'immutable item result fact'); END;

CREATE TRIGGER attempt_item_results_context_insert BEFORE INSERT ON attempt_item_results
WHEN NOT EXISTS (
    SELECT 1 FROM attempts a JOIN student_works w ON w.id=a.student_work_id
    JOIN assessments assessment ON assessment.id=w.assessment_id
    JOIN assessment_items item ON item.id=NEW.assessment_item_id AND item.assessment_id=w.assessment_id
    WHERE a.id=NEW.attempt_id AND a.deleted_at IS NULL AND w.deleted_at IS NULL
      AND assessment.deleted_at IS NULL AND item.deleted_at IS NULL
)
BEGIN SELECT RAISE(ABORT, 'item result requires active attempt and item in same assessment'); END;

-- Soft-delete retains facts and therefore does not unlock their catalogue.
CREATE VIEW analytics_locked_assessments AS
SELECT DISTINCT w.assessment_id AS id FROM student_works w JOIN attempts a ON a.student_work_id=w.id;

-- Taxonomy scope is only evidence-related nodes and their Topic ancestors.
CREATE VIEW analytics_locked_taxonomy AS
WITH RECURSIVE locked(kind,id) AS (
    SELECT 'topic', t.topic_id FROM assessment_topics t
      JOIN analytics_locked_assessments a ON a.id=t.assessment_id
    UNION
    SELECT 'topic', t.topic_id FROM assessment_item_topics t
      JOIN assessment_items i ON i.id=t.assessment_item_id
      JOIN analytics_locked_assessments a ON a.id=i.assessment_id
    UNION
    SELECT 'skill', s.skill_id FROM assessment_skills s
      JOIN analytics_locked_assessments a ON a.id=s.assessment_id
    UNION
    SELECT 'skill', s.skill_id FROM assessment_item_skills s
      JOIN assessment_items i ON i.id=s.assessment_item_id
      JOIN analytics_locked_assessments a ON a.id=i.assessment_id
    UNION
    SELECT 'topic', t.parent_topic_id FROM topics t JOIN locked l ON l.kind='topic' AND l.id=t.id
      WHERE t.parent_topic_id IS NOT NULL
)
SELECT kind,id FROM locked;

CREATE VIEW analytics_locked_topics AS SELECT id FROM analytics_locked_taxonomy WHERE kind='topic';
CREATE VIEW analytics_locked_skills AS SELECT id FROM analytics_locked_taxonomy WHERE kind='skill';

CREATE TRIGGER assessments_semantic_lock BEFORE UPDATE ON assessments
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=OLD.id)
AND (NEW.offering_id IS NOT OLD.offering_id OR NEW.type IS NOT OLD.type
OR NEW.number IS NOT OLD.number OR NEW.title IS NOT OLD.title
OR NEW.description IS NOT OLD.description OR NEW.max_score IS NOT OLD.max_score)
BEGIN SELECT RAISE(ABORT, 'immutable assessment semantics after first attempt'); END;

CREATE TRIGGER assessment_items_semantic_insert BEFORE INSERT ON assessment_items
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=NEW.assessment_id)
BEGIN SELECT RAISE(ABORT, 'immutable assessment items after first attempt'); END;

CREATE TRIGGER assessment_items_semantic_update BEFORE UPDATE ON assessment_items
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=OLD.assessment_id)
AND (NEW.assessment_id IS NOT OLD.assessment_id OR NEW.title IS NOT OLD.title
OR NEW.description IS NOT OLD.description OR NEW.max_score IS NOT OLD.max_score
OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable assessment item semantics after first attempt'); END;

CREATE TRIGGER assessment_topics_semantic_insert BEFORE INSERT ON assessment_topics
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=NEW.assessment_id)
BEGIN SELECT RAISE(ABORT, 'immutable assessment topics after first attempt'); END;

CREATE TRIGGER assessment_topics_semantic_update BEFORE UPDATE ON assessment_topics
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=OLD.assessment_id)
AND (NEW.assessment_id IS NOT OLD.assessment_id OR NEW.topic_id IS NOT OLD.topic_id OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable assessment topics after first attempt'); END;

CREATE TRIGGER assessment_skills_semantic_insert BEFORE INSERT ON assessment_skills
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=NEW.assessment_id)
BEGIN SELECT RAISE(ABORT, 'immutable assessment skills after first attempt'); END;

CREATE TRIGGER assessment_skills_semantic_update BEFORE UPDATE ON assessment_skills
WHEN EXISTS (SELECT 1 FROM analytics_locked_assessments WHERE id=OLD.assessment_id)
AND (NEW.assessment_id IS NOT OLD.assessment_id OR NEW.skill_id IS NOT OLD.skill_id OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable assessment skills after first attempt'); END;

CREATE TRIGGER assessment_item_topics_semantic_insert BEFORE INSERT ON assessment_item_topics
WHEN EXISTS (SELECT 1 FROM assessment_items i JOIN analytics_locked_assessments a ON a.id=i.assessment_id WHERE i.id=NEW.assessment_item_id)
BEGIN SELECT RAISE(ABORT, 'immutable item topics after first attempt'); END;

CREATE TRIGGER assessment_item_topics_semantic_update BEFORE UPDATE ON assessment_item_topics
WHEN EXISTS (SELECT 1 FROM assessment_items i JOIN analytics_locked_assessments a ON a.id=i.assessment_id WHERE i.id=OLD.assessment_item_id)
AND (NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.topic_id IS NOT OLD.topic_id OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable item topics after first attempt'); END;

CREATE TRIGGER assessment_item_skills_semantic_insert BEFORE INSERT ON assessment_item_skills
WHEN EXISTS (SELECT 1 FROM assessment_items i JOIN analytics_locked_assessments a ON a.id=i.assessment_id WHERE i.id=NEW.assessment_item_id)
BEGIN SELECT RAISE(ABORT, 'immutable item skills after first attempt'); END;

CREATE TRIGGER assessment_item_skills_semantic_update BEFORE UPDATE ON assessment_item_skills
WHEN EXISTS (SELECT 1 FROM assessment_items i JOIN analytics_locked_assessments a ON a.id=i.assessment_id WHERE i.id=OLD.assessment_item_id)
AND (NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.skill_id IS NOT OLD.skill_id OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable item skills after first attempt'); END;

CREATE TRIGGER topics_semantic_update BEFORE UPDATE ON topics
WHEN EXISTS (SELECT 1 FROM analytics_locked_topics WHERE id=OLD.id)
AND (NEW.course_id IS NOT OLD.course_id OR NEW.parent_topic_id IS NOT OLD.parent_topic_id
OR NEW.title IS NOT OLD.title OR NEW.description IS NOT OLD.description OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable historical topic semantics'); END;

CREATE TRIGGER skills_semantic_update BEFORE UPDATE ON skills
WHEN EXISTS (SELECT 1 FROM analytics_locked_skills WHERE id=OLD.id)
AND (NEW.course_id IS NOT OLD.course_id OR NEW.title IS NOT OLD.title
OR NEW.description IS NOT OLD.description OR NEW.deleted_at IS NOT OLD.deleted_at)
BEGIN SELECT RAISE(ABORT, 'immutable historical skill semantics'); END;
