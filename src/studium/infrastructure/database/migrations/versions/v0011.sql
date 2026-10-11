
CREATE TABLE plan_content_sources (
	id TEXT NOT NULL,
	semester_plan_id TEXT NOT NULL,
	plan_module_id TEXT,
	planned_work_id TEXT,
	program_version_id TEXT,
	course_semester INTEGER,
	snapshot_json TEXT NOT NULL,
	provenance TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	CHECK (course_semester IS NULL OR typeof(course_semester)='integer'),
	CHECK (json_valid(snapshot_json) AND json_type(snapshot_json)='object'),
	UNIQUE (plan_module_id),
	UNIQUE (planned_work_id),
	CHECK ((plan_module_id IS NOT NULL)+(planned_work_id IS NOT NULL)=1),
	CHECK (course_semester IS NULL OR course_semester>=1),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(semester_plan_id) REFERENCES semester_plans (id) ON DELETE RESTRICT,
	FOREIGN KEY(plan_module_id) REFERENCES plan_modules (id) ON DELETE RESTRICT,
	FOREIGN KEY(planned_work_id) REFERENCES planned_works (id) ON DELETE RESTRICT,
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT
)

;

CREATE INDEX plan_content_sources_plan_module_id_qa_idx ON plan_content_sources (plan_module_id);

CREATE INDEX plan_content_sources_planned_work_id_qa_idx ON plan_content_sources (planned_work_id);

CREATE INDEX plan_content_sources_program_version_id_qa_idx ON plan_content_sources (program_version_id);

CREATE INDEX plan_content_sources_semester_plan_id_qa_idx ON plan_content_sources (semester_plan_id);

CREATE TRIGGER plan_content_sources_immutable BEFORE UPDATE ON plan_content_sources BEGIN SELECT RAISE(ABORT,'immutable content source'); END;

CREATE TRIGGER plan_content_sources_no_delete BEFORE DELETE ON plan_content_sources BEGIN SELECT RAISE(ABORT,'immutable content source'); END;


CREATE TABLE late_work_authorizations (
	id TEXT NOT NULL,
	student_work_id TEXT NOT NULL,
	enrollment_id TEXT NOT NULL,
	student_id TEXT NOT NULL,
	assessment_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL,
	revision INTEGER DEFAULT 1 NOT NULL,
	deleted_at INTEGER,
	PRIMARY KEY (id),
	UNIQUE (student_work_id),
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'),
	CHECK (typeof(created_at) = 'integer'),
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at),
	CHECK (typeof(revision) = 'integer' AND revision >= 1),
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)),
	FOREIGN KEY(student_work_id) REFERENCES student_works (id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE RESTRICT,
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT,
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
)

;

CREATE INDEX late_work_authorizations_assessment_id_qa_idx ON late_work_authorizations (assessment_id);

CREATE INDEX late_work_authorizations_enrollment_id_qa_idx ON late_work_authorizations (enrollment_id);

CREATE INDEX late_work_authorizations_student_id_qa_idx ON late_work_authorizations (student_id);

CREATE INDEX late_work_authorizations_student_work_id_qa_idx ON late_work_authorizations (student_work_id);

CREATE TRIGGER late_work_authorizations_immutable BEFORE UPDATE ON late_work_authorizations BEGIN SELECT RAISE(ABORT,'immutable content source'); END;

CREATE TRIGGER late_work_authorizations_no_delete BEFORE DELETE ON late_work_authorizations BEGIN SELECT RAISE(ABORT,'immutable content source'); END;

CREATE TRIGGER plan_content_sources_scope BEFORE INSERT ON plan_content_sources
WHEN NOT EXISTS (
 SELECT 1 FROM semester_plans p JOIN course_offerings o ON o.id=p.offering_id
 WHERE p.id=NEW.semester_plan_id
 AND (NEW.plan_module_id IS NULL OR EXISTS (SELECT 1 FROM plan_modules m WHERE m.id=NEW.plan_module_id AND m.semester_plan_id=p.id))
 AND (NEW.planned_work_id IS NULL OR EXISTS (SELECT 1 FROM planned_works w WHERE w.id=NEW.planned_work_id AND w.semester_plan_id=p.id))
 AND (NEW.program_version_id IS NULL OR EXISTS (SELECT 1 FROM program_versions v JOIN course_programs c ON c.id=v.course_program_id WHERE v.id=NEW.program_version_id AND c.course_id=o.course_id))
)
BEGIN SELECT RAISE(ABORT,'content source context mismatch'); END;

CREATE TRIGGER late_work_authorizations_scope BEFORE INSERT ON late_work_authorizations
WHEN NOT EXISTS (
 SELECT 1 FROM enrollments en JOIN assessments a ON a.offering_id=en.offering_id
 JOIN course_offerings o ON o.id=a.offering_id JOIN students s ON s.id=en.student_id
 JOIN academic_terms t ON t.id=o.term_id JOIN courses c ON c.id=o.course_id
 JOIN student_groups g ON g.id=o.group_id
 WHERE en.id=NEW.enrollment_id AND en.student_id=NEW.student_id AND a.id=NEW.assessment_id
 AND en.deleted_at IS NULL AND en.status IN ('WITHDRAWN','COMPLETED') AND en.ended_at IS NOT NULL
 AND a.deleted_at IS NULL AND o.deleted_at IS NULL AND s.deleted_at IS NULL AND s.active=1
 AND t.deleted_at IS NULL AND c.deleted_at IS NULL AND g.deleted_at IS NULL
 AND (a.issued_at IS NOT NULL AND a.issued_at<=en.ended_at OR EXISTS (
   SELECT 1 FROM issued_works i WHERE i.assessment_id=a.id AND i.deleted_at IS NULL
   AND (i.actual_issued_at IS NULL OR i.actual_issued_at<=en.ended_at)))
)
BEGIN SELECT RAISE(ABORT,'late work requires original issued context and historical membership'); END;

DROP TRIGGER student_works_active_membership;
CREATE TRIGGER student_works_active_membership BEFORE INSERT ON student_works
WHEN NOT EXISTS (
 SELECT 1 FROM assessments a JOIN course_offerings o ON o.id=a.offering_id
 JOIN enrollments en ON en.offering_id=o.id AND en.student_id=NEW.student_id
 JOIN students s ON s.id=en.student_id
 WHERE a.id=NEW.assessment_id AND a.deleted_at IS NULL AND o.deleted_at IS NULL
 AND en.deleted_at IS NULL AND s.deleted_at IS NULL AND s.active=1
 AND (en.status='ACTIVE' OR EXISTS (
   SELECT 1 FROM late_work_authorizations l WHERE l.student_work_id=NEW.id
   AND l.student_id=NEW.student_id AND l.assessment_id=a.id AND l.enrollment_id=en.id
   AND l.deleted_at IS NULL AND en.status IN ('WITHDRAWN','COMPLETED') AND en.ended_at IS NOT NULL))
)
BEGIN SELECT RAISE(ABORT,'student work requires active membership or explicit original late submission'); END;

CREATE TRIGGER file_assets_saved_content_guard BEFORE UPDATE ON file_assets
WHEN NEW.deleted_at IS NOT OLD.deleted_at AND NEW.deleted_at IS NOT NULL AND (
 EXISTS (SELECT 1 FROM version_references v WHERE v.file_asset_id=OLD.id) OR
 EXISTS (SELECT 1 FROM plan_content_sources s,json_tree(s.snapshot_json) j WHERE j.key='file_asset_id' AND j.value=OLD.id)
)
BEGIN SELECT RAISE(ABORT,'file asset retained by frozen course content'); END;
