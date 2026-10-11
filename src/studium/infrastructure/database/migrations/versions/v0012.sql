-- Preserve recorded frozen classification endpoints. Existing guards remain intact.

CREATE TRIGGER topics_frozen_content_archive BEFORE UPDATE OF deleted_at ON topics
WHEN OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL AND (
  EXISTS(SELECT 1 FROM version_references WHERE topic_id=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.topic_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.definition_topics') t WHERE json_extract(t.value,'$.topic_id')=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.problem_snapshots') p,json_each(p.value,'$.topic_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.topic_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.definition_topics') t WHERE json_extract(t.value,'$.topic_id')=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.problem_snapshots') p,json_each(p.value,'$.topic_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM student_problem_assignments s,json_each(s.teacher_snapshot_json,'$.topic_ids') t WHERE t.value=OLD.id)
)
BEGIN SELECT RAISE(ABORT, 'frozen classification dependency'); END;

CREATE TRIGGER skills_frozen_content_archive BEFORE UPDATE OF deleted_at ON skills
WHEN OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL AND (
  EXISTS(SELECT 1 FROM version_references WHERE skill_id=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.skill_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.definition_skills') t WHERE json_extract(t.value,'$.skill_id')=OLD.id)
  OR EXISTS(SELECT 1 FROM program_versions s,json_each(s.content_json,'$.problem_snapshots') p,json_each(p.value,'$.skill_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.skill_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.definition_skills') t WHERE json_extract(t.value,'$.skill_id')=OLD.id)
  OR EXISTS(SELECT 1 FROM plan_content_sources s,json_each(s.snapshot_json,'$.problem_snapshots') p,json_each(p.value,'$.skill_ids') t WHERE t.value=OLD.id)
  OR EXISTS(SELECT 1 FROM student_problem_assignments s,json_each(s.teacher_snapshot_json,'$.skill_ids') t WHERE t.value=OLD.id)
)
BEGIN SELECT RAISE(ABORT, 'frozen classification dependency'); END;
