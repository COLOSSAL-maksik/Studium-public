CREATE TABLE directions (
	id TEXT NOT NULL, 
	code TEXT NOT NULL, 
	normalized_key TEXT NOT NULL, 
	name TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (normalized_key), 
	CHECK (length(trim(code))>0), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at))
);


CREATE TRIGGER directions_qa_revision BEFORE UPDATE ON directions
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER directions_qa_no_delete BEFORE DELETE ON directions BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TABLE course_programs (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title))>0), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
);


CREATE TRIGGER course_programs_qa_revision BEFORE UPDATE ON course_programs
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER course_programs_qa_no_delete BEFORE DELETE ON course_programs BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE INDEX course_programs_course_id_qa_idx ON course_programs(course_id);

CREATE TABLE program_versions (
	id TEXT NOT NULL, 
	course_program_id TEXT NOT NULL, 
	version_no INTEGER NOT NULL, 
	content_json TEXT NOT NULL, 
	label TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(version_no)='integer'), 
	CHECK (json_valid(content_json) AND json_type(content_json)='object'), 
	UNIQUE (course_program_id, version_no), 
	CHECK (version_no>=1), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_program_id) REFERENCES course_programs (id) ON DELETE RESTRICT
);


CREATE TRIGGER program_versions_qa_revision BEFORE UPDATE ON program_versions
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER program_versions_qa_no_delete BEFORE DELETE ON program_versions BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER program_versions_qa_immutable BEFORE UPDATE ON program_versions WHEN NEW.course_program_id IS NOT OLD.course_program_id OR NEW.version_no IS NOT OLD.version_no OR NEW.content_json IS NOT OLD.content_json OR NEW.label IS NOT OLD.label BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX program_versions_course_program_id_qa_idx ON program_versions(course_program_id);

CREATE TABLE program_directions (
	id TEXT NOT NULL, 
	program_version_id TEXT NOT NULL, 
	direction_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (program_version_id, direction_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(direction_id) REFERENCES directions (id) ON DELETE RESTRICT
);


CREATE TRIGGER program_directions_qa_revision BEFORE UPDATE ON program_directions
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER program_directions_qa_no_delete BEFORE DELETE ON program_directions BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER program_directions_qa_immutable BEFORE UPDATE ON program_directions WHEN NEW.program_version_id IS NOT OLD.program_version_id OR NEW.direction_id IS NOT OLD.direction_id BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX program_directions_program_version_id_qa_idx ON program_directions(program_version_id);

CREATE INDEX program_directions_direction_id_qa_idx ON program_directions(direction_id);

CREATE TABLE legacy_program_maps (
	id TEXT NOT NULL, 
	legacy_program_id TEXT NOT NULL, 
	program_version_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (legacy_program_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(legacy_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT
);


CREATE TRIGGER legacy_program_maps_qa_revision BEFORE UPDATE ON legacy_program_maps
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER legacy_program_maps_qa_no_delete BEFORE DELETE ON legacy_program_maps BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER legacy_program_maps_qa_immutable BEFORE UPDATE ON legacy_program_maps WHEN NEW.legacy_program_id IS NOT OLD.legacy_program_id OR NEW.program_version_id IS NOT OLD.program_version_id BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX legacy_program_maps_legacy_program_id_qa_idx ON legacy_program_maps(legacy_program_id);

CREATE INDEX legacy_program_maps_program_version_id_qa_idx ON legacy_program_maps(program_version_id);

CREATE TABLE semester_plans (
	id TEXT NOT NULL, 
	offering_id TEXT NOT NULL, 
	program_version_id TEXT, 
	first_week_start TEXT NOT NULL, 
	weeks INTEGER NOT NULL, 
	course_semester INTEGER, 
	week_utc_offset_minutes INTEGER NOT NULL, 
	configured INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(weeks)='integer'), 
	CHECK (course_semester IS NULL OR typeof(course_semester)='integer'), 
	CHECK (typeof(week_utc_offset_minutes)='integer'), 
	CHECK (typeof(configured)='integer'), 
	UNIQUE (offering_id), 
	CHECK (weeks BETWEEN 1 AND 104), 
	CHECK (course_semester IS NULL OR course_semester>=1), 
	CHECK (configured IN (0,1)), 
	CHECK (week_utc_offset_minutes BETWEEN -840 AND 840), 
	CHECK (date(first_week_start,'+0 days')=first_week_start AND date(first_week_start,'+0 days') IS NOT NULL), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT, 
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT
);


CREATE TRIGGER semester_plans_qa_revision BEFORE UPDATE ON semester_plans
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER semester_plans_qa_no_delete BEFORE DELETE ON semester_plans BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE INDEX semester_plans_offering_id_qa_idx ON semester_plans(offering_id);

CREATE INDEX semester_plans_program_version_id_qa_idx ON semester_plans(program_version_id);

CREATE TABLE plan_modules (
	id TEXT NOT NULL, 
	semester_plan_id TEXT NOT NULL, 
	source_module_id TEXT, 
	title TEXT NOT NULL, 
	start_week INTEGER NOT NULL, 
	end_week INTEGER NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(start_week)='integer'), 
	CHECK (typeof(end_week)='integer'), 
	CHECK (typeof(sort_order)='integer'), 
	UNIQUE (semester_plan_id, source_module_id), 
	CHECK (start_week>=1 AND end_week>=start_week AND sort_order>=0), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(semester_plan_id) REFERENCES semester_plans (id) ON DELETE RESTRICT, 
	FOREIGN KEY(source_module_id) REFERENCES program_modules (id) ON DELETE RESTRICT
);


CREATE TRIGGER plan_modules_qa_revision BEFORE UPDATE ON plan_modules
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER plan_modules_qa_no_delete BEFORE DELETE ON plan_modules BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE INDEX plan_modules_semester_plan_id_qa_idx ON plan_modules(semester_plan_id);

CREATE INDEX plan_modules_source_module_id_qa_idx ON plan_modules(source_module_id);

CREATE TABLE planned_works (
	id TEXT NOT NULL, 
	semester_plan_id TEXT NOT NULL, 
	module_id TEXT, 
	definition_id TEXT, 
	source_work_id TEXT, 
	title TEXT NOT NULL, 
	type TEXT NOT NULL, 
	number TEXT NOT NULL, 
	issue_date TEXT, 
	due_date TEXT, 
	exact_due_at INTEGER, 
	deadline_kind TEXT NOT NULL, 
	due_week INTEGER, 
	min_cents INTEGER, 
	max_cents INTEGER, 
	sort_order INTEGER NOT NULL, 
	cancelled INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (exact_due_at IS NULL OR typeof(exact_due_at)='integer'), 
	CHECK (due_week IS NULL OR typeof(due_week)='integer'), 
	CHECK (deadline_kind IN ('NONE','DATE_EXCLUSIVE','EXACT_INCLUSIVE','WEEK_ONLY')), 
	CHECK (due_week IS NULL OR due_week>=1), 
	CHECK (min_cents IS NULL OR typeof(min_cents)='integer'), 
	CHECK (min_cents IS NULL OR min_cents >= 0), 
	CHECK (max_cents IS NULL OR typeof(max_cents)='integer'), 
	CHECK (max_cents IS NULL OR max_cents >= 0), 
	CHECK (typeof(sort_order)='integer'), 
	CHECK (typeof(cancelled)='integer'), 
	UNIQUE (semester_plan_id, source_work_id), 
	CHECK (type IN ('HOMEWORK','TEST','CONTROL_WORK','DEFENSE','LAB','EXAM','OTHER')), 
	CHECK (cancelled IN (0,1) AND sort_order>=0), 
	CHECK ((min_cents IS NULL AND max_cents IS NULL) OR (min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=max_cents AND max_cents>0)), 
	CHECK (issue_date IS NULL OR (date(issue_date,'+0 days')=issue_date AND date(issue_date,'+0 days') IS NOT NULL)), 
	CHECK (due_date IS NULL OR (date(due_date,'+0 days')=due_date AND date(due_date,'+0 days') IS NOT NULL)), 
	CHECK (issue_date IS NULL OR due_date IS NULL OR issue_date<=due_date), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(semester_plan_id) REFERENCES semester_plans (id) ON DELETE RESTRICT, 
	FOREIGN KEY(module_id) REFERENCES plan_modules (id) ON DELETE RESTRICT, 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(source_work_id) REFERENCES program_works (id) ON DELETE RESTRICT
);


CREATE TRIGGER planned_works_qa_revision BEFORE UPDATE ON planned_works
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER planned_works_qa_no_delete BEFORE DELETE ON planned_works BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE INDEX planned_works_semester_plan_id_qa_idx ON planned_works(semester_plan_id);

CREATE INDEX planned_works_module_id_qa_idx ON planned_works(module_id);

CREATE INDEX planned_works_definition_id_qa_idx ON planned_works(definition_id);

CREATE INDEX planned_works_source_work_id_qa_idx ON planned_works(source_work_id);

CREATE TABLE plan_history (
	id TEXT NOT NULL, 
	semester_plan_id TEXT NOT NULL, 
	plan_revision INTEGER NOT NULL, 
	snapshot_json TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	provenance TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(plan_revision)='integer'), 
	CHECK (json_valid(snapshot_json) AND json_type(snapshot_json)='object'), 
	UNIQUE (semester_plan_id, plan_revision), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(semester_plan_id) REFERENCES semester_plans (id) ON DELETE RESTRICT
);


CREATE TRIGGER plan_history_qa_revision BEFORE UPDATE ON plan_history
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER plan_history_qa_no_delete BEFORE DELETE ON plan_history BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER plan_history_qa_immutable BEFORE UPDATE ON plan_history WHEN NEW.semester_plan_id IS NOT OLD.semester_plan_id OR NEW.plan_revision IS NOT OLD.plan_revision OR NEW.snapshot_json IS NOT OLD.snapshot_json OR NEW.reason IS NOT OLD.reason OR NEW.provenance IS NOT OLD.provenance BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX plan_history_semester_plan_id_qa_idx ON plan_history(semester_plan_id);

CREATE TABLE issued_works (
	id TEXT NOT NULL, 
	planned_work_id TEXT NOT NULL, 
	assessment_id TEXT NOT NULL, 
	actual_issued_at INTEGER, 
	provenance TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (actual_issued_at IS NULL OR typeof(actual_issued_at)='integer'), 
	UNIQUE (planned_work_id), 
	UNIQUE (assessment_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(planned_work_id) REFERENCES planned_works (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
);


CREATE TRIGGER issued_works_qa_revision BEFORE UPDATE ON issued_works
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER issued_works_qa_no_delete BEFORE DELETE ON issued_works BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER issued_works_qa_immutable BEFORE UPDATE ON issued_works WHEN NEW.planned_work_id IS NOT OLD.planned_work_id OR NEW.assessment_id IS NOT OLD.assessment_id OR NEW.actual_issued_at IS NOT OLD.actual_issued_at OR NEW.provenance IS NOT OLD.provenance BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX issued_works_planned_work_id_qa_idx ON issued_works(planned_work_id);

CREATE INDEX issued_works_assessment_id_qa_idx ON issued_works(assessment_id);

CREATE TABLE scoring_rules (
	id TEXT NOT NULL, 
	assessment_id TEXT NOT NULL, 
	sequence INTEGER NOT NULL, 
	min_cents INTEGER, 
	max_cents INTEGER, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sequence)='integer'), 
	CHECK (min_cents IS NULL OR typeof(min_cents)='integer'), 
	CHECK (min_cents IS NULL OR min_cents >= 0), 
	CHECK (max_cents IS NULL OR typeof(max_cents)='integer'), 
	CHECK (max_cents IS NULL OR max_cents >= 0), 
	UNIQUE (assessment_id, sequence), 
	CHECK (min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=max_cents AND max_cents>0 AND sequence>=1), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT
);


CREATE TRIGGER scoring_rules_qa_revision BEFORE UPDATE ON scoring_rules
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER scoring_rules_qa_no_delete BEFORE DELETE ON scoring_rules BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER scoring_rules_qa_immutable BEFORE UPDATE ON scoring_rules WHEN NEW.assessment_id IS NOT OLD.assessment_id OR NEW.sequence IS NOT OLD.sequence OR NEW.min_cents IS NOT OLD.min_cents OR NEW.max_cents IS NOT OLD.max_cents BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX scoring_rules_assessment_id_qa_idx ON scoring_rules(assessment_id);

CREATE TABLE submissions (
	id TEXT NOT NULL, 
	attempt_id TEXT NOT NULL, 
	rule_id TEXT, 
	received_at INTEGER NOT NULL, 
	utc_offset_minutes INTEGER NOT NULL, 
	provenance TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(received_at)='integer'), 
	CHECK (typeof(utc_offset_minutes)='integer'), 
	UNIQUE (attempt_id), 
	CHECK (utc_offset_minutes BETWEEN -840 AND 840), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE RESTRICT, 
	FOREIGN KEY(rule_id) REFERENCES scoring_rules (id) ON DELETE RESTRICT
);


CREATE TRIGGER submissions_qa_revision BEFORE UPDATE ON submissions
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER submissions_qa_no_delete BEFORE DELETE ON submissions BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER submissions_qa_immutable BEFORE UPDATE ON submissions WHEN NEW.attempt_id IS NOT OLD.attempt_id OR NEW.rule_id IS NOT OLD.rule_id OR NEW.received_at IS NOT OLD.received_at OR NEW.utc_offset_minutes IS NOT OLD.utc_offset_minutes OR NEW.provenance IS NOT OLD.provenance BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX submissions_attempt_id_qa_idx ON submissions(attempt_id);

CREATE INDEX submissions_rule_id_qa_idx ON submissions(rule_id);

CREATE TABLE reviews (
	id TEXT NOT NULL, 
	submission_id TEXT NOT NULL, 
	rule_id TEXT, 
	review_seq INTEGER NOT NULL, 
	result TEXT NOT NULL, 
	reviewed_at INTEGER NOT NULL, 
	score_cents INTEGER, 
	min_cents INTEGER, 
	max_cents INTEGER, 
	comment TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(review_seq)='integer'), 
	CHECK (typeof(reviewed_at)='integer'), 
	CHECK (score_cents IS NULL OR typeof(score_cents)='integer'), 
	CHECK (score_cents IS NULL OR score_cents >= 0), 
	CHECK (min_cents IS NULL OR typeof(min_cents)='integer'), 
	CHECK (min_cents IS NULL OR min_cents >= 0), 
	CHECK (max_cents IS NULL OR typeof(max_cents)='integer'), 
	CHECK (max_cents IS NULL OR max_cents >= 0), 
	UNIQUE (submission_id, review_seq), 
	CHECK (review_seq>=1), 
	CHECK (result IN ('NEEDS_REVISION','ACCEPTED','SCORED','REJECTED','COMMENT_ONLY')), 
	CHECK (result!='SCORED' OR score_cents IS NOT NULL), 
	CHECK (score_cents IS NULL OR (result IN ('SCORED','ACCEPTED') AND rule_id IS NOT NULL AND min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=score_cents AND score_cents<=max_cents)), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(submission_id) REFERENCES submissions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(rule_id) REFERENCES scoring_rules (id) ON DELETE RESTRICT
);


CREATE TRIGGER reviews_qa_revision BEFORE UPDATE ON reviews
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER reviews_qa_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER reviews_qa_immutable BEFORE UPDATE ON reviews WHEN NEW.submission_id IS NOT OLD.submission_id OR NEW.rule_id IS NOT OLD.rule_id OR NEW.review_seq IS NOT OLD.review_seq OR NEW.result IS NOT OLD.result OR NEW.reviewed_at IS NOT OLD.reviewed_at OR NEW.score_cents IS NOT OLD.score_cents OR NEW.min_cents IS NOT OLD.min_cents OR NEW.max_cents IS NOT OLD.max_cents OR NEW.comment IS NOT OLD.comment BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX reviews_submission_id_qa_idx ON reviews(submission_id);

CREATE INDEX reviews_rule_id_qa_idx ON reviews(rule_id);

CREATE TABLE review_grades (
	id TEXT NOT NULL, 
	review_id TEXT NOT NULL, 
	kind TEXT NOT NULL, 
	score_cents INTEGER, 
	max_cents INTEGER, 
	passed INTEGER, 
	label TEXT, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (score_cents IS NULL OR typeof(score_cents)='integer'), 
	CHECK (score_cents IS NULL OR score_cents >= 0), 
	CHECK (max_cents IS NULL OR typeof(max_cents)='integer'), 
	CHECK (max_cents IS NULL OR max_cents >= 0), 
	CHECK (passed IS NULL OR typeof(passed)='integer'), 
	UNIQUE (review_id), 
	CHECK ((kind='NUMERIC' AND score_cents IS NOT NULL AND max_cents IS NOT NULL AND passed IS NULL AND label IS NULL) OR (kind='PASS_FAIL' AND passed IS NOT NULL AND passed IN (0,1) AND score_cents IS NULL AND max_cents IS NULL AND label IS NULL) OR (kind='TRADITIONAL' AND label IS NOT NULL AND length(trim(label))>0 AND passed IS NULL AND score_cents IS NULL AND max_cents IS NULL)), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(review_id) REFERENCES reviews (id) ON DELETE RESTRICT
);


CREATE TRIGGER review_grades_qa_revision BEFORE UPDATE ON review_grades
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER review_grades_qa_no_delete BEFORE DELETE ON review_grades BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER review_grades_qa_immutable BEFORE UPDATE ON review_grades WHEN NEW.review_id IS NOT OLD.review_id OR NEW.kind IS NOT OLD.kind OR NEW.score_cents IS NOT OLD.score_cents OR NEW.max_cents IS NOT OLD.max_cents OR NEW.passed IS NOT OLD.passed OR NEW.label IS NOT OLD.label BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX review_grades_review_id_qa_idx ON review_grades(review_id);

CREATE TABLE review_files (
	id TEXT NOT NULL, 
	review_id TEXT NOT NULL, 
	file_asset_id TEXT NOT NULL, 
	caption TEXT NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order)='integer'), 
	UNIQUE (review_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(review_id) REFERENCES reviews (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
);


CREATE TRIGGER review_files_qa_revision BEFORE UPDATE ON review_files
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER review_files_qa_no_delete BEFORE DELETE ON review_files BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER review_files_qa_immutable BEFORE UPDATE ON review_files WHEN NEW.review_id IS NOT OLD.review_id OR NEW.file_asset_id IS NOT OLD.file_asset_id OR NEW.caption IS NOT OLD.caption OR NEW.sort_order IS NOT OLD.sort_order BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX review_files_review_id_qa_idx ON review_files(review_id);

CREATE INDEX review_files_file_asset_id_qa_idx ON review_files(file_asset_id);

CREATE TABLE review_returns (
	id TEXT NOT NULL, 
	review_id TEXT NOT NULL, 
	returned_at INTEGER NOT NULL, 
	comment TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(returned_at)='integer'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(review_id) REFERENCES reviews (id) ON DELETE RESTRICT
);


CREATE TRIGGER review_returns_qa_revision BEFORE UPDATE ON review_returns
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER review_returns_qa_no_delete BEFORE DELETE ON review_returns BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER review_returns_qa_immutable BEFORE UPDATE ON review_returns WHEN NEW.review_id IS NOT OLD.review_id OR NEW.returned_at IS NOT OLD.returned_at OR NEW.comment IS NOT OLD.comment BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX review_returns_review_id_qa_idx ON review_returns(review_id);

CREATE TABLE required_work_sets (
	id TEXT NOT NULL, 
	module_id TEXT NOT NULL, 
	student_id TEXT NOT NULL, 
	sequence INTEGER NOT NULL, 
	reason TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sequence)='integer'), 
	UNIQUE (module_id, student_id, sequence), 
	CHECK (sequence>=1), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(module_id) REFERENCES plan_modules (id) ON DELETE RESTRICT, 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT
);


CREATE TRIGGER required_work_sets_qa_revision BEFORE UPDATE ON required_work_sets
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER required_work_sets_qa_no_delete BEFORE DELETE ON required_work_sets BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER required_work_sets_qa_immutable BEFORE UPDATE ON required_work_sets WHEN NEW.module_id IS NOT OLD.module_id OR NEW.student_id IS NOT OLD.student_id OR NEW.sequence IS NOT OLD.sequence OR NEW.reason IS NOT OLD.reason BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX required_work_sets_module_id_qa_idx ON required_work_sets(module_id);

CREATE INDEX required_work_sets_student_id_qa_idx ON required_work_sets(student_id);

CREATE TABLE required_work_bindings (
	id TEXT NOT NULL, 
	required_set_id TEXT NOT NULL, 
	student_work_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (required_set_id, student_work_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(required_set_id) REFERENCES required_work_sets (id) ON DELETE RESTRICT, 
	FOREIGN KEY(student_work_id) REFERENCES student_works (id) ON DELETE RESTRICT
);


CREATE TRIGGER required_work_bindings_qa_revision BEFORE UPDATE ON required_work_bindings
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER required_work_bindings_qa_no_delete BEFORE DELETE ON required_work_bindings BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER required_work_bindings_qa_immutable BEFORE UPDATE ON required_work_bindings WHEN NEW.required_set_id IS NOT OLD.required_set_id OR NEW.student_work_id IS NOT OLD.student_work_id BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX required_work_bindings_required_set_id_qa_idx ON required_work_bindings(required_set_id);

CREATE INDEX required_work_bindings_student_work_id_qa_idx ON required_work_bindings(student_work_id);

CREATE TABLE answer_templates (
	id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	schema_json TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (json_valid(schema_json) AND json_type(schema_json)='array'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at))
);


CREATE TRIGGER answer_templates_qa_revision BEFORE UPDATE ON answer_templates
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER answer_templates_qa_no_delete BEFORE DELETE ON answer_templates BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TABLE debt_restorations (
	id TEXT NOT NULL, 
	student_work_id TEXT NOT NULL, 
	before_json TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (json_valid(before_json) AND json_type(before_json)='object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(student_work_id) REFERENCES student_works (id) ON DELETE RESTRICT
);


CREATE TRIGGER debt_restorations_qa_revision BEFORE UPDATE ON debt_restorations
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER debt_restorations_qa_no_delete BEFORE DELETE ON debt_restorations BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER debt_restorations_qa_immutable BEFORE UPDATE ON debt_restorations WHEN NEW.student_work_id IS NOT OLD.student_work_id OR NEW.before_json IS NOT OLD.before_json OR NEW.reason IS NOT OLD.reason BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX debt_restorations_student_work_id_qa_idx ON debt_restorations(student_work_id);

CREATE TABLE version_references (
	id TEXT NOT NULL, 
	program_version_id TEXT NOT NULL, 
	topic_id TEXT, 
	skill_id TEXT, 
	definition_id TEXT, 
	seminar_material_id TEXT, 
	literature_item_id TEXT, 
	file_asset_id TEXT, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK ((topic_id IS NOT NULL)+(skill_id IS NOT NULL)+(definition_id IS NOT NULL)+(seminar_material_id IS NOT NULL)+(literature_item_id IS NOT NULL)+(file_asset_id IS NOT NULL)=1), 
	UNIQUE (program_version_id, topic_id), 
	UNIQUE (program_version_id, skill_id), 
	UNIQUE (program_version_id, definition_id), 
	UNIQUE (program_version_id, seminar_material_id), 
	UNIQUE (program_version_id, literature_item_id), 
	UNIQUE (program_version_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(program_version_id) REFERENCES program_versions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT, 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(seminar_material_id) REFERENCES seminar_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(literature_item_id) REFERENCES literature_items (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
);


CREATE TRIGGER version_references_qa_revision BEFORE UPDATE ON version_references
WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at
BEGIN SELECT RAISE(ABORT,'invalid revision or identity'); END;

CREATE TRIGGER version_references_qa_no_delete BEFORE DELETE ON version_references BEGIN SELECT RAISE(ABORT,'must be soft deleted'); END;

CREATE TRIGGER version_references_qa_immutable BEFORE UPDATE ON version_references WHEN NEW.program_version_id IS NOT OLD.program_version_id OR NEW.topic_id IS NOT OLD.topic_id OR NEW.skill_id IS NOT OLD.skill_id OR NEW.definition_id IS NOT OLD.definition_id OR NEW.seminar_material_id IS NOT OLD.seminar_material_id OR NEW.literature_item_id IS NOT OLD.literature_item_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT,'immutable fact'); END;

CREATE INDEX version_references_program_version_id_qa_idx ON version_references(program_version_id);

CREATE INDEX version_references_topic_id_qa_idx ON version_references(topic_id);

CREATE INDEX version_references_skill_id_qa_idx ON version_references(skill_id);

CREATE INDEX version_references_definition_id_qa_idx ON version_references(definition_id);

CREATE INDEX version_references_seminar_material_id_qa_idx ON version_references(seminar_material_id);

CREATE INDEX version_references_literature_item_id_qa_idx ON version_references(literature_item_id);

CREATE INDEX version_references_file_asset_id_qa_idx ON version_references(file_asset_id);


CREATE TRIGGER directions_qa_code_lock BEFORE UPDATE ON directions
WHEN NEW.code IS NOT OLD.code OR NEW.normalized_key IS NOT OLD.normalized_key
BEGIN SELECT RAISE(ABORT,'immutable direction identity'); END;
CREATE TRIGGER semester_plans_qa_scope BEFORE INSERT ON semester_plans
WHEN NEW.program_version_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM course_offerings o JOIN program_versions v ON v.id=NEW.program_version_id
 JOIN course_programs p ON p.id=v.course_program_id WHERE o.id=NEW.offering_id AND o.course_id=p.course_id)
BEGIN SELECT RAISE(ABORT,'requires same course'); END;
CREATE TRIGGER semester_plans_qa_scope_update BEFORE UPDATE ON semester_plans
WHEN NEW.offering_id IS NOT OLD.offering_id OR (NEW.program_version_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM course_offerings o JOIN program_versions v ON v.id=NEW.program_version_id
 JOIN course_programs p ON p.id=v.course_program_id WHERE o.id=NEW.offering_id AND o.course_id=p.course_id))
BEGIN SELECT RAISE(ABORT,'requires same course'); END;
CREATE TRIGGER plan_modules_qa_bounds BEFORE INSERT ON plan_modules
WHEN NEW.end_week > (SELECT weeks FROM semester_plans WHERE id=NEW.semester_plan_id)
BEGIN SELECT RAISE(ABORT,'module outside semester'); END;
CREATE TRIGGER plan_modules_qa_bounds_update BEFORE UPDATE ON plan_modules
WHEN NEW.semester_plan_id IS NOT OLD.semester_plan_id OR NEW.end_week > (SELECT weeks FROM semester_plans WHERE id=NEW.semester_plan_id)
BEGIN SELECT RAISE(ABORT,'module outside semester'); END;
CREATE TRIGGER planned_works_qa_scope BEFORE INSERT ON planned_works
WHEN (NEW.module_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM plan_modules WHERE id=NEW.module_id AND semester_plan_id=NEW.semester_plan_id))
 OR (NEW.definition_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM homework_definitions d JOIN semester_plans p ON p.id=NEW.semester_plan_id JOIN course_offerings o ON o.id=p.offering_id WHERE d.id=NEW.definition_id AND d.course_id=o.course_id))
BEGIN SELECT RAISE(ABORT,'requires matching work context'); END;
CREATE TRIGGER planned_works_qa_scope_update BEFORE UPDATE ON planned_works
WHEN NEW.semester_plan_id IS NOT OLD.semester_plan_id OR (NEW.module_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM plan_modules WHERE id=NEW.module_id AND semester_plan_id=NEW.semester_plan_id))
 OR (NEW.definition_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM homework_definitions d JOIN semester_plans p ON p.id=NEW.semester_plan_id JOIN course_offerings o ON o.id=p.offering_id WHERE d.id=NEW.definition_id AND d.course_id=o.course_id))
BEGIN SELECT RAISE(ABORT,'requires matching work context'); END;
CREATE TRIGGER issued_works_qa_scope BEFORE INSERT ON issued_works
WHEN NOT EXISTS (SELECT 1 FROM planned_works w JOIN semester_plans p ON p.id=w.semester_plan_id JOIN assessments a ON a.offering_id=p.offering_id WHERE w.id=NEW.planned_work_id AND a.id=NEW.assessment_id)
BEGIN SELECT RAISE(ABORT,'requires same offering'); END;
CREATE TRIGGER submissions_qa_scope BEFORE INSERT ON submissions
WHEN NOT EXISTS (SELECT 1 FROM attempts a JOIN student_works w ON w.id=a.student_work_id WHERE a.id=NEW.attempt_id AND a.result='PRESENTED'
 AND (NEW.rule_id IS NULL OR EXISTS (SELECT 1 FROM scoring_rules r WHERE r.id=NEW.rule_id AND r.assessment_id=w.assessment_id)))
BEGIN SELECT RAISE(ABORT,'requires saved submission and matching rule'); END;
CREATE TRIGGER reviews_qa_scope BEFORE INSERT ON reviews
WHEN NOT EXISTS (SELECT 1 FROM submissions s JOIN attempts a ON a.id=s.attempt_id JOIN student_works w ON w.id=a.student_work_id JOIN assessments z ON z.id=w.assessment_id
 WHERE s.id=NEW.submission_id AND NEW.reviewed_at>=s.received_at AND NOT(z.type='HOMEWORK' AND NEW.result='REJECTED')
 AND (NEW.rule_id IS NULL OR EXISTS (SELECT 1 FROM scoring_rules r WHERE r.id=NEW.rule_id AND r.assessment_id=w.assessment_id AND r.min_cents IS NEW.min_cents AND r.max_cents IS NEW.max_cents)))
BEGIN SELECT RAISE(ABORT,'requires matching review context and snapshot'); END;
CREATE TRIGGER reviews_qa_sequence BEFORE INSERT ON reviews
WHEN NEW.review_seq != (SELECT COALESCE(MAX(review_seq),0)+1 FROM reviews WHERE submission_id=NEW.submission_id)
BEGIN SELECT RAISE(ABORT,'review number must increase'); END;
CREATE TRIGGER reviews_qa_revision_scored BEFORE INSERT ON reviews
WHEN NEW.result='SCORED' AND (SELECT result FROM reviews WHERE submission_id=NEW.submission_id AND result IN ('NEEDS_REVISION','ACCEPTED') ORDER BY review_seq DESC LIMIT 1)='NEEDS_REVISION'
BEGIN SELECT RAISE(ABORT,'revision requires explicit ACCEPTED'); END;
CREATE TRIGGER review_grades_qa_binding BEFORE INSERT ON review_grades
WHEN NOT EXISTS (SELECT 1 FROM reviews r WHERE r.id=NEW.review_id AND
 ((NEW.kind='NUMERIC' AND r.score_cents IS NEW.score_cents AND r.max_cents IS NEW.max_cents AND r.result IN ('ACCEPTED','SCORED'))
 OR (NEW.kind='PASS_FAIL' AND ((NEW.passed=1 AND r.result='ACCEPTED') OR (NEW.passed=0 AND r.result IN ('NEEDS_REVISION','REJECTED'))))
 OR NEW.kind='TRADITIONAL'))
BEGIN SELECT RAISE(ABORT,'requires matching grade snapshot'); END;
CREATE TRIGGER review_returns_qa_time BEFORE INSERT ON review_returns
WHEN NEW.returned_at < (SELECT reviewed_at FROM reviews WHERE id=NEW.review_id)
BEGIN SELECT RAISE(ABORT,'return precedes review'); END;
CREATE TRIGGER required_work_bindings_qa_scope BEFORE INSERT ON required_work_bindings
WHEN NOT EXISTS (SELECT 1 FROM required_work_sets s JOIN student_works w ON w.student_id=s.student_id JOIN issued_works i ON i.assessment_id=w.assessment_id JOIN planned_works p ON p.id=i.planned_work_id WHERE s.id=NEW.required_set_id AND w.id=NEW.student_work_id AND p.module_id=s.module_id)
BEGIN SELECT RAISE(ABORT,'requires same student and module'); END;

