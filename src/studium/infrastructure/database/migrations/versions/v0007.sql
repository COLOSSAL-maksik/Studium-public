-- Iteration 2 additive snapshot; existing records and v1-v6 resources retained.


CREATE TABLE work_programs (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	term_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	first_week_start TEXT NOT NULL, 
	weeks INTEGER DEFAULT 17 NOT NULL, 
	direction TEXT DEFAULT '' NOT NULL, 
	faculty TEXT DEFAULT '' NOT NULL, 
	version TEXT DEFAULT '' NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	semester TEXT DEFAULT 'AUTUMN' NOT NULL, 
	week_utc_offset_minutes INTEGER DEFAULT 180 NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (date(first_week_start, '+0 days') IS NOT NULL AND date(first_week_start, '+0 days') = first_week_start), 
	CHECK (typeof(weeks) = 'integer' AND weeks BETWEEN 1 AND 104), 
	CHECK (semester IN ('AUTUMN','SPRING')), 
	CHECK (typeof(week_utc_offset_minutes) = 'integer' AND week_utc_offset_minutes BETWEEN -840 AND 840), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT, 
	FOREIGN KEY(term_id) REFERENCES academic_terms (id) ON DELETE RESTRICT
)

;

CREATE INDEX work_programs_course_id ON work_programs (course_id);

CREATE INDEX work_programs_term_id ON work_programs (term_id);

CREATE TRIGGER work_programs_metadata_update BEFORE UPDATE ON work_programs WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER work_programs_no_delete BEFORE DELETE ON work_programs BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER work_programs_identity_update BEFORE UPDATE ON work_programs WHEN NEW.course_id IS NOT OLD.course_id OR NEW.term_id IS NOT OLD.term_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_modules (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	start_week INTEGER NOT NULL, 
	end_week INTEGER NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (length(trim(title)) > 0), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (typeof(start_week) = 'integer' AND typeof(end_week) = 'integer' AND start_week >= 1 AND end_week >= start_week), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_modules_work_program_id ON program_modules (work_program_id);

CREATE TRIGGER program_modules_metadata_update BEFORE UPDATE ON program_modules WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_modules_no_delete BEFORE DELETE ON program_modules BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_modules_identity_update BEFORE UPDATE ON program_modules WHEN NEW.work_program_id IS NOT OLD.work_program_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_works (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	definition_id TEXT NOT NULL, 
	module_id TEXT, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	planned_issue_week INTEGER, 
	planned_due_week INTEGER, 
	issue_date TEXT, 
	due_date TEXT, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	CHECK (planned_issue_week IS NULL OR (typeof(planned_issue_week) = 'integer' AND planned_issue_week >= 1)), 
	CHECK (planned_due_week IS NULL OR (typeof(planned_due_week) = 'integer' AND planned_due_week >= 1)), 
	CHECK (issue_date IS NULL OR (date(issue_date, '+0 days') IS NOT NULL AND date(issue_date, '+0 days') = issue_date)), 
	CHECK (due_date IS NULL OR (date(due_date, '+0 days') IS NOT NULL AND date(due_date, '+0 days') = due_date)), 
	UNIQUE (work_program_id, definition_id), 
	CHECK (planned_issue_week IS NULL OR planned_due_week IS NULL OR planned_due_week >= planned_issue_week), 
	CHECK (issue_date IS NULL OR due_date IS NULL OR due_date >= issue_date), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(module_id) REFERENCES program_modules (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_works_definition_id ON program_works (definition_id);

CREATE INDEX program_works_module_id ON program_works (module_id);

CREATE INDEX program_works_work_program_id ON program_works (work_program_id);

CREATE TRIGGER program_works_metadata_update BEFORE UPDATE ON program_works WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_works_no_delete BEFORE DELETE ON program_works BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_works_identity_update BEFORE UPDATE ON program_works WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.definition_id IS NOT OLD.definition_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE homework_packs (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
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

CREATE INDEX homework_packs_course_id ON homework_packs (course_id);

CREATE TRIGGER homework_packs_metadata_update BEFORE UPDATE ON homework_packs WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER homework_packs_no_delete BEFORE DELETE ON homework_packs BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER homework_packs_identity_update BEFORE UPDATE ON homework_packs WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE methodical_materials (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
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

CREATE INDEX methodical_materials_course_id ON methodical_materials (course_id);

CREATE TRIGGER methodical_materials_metadata_update BEFORE UPDATE ON methodical_materials WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER methodical_materials_no_delete BEFORE DELETE ON methodical_materials BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER methodical_materials_identity_update BEFORE UPDATE ON methodical_materials WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE knowledge_entries (
	id TEXT NOT NULL, 
	course_id TEXT NOT NULL, 
	title TEXT NOT NULL, 
	notes TEXT DEFAULT '' NOT NULL, 
	tags_json TEXT DEFAULT '[]' NOT NULL, 
	details_json TEXT DEFAULT '{}' NOT NULL, 
	answer TEXT DEFAULT '' NOT NULL, 
	type TEXT DEFAULT 'QUESTION' NOT NULL, 
	draft INTEGER DEFAULT 1 NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (type IN ('QUESTION','ERROR','UNDERSTANDING','ORGANIZATION')), 
	CHECK (draft IN (0,1)), 
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

CREATE INDEX knowledge_entries_course_id ON knowledge_entries (course_id);

CREATE TRIGGER knowledge_entries_metadata_update BEFORE UPDATE ON knowledge_entries WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER knowledge_entries_no_delete BEFORE DELETE ON knowledge_entries BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER knowledge_entries_identity_update BEFORE UPDATE ON knowledge_entries WHEN NEW.course_id IS NOT OLD.course_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE assessment_problems (
	id TEXT NOT NULL, 
	assessment_item_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	source_revision INTEGER NOT NULL, 
	statement_snapshot TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (assessment_item_id), 
	CHECK (typeof(source_revision) = 'integer' AND source_revision >= 1), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(assessment_item_id) REFERENCES assessment_items (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
)

;

CREATE INDEX assessment_problems_assessment_item_id ON assessment_problems (assessment_item_id);

CREATE INDEX assessment_problems_problem_id ON assessment_problems (problem_id);

CREATE TRIGGER assessment_problems_metadata_update BEFORE UPDATE ON assessment_problems WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER assessment_problems_no_delete BEFORE DELETE ON assessment_problems BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER assessment_problems_identity_update BEFORE UPDATE ON assessment_problems WHEN NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.problem_id IS NOT OLD.problem_id OR NEW.source_revision IS NOT OLD.source_revision OR NEW.statement_snapshot IS NOT OLD.statement_snapshot BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE student_problem_assignments (
	id TEXT NOT NULL, 
	student_work_id TEXT NOT NULL, 
	assessment_item_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	source_revision INTEGER NOT NULL, 
	title_snapshot TEXT DEFAULT '' NOT NULL, 
	statement_snapshot TEXT DEFAULT '' NOT NULL, 
	teacher_snapshot_json TEXT DEFAULT '{}' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (student_work_id, assessment_item_id), 
	CHECK (typeof(source_revision) = 'integer' AND source_revision >= 1), 
	CHECK (json_valid(teacher_snapshot_json) AND json_type(teacher_snapshot_json) = 'object'), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(student_work_id) REFERENCES student_works (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assessment_item_id) REFERENCES assessment_items (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
)

;

CREATE INDEX student_problem_assignments_assessment_item_id ON student_problem_assignments (assessment_item_id);

CREATE INDEX student_problem_assignments_problem_id ON student_problem_assignments (problem_id);

CREATE INDEX student_problem_assignments_student_work_id ON student_problem_assignments (student_work_id);

CREATE TRIGGER student_problem_assignments_metadata_update BEFORE UPDATE ON student_problem_assignments WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER student_problem_assignments_no_delete BEFORE DELETE ON student_problem_assignments BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER student_problem_assignments_identity_update BEFORE UPDATE ON student_problem_assignments WHEN NEW.student_work_id IS NOT OLD.student_work_id OR NEW.assessment_item_id IS NOT OLD.assessment_item_id OR NEW.problem_id IS NOT OLD.problem_id OR NEW.source_revision IS NOT OLD.source_revision OR NEW.title_snapshot IS NOT OLD.title_snapshot OR NEW.statement_snapshot IS NOT OLD.statement_snapshot OR NEW.teacher_snapshot_json IS NOT OLD.teacher_snapshot_json BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE attempt_skill_results (
	id TEXT NOT NULL, 
	attempt_item_result_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	outcome TEXT NOT NULL, 
	comment TEXT DEFAULT '' NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (outcome IN ('CORRECT','PARTIAL','INCORRECT','NOT_EVALUATED')), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(attempt_item_result_id) REFERENCES attempt_item_results (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE UNIQUE INDEX attempt_skill_results_active_pair ON attempt_skill_results (attempt_item_result_id, skill_id) WHERE deleted_at IS NULL;

CREATE INDEX attempt_skill_results_attempt_item_result_id ON attempt_skill_results (attempt_item_result_id);

CREATE INDEX attempt_skill_results_skill_id ON attempt_skill_results (skill_id);

CREATE TRIGGER attempt_skill_results_metadata_update BEFORE UPDATE ON attempt_skill_results WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER attempt_skill_results_no_delete BEFORE DELETE ON attempt_skill_results BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER attempt_skill_results_identity_update BEFORE UPDATE ON attempt_skill_results WHEN NEW.attempt_item_result_id IS NOT OLD.attempt_item_result_id OR NEW.skill_id IS NOT OLD.skill_id OR NEW.outcome IS NOT OLD.outcome OR NEW.comment IS NOT OLD.comment BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_topics (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (work_program_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_topics_topic_id ON program_topics (topic_id);

CREATE INDEX program_topics_work_program_id ON program_topics (work_program_id);

CREATE TRIGGER program_topics_metadata_update BEFORE UPDATE ON program_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_topics_no_delete BEFORE DELETE ON program_topics BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_topics_identity_update BEFORE UPDATE ON program_topics WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_skills (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (work_program_id, skill_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_skills_skill_id ON program_skills (skill_id);

CREATE INDEX program_skills_work_program_id ON program_skills (work_program_id);

CREATE TRIGGER program_skills_metadata_update BEFORE UPDATE ON program_skills WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_skills_no_delete BEFORE DELETE ON program_skills BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_skills_identity_update BEFORE UPDATE ON program_skills WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.skill_id IS NOT OLD.skill_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_materials (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	seminar_material_id TEXT NOT NULL, 
	module_id TEXT, 
	planned_week INTEGER, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1)), 
	UNIQUE (work_program_id, seminar_material_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(seminar_material_id) REFERENCES seminar_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(module_id) REFERENCES program_modules (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_materials_module_id ON program_materials (module_id);

CREATE INDEX program_materials_seminar_material_id ON program_materials (seminar_material_id);

CREATE INDEX program_materials_work_program_id ON program_materials (work_program_id);

CREATE TRIGGER program_materials_metadata_update BEFORE UPDATE ON program_materials WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_materials_no_delete BEFORE DELETE ON program_materials BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_materials_identity_update BEFORE UPDATE ON program_materials WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.seminar_material_id IS NOT OLD.seminar_material_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_literature (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
	literature_item_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (work_program_id, literature_item_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(literature_item_id) REFERENCES literature_items (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_literature_literature_item_id ON program_literature (literature_item_id);

CREATE INDEX program_literature_work_program_id ON program_literature (work_program_id);

CREATE TRIGGER program_literature_metadata_update BEFORE UPDATE ON program_literature WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_literature_no_delete BEFORE DELETE ON program_literature BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_literature_identity_update BEFORE UPDATE ON program_literature WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.literature_item_id IS NOT OLD.literature_item_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE homework_pack_works (
	id TEXT NOT NULL, 
	homework_pack_id TEXT NOT NULL, 
	definition_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (homework_pack_id, definition_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(homework_pack_id) REFERENCES homework_packs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT
)

;

CREATE INDEX homework_pack_works_definition_id ON homework_pack_works (definition_id);

CREATE INDEX homework_pack_works_homework_pack_id ON homework_pack_works (homework_pack_id);

CREATE TRIGGER homework_pack_works_metadata_update BEFORE UPDATE ON homework_pack_works WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER homework_pack_works_no_delete BEFORE DELETE ON homework_pack_works BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER homework_pack_works_identity_update BEFORE UPDATE ON homework_pack_works WHEN NEW.homework_pack_id IS NOT OLD.homework_pack_id OR NEW.definition_id IS NOT OLD.definition_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE knowledge_sources (
	id TEXT NOT NULL, 
	knowledge_entry_id TEXT NOT NULL, 
	question_case_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (knowledge_entry_id, question_case_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(knowledge_entry_id) REFERENCES knowledge_entries (id) ON DELETE RESTRICT, 
	FOREIGN KEY(question_case_id) REFERENCES question_cases (id) ON DELETE RESTRICT
)

;

CREATE INDEX knowledge_sources_knowledge_entry_id ON knowledge_sources (knowledge_entry_id);

CREATE INDEX knowledge_sources_question_case_id ON knowledge_sources (question_case_id);

CREATE TRIGGER knowledge_sources_metadata_update BEFORE UPDATE ON knowledge_sources WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER knowledge_sources_no_delete BEFORE DELETE ON knowledge_sources BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER knowledge_sources_identity_update BEFORE UPDATE ON knowledge_sources WHEN NEW.knowledge_entry_id IS NOT OLD.knowledge_entry_id OR NEW.question_case_id IS NOT OLD.question_case_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE knowledge_materials (
	id TEXT NOT NULL, 
	knowledge_entry_id TEXT NOT NULL, 
	methodical_material_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (knowledge_entry_id, methodical_material_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(knowledge_entry_id) REFERENCES knowledge_entries (id) ON DELETE RESTRICT, 
	FOREIGN KEY(methodical_material_id) REFERENCES methodical_materials (id) ON DELETE RESTRICT
)

;

CREATE INDEX knowledge_materials_knowledge_entry_id ON knowledge_materials (knowledge_entry_id);

CREATE INDEX knowledge_materials_methodical_material_id ON knowledge_materials (methodical_material_id);

CREATE TRIGGER knowledge_materials_metadata_update BEFORE UPDATE ON knowledge_materials WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER knowledge_materials_no_delete BEFORE DELETE ON knowledge_materials BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER knowledge_materials_identity_update BEFORE UPDATE ON knowledge_materials WHEN NEW.knowledge_entry_id IS NOT OLD.knowledge_entry_id OR NEW.methodical_material_id IS NOT OLD.methodical_material_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE definition_problems (
	id TEXT NOT NULL, 
	definition_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	sort_order INTEGER DEFAULT 0 NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	CHECK (typeof(sort_order) = 'integer' AND sort_order >= 0), 
	UNIQUE (definition_id, problem_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
)

;

CREATE INDEX definition_problems_definition_id ON definition_problems (definition_id);

CREATE INDEX definition_problems_problem_id ON definition_problems (problem_id);

CREATE TRIGGER definition_problems_metadata_update BEFORE UPDATE ON definition_problems WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER definition_problems_no_delete BEFORE DELETE ON definition_problems BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER definition_problems_identity_update BEFORE UPDATE ON definition_problems WHEN NEW.definition_id IS NOT OLD.definition_id OR NEW.problem_id IS NOT OLD.problem_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE problem_topics (
	id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (problem_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX problem_topics_problem_id ON problem_topics (problem_id);

CREATE INDEX problem_topics_topic_id ON problem_topics (topic_id);

CREATE TRIGGER problem_topics_metadata_update BEFORE UPDATE ON problem_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problem_topics_no_delete BEFORE DELETE ON problem_topics BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problem_topics_identity_update BEFORE UPDATE ON problem_topics WHEN NEW.problem_id IS NOT OLD.problem_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE problem_skills (
	id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (problem_id, skill_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE INDEX problem_skills_problem_id ON problem_skills (problem_id);

CREATE INDEX problem_skills_skill_id ON problem_skills (skill_id);

CREATE TRIGGER problem_skills_metadata_update BEFORE UPDATE ON problem_skills WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER problem_skills_no_delete BEFORE DELETE ON problem_skills BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER problem_skills_identity_update BEFORE UPDATE ON problem_skills WHEN NEW.problem_id IS NOT OLD.problem_id OR NEW.skill_id IS NOT OLD.skill_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE definition_topics (
	id TEXT NOT NULL, 
	definition_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (definition_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX definition_topics_definition_id ON definition_topics (definition_id);

CREATE INDEX definition_topics_topic_id ON definition_topics (topic_id);

CREATE TRIGGER definition_topics_metadata_update BEFORE UPDATE ON definition_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER definition_topics_no_delete BEFORE DELETE ON definition_topics BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER definition_topics_identity_update BEFORE UPDATE ON definition_topics WHEN NEW.definition_id IS NOT OLD.definition_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE definition_skills (
	id TEXT NOT NULL, 
	definition_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (definition_id, skill_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(definition_id) REFERENCES homework_definitions (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE INDEX definition_skills_definition_id ON definition_skills (definition_id);

CREATE INDEX definition_skills_skill_id ON definition_skills (skill_id);

CREATE TRIGGER definition_skills_metadata_update BEFORE UPDATE ON definition_skills WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER definition_skills_no_delete BEFORE DELETE ON definition_skills BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER definition_skills_identity_update BEFORE UPDATE ON definition_skills WHEN NEW.definition_id IS NOT OLD.definition_id OR NEW.skill_id IS NOT OLD.skill_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE methodical_topics (
	id TEXT NOT NULL, 
	methodical_material_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (methodical_material_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(methodical_material_id) REFERENCES methodical_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX methodical_topics_methodical_material_id ON methodical_topics (methodical_material_id);

CREATE INDEX methodical_topics_topic_id ON methodical_topics (topic_id);

CREATE TRIGGER methodical_topics_metadata_update BEFORE UPDATE ON methodical_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER methodical_topics_no_delete BEFORE DELETE ON methodical_topics BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER methodical_topics_identity_update BEFORE UPDATE ON methodical_topics WHEN NEW.methodical_material_id IS NOT OLD.methodical_material_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE methodical_skills (
	id TEXT NOT NULL, 
	methodical_material_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (methodical_material_id, skill_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(methodical_material_id) REFERENCES methodical_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE INDEX methodical_skills_methodical_material_id ON methodical_skills (methodical_material_id);

CREATE INDEX methodical_skills_skill_id ON methodical_skills (skill_id);

CREATE TRIGGER methodical_skills_metadata_update BEFORE UPDATE ON methodical_skills WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER methodical_skills_no_delete BEFORE DELETE ON methodical_skills BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER methodical_skills_identity_update BEFORE UPDATE ON methodical_skills WHEN NEW.methodical_material_id IS NOT OLD.methodical_material_id OR NEW.skill_id IS NOT OLD.skill_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE knowledge_topics (
	id TEXT NOT NULL, 
	knowledge_entry_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (knowledge_entry_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(knowledge_entry_id) REFERENCES knowledge_entries (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
)

;

CREATE INDEX knowledge_topics_knowledge_entry_id ON knowledge_topics (knowledge_entry_id);

CREATE INDEX knowledge_topics_topic_id ON knowledge_topics (topic_id);

CREATE TRIGGER knowledge_topics_metadata_update BEFORE UPDATE ON knowledge_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER knowledge_topics_no_delete BEFORE DELETE ON knowledge_topics BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER knowledge_topics_identity_update BEFORE UPDATE ON knowledge_topics WHEN NEW.knowledge_entry_id IS NOT OLD.knowledge_entry_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE knowledge_skills (
	id TEXT NOT NULL, 
	knowledge_entry_id TEXT NOT NULL, 
	skill_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (knowledge_entry_id, skill_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(knowledge_entry_id) REFERENCES knowledge_entries (id) ON DELETE RESTRICT, 
	FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;

CREATE INDEX knowledge_skills_knowledge_entry_id ON knowledge_skills (knowledge_entry_id);

CREATE INDEX knowledge_skills_skill_id ON knowledge_skills (skill_id);

CREATE TRIGGER knowledge_skills_metadata_update BEFORE UPDATE ON knowledge_skills WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER knowledge_skills_no_delete BEFORE DELETE ON knowledge_skills BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER knowledge_skills_identity_update BEFORE UPDATE ON knowledge_skills WHEN NEW.knowledge_entry_id IS NOT OLD.knowledge_entry_id OR NEW.skill_id IS NOT OLD.skill_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE student_problem_files (
	id TEXT NOT NULL, 
	student_problem_assignment_id TEXT NOT NULL, 
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
	UNIQUE (student_problem_assignment_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(student_problem_assignment_id) REFERENCES student_problem_assignments (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX student_problem_files_file_asset_id ON student_problem_files (file_asset_id);

CREATE INDEX student_problem_files_student_problem_assignment_id ON student_problem_files (student_problem_assignment_id);

CREATE TRIGGER student_problem_files_metadata_update BEFORE UPDATE ON student_problem_files WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER student_problem_files_no_delete BEFORE DELETE ON student_problem_files BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER student_problem_files_identity_update BEFORE UPDATE ON student_problem_files WHEN NEW.student_problem_assignment_id IS NOT OLD.student_problem_assignment_id OR NEW.file_asset_id IS NOT OLD.file_asset_id OR NEW.caption IS NOT OLD.caption OR NEW.sort_order IS NOT OLD.sort_order OR NEW.role IS NOT OLD.role BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE program_attachments (
	id TEXT NOT NULL, 
	work_program_id TEXT NOT NULL, 
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
	UNIQUE (work_program_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(work_program_id) REFERENCES work_programs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX program_attachments_file_asset_id ON program_attachments (file_asset_id);

CREATE INDEX program_attachments_work_program_id ON program_attachments (work_program_id);

CREATE TRIGGER program_attachments_metadata_update BEFORE UPDATE ON program_attachments WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER program_attachments_no_delete BEFORE DELETE ON program_attachments BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER program_attachments_identity_update BEFORE UPDATE ON program_attachments WHEN NEW.work_program_id IS NOT OLD.work_program_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE homework_pack_attachments (
	id TEXT NOT NULL, 
	homework_pack_id TEXT NOT NULL, 
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
	UNIQUE (homework_pack_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(homework_pack_id) REFERENCES homework_packs (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX homework_pack_attachments_file_asset_id ON homework_pack_attachments (file_asset_id);

CREATE INDEX homework_pack_attachments_homework_pack_id ON homework_pack_attachments (homework_pack_id);

CREATE TRIGGER homework_pack_attachments_metadata_update BEFORE UPDATE ON homework_pack_attachments WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER homework_pack_attachments_no_delete BEFORE DELETE ON homework_pack_attachments BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER homework_pack_attachments_identity_update BEFORE UPDATE ON homework_pack_attachments WHEN NEW.homework_pack_id IS NOT OLD.homework_pack_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE methodical_attachments (
	id TEXT NOT NULL, 
	methodical_material_id TEXT NOT NULL, 
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
	UNIQUE (methodical_material_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(methodical_material_id) REFERENCES methodical_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX methodical_attachments_file_asset_id ON methodical_attachments (file_asset_id);

CREATE INDEX methodical_attachments_methodical_material_id ON methodical_attachments (methodical_material_id);

CREATE TRIGGER methodical_attachments_metadata_update BEFORE UPDATE ON methodical_attachments WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER methodical_attachments_no_delete BEFORE DELETE ON methodical_attachments BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER methodical_attachments_identity_update BEFORE UPDATE ON methodical_attachments WHEN NEW.methodical_material_id IS NOT OLD.methodical_material_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;


CREATE TABLE assessment_attachments (
	id TEXT NOT NULL, 
	assessment_id TEXT NOT NULL, 
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
	UNIQUE (assessment_id, file_asset_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE RESTRICT, 
	FOREIGN KEY(file_asset_id) REFERENCES file_assets (id) ON DELETE RESTRICT
)

;

CREATE INDEX assessment_attachments_assessment_id ON assessment_attachments (assessment_id);

CREATE INDEX assessment_attachments_file_asset_id ON assessment_attachments (file_asset_id);

CREATE TRIGGER assessment_attachments_metadata_update BEFORE UPDATE ON assessment_attachments WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT, 'immutable identity or invalid revision'); END;

CREATE TRIGGER assessment_attachments_no_delete BEFORE DELETE ON assessment_attachments BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;

CREATE TRIGGER assessment_attachments_identity_update BEFORE UPDATE ON assessment_attachments WHEN NEW.assessment_id IS NOT OLD.assessment_id OR NEW.file_asset_id IS NOT OLD.file_asset_id BEGIN SELECT RAISE(ABORT, 'immutable ownership or factual snapshot'); END;

ALTER TABLE student_groups ADD COLUMN faculty_short TEXT NOT NULL DEFAULT '';

ALTER TABLE course_offerings ADD COLUMN work_program_id TEXT REFERENCES work_programs(id);

CREATE INDEX course_offerings_work_program ON course_offerings(work_program_id);

ALTER TABLE assessments ADD COLUMN program_work_id TEXT REFERENCES program_works(id);

CREATE INDEX assessments_program_work ON assessments(program_work_id);

CREATE UNIQUE INDEX assessments_program_work_active ON assessments(offering_id,program_work_id) WHERE deleted_at IS NULL AND program_work_id IS NOT NULL;

ALTER TABLE homework_definitions ADD COLUMN type TEXT NOT NULL DEFAULT 'HOMEWORK' CHECK(type IN ('HOMEWORK','CONTROL_WORK','LAB','DEFENSE','EXAM','TEST','OTHER'));

ALTER TABLE problems ADD COLUMN identifier TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX problems_identifier_active ON problems(course_id,identifier) WHERE deleted_at IS NULL AND identifier != '';

ALTER TABLE seminar_materials ADD COLUMN type TEXT NOT NULL DEFAULT 'SEMINAR' CHECK(type IN ('SEMINAR','LECTURE'));

ALTER TABLE lessons ADD COLUMN planned_date TEXT CHECK(planned_date IS NULL OR (date(planned_date, '+0 days') IS NOT NULL AND date(planned_date, '+0 days') = planned_date));

ALTER TABLE lessons ADD COLUMN planned_week INTEGER CHECK(planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1));

ALTER TABLE lessons ADD COLUMN module_id TEXT REFERENCES program_modules(id);

ALTER TABLE lessons ADD COLUMN cancelled INTEGER NOT NULL DEFAULT 0 CHECK(cancelled IN (0,1));

ALTER TABLE lessons ADD COLUMN cancellation_reason TEXT NOT NULL DEFAULT '';

CREATE TRIGGER file_assets_student_problem_files_guard BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM student_problem_files WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_program_attachments_guard BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM program_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_homework_pack_attachments_guard BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM homework_pack_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_methodical_attachments_guard BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM methodical_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER file_assets_assessment_attachments_guard BEFORE UPDATE ON file_assets WHEN NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM assessment_attachments WHERE file_asset_id=NEW.id AND deleted_at IS NULL) BEGIN SELECT RAISE(ABORT, 'asset requires detached content attachments'); END;

CREATE TRIGGER course_offerings_program_context_insert BEFORE INSERT ON course_offerings WHEN NEW.work_program_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND p.course_id=NEW.course_id AND p.term_id=NEW.term_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER course_offerings_program_context_update BEFORE UPDATE ON course_offerings WHEN NEW.work_program_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND p.course_id=NEW.course_id AND p.term_id=NEW.term_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_modules_program_context_insert BEFORE INSERT ON program_modules WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND NEW.end_week<=p.weeks) OR EXISTS(SELECT 1 FROM program_modules m WHERE m.work_program_id=NEW.work_program_id AND m.id!=NEW.id AND m.deleted_at IS NULL AND m.start_week<=NEW.end_week AND m.end_week>=NEW.start_week)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_modules_program_context_update BEFORE UPDATE ON program_modules WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND NEW.end_week<=p.weeks) OR EXISTS(SELECT 1 FROM program_modules m WHERE m.work_program_id=NEW.work_program_id AND m.id!=NEW.id AND m.deleted_at IS NULL AND m.start_week<=NEW.end_week AND m.end_week>=NEW.start_week)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_works_program_context_insert BEFORE INSERT ON program_works WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.work_program_id AND d.id=NEW.definition_id AND (NEW.planned_issue_week IS NULL OR NEW.planned_issue_week<=p.weeks) AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules m WHERE m.id=NEW.module_id AND m.work_program_id=p.id AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week BETWEEN m.start_week AND m.end_week))) AND (NEW.issue_date IS NULL OR (NEW.planned_issue_week IS NOT NULL AND NEW.issue_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_issue_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_issue_week*7-1) || ' days'))) AND (NEW.due_date IS NULL OR (NEW.planned_due_week IS NOT NULL AND NEW.due_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_due_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_due_week*7-1) || ' days')))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_works_program_context_update BEFORE UPDATE ON program_works WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.work_program_id AND d.id=NEW.definition_id AND (NEW.planned_issue_week IS NULL OR NEW.planned_issue_week<=p.weeks) AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules m WHERE m.id=NEW.module_id AND m.work_program_id=p.id AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week BETWEEN m.start_week AND m.end_week))) AND (NEW.issue_date IS NULL OR (NEW.planned_issue_week IS NOT NULL AND NEW.issue_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_issue_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_issue_week*7-1) || ' days'))) AND (NEW.due_date IS NULL OR (NEW.planned_due_week IS NOT NULL AND NEW.due_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_due_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_due_week*7-1) || ' days')))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessments_program_context_insert BEFORE INSERT ON assessments WHEN NEW.program_work_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_works w JOIN course_offerings o ON o.work_program_id=w.work_program_id WHERE w.id=NEW.program_work_id AND o.id=NEW.offering_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessments_program_context_update BEFORE UPDATE ON assessments WHEN NEW.program_work_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_works w JOIN course_offerings o ON o.work_program_id=w.work_program_id WHERE w.id=NEW.program_work_id AND o.id=NEW.offering_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER lessons_program_context_insert BEFORE INSERT ON lessons WHEN (NEW.planned_week IS NOT NULL AND NOT EXISTS(SELECT 1 FROM course_offerings o JOIN work_programs p ON p.id=o.work_program_id WHERE o.id=NEW.course_offering_id AND NEW.planned_week<=p.weeks)) OR (NEW.module_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_modules m JOIN course_offerings o ON o.work_program_id=m.work_program_id WHERE m.id=NEW.module_id AND o.id=NEW.course_offering_id AND (NEW.planned_week IS NULL OR NEW.planned_week BETWEEN m.start_week AND m.end_week))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER lessons_program_context_update BEFORE UPDATE ON lessons WHEN (NEW.planned_week IS NOT NULL AND NOT EXISTS(SELECT 1 FROM course_offerings o JOIN work_programs p ON p.id=o.work_program_id WHERE o.id=NEW.course_offering_id AND NEW.planned_week<=p.weeks)) OR (NEW.module_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_modules m JOIN course_offerings o ON o.work_program_id=m.work_program_id WHERE m.id=NEW.module_id AND o.id=NEW.course_offering_id AND (NEW.planned_week IS NULL OR NEW.planned_week BETWEEN m.start_week AND m.end_week))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER homework_pack_works_program_context_insert BEFORE INSERT ON homework_pack_works WHEN NOT EXISTS(SELECT 1 FROM homework_packs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.homework_pack_id AND d.id=NEW.definition_id AND d.type='HOMEWORK') BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER homework_pack_works_program_context_update BEFORE UPDATE ON homework_pack_works WHEN NOT EXISTS(SELECT 1 FROM homework_packs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.homework_pack_id AND d.id=NEW.definition_id AND d.type='HOMEWORK') BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_problems_program_context_insert BEFORE INSERT ON definition_problems WHEN NOT EXISTS(SELECT 1 FROM homework_definitions d JOIN problems p ON p.course_id=d.course_id WHERE d.id=NEW.definition_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_problems_program_context_update BEFORE UPDATE ON definition_problems WHEN NOT EXISTS(SELECT 1 FROM homework_definitions d JOIN problems p ON p.course_id=d.course_id WHERE d.id=NEW.definition_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessment_problems_program_context_insert BEFORE INSERT ON assessment_problems WHEN NOT EXISTS(SELECT 1 FROM assessment_items i JOIN assessments a ON a.id=i.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE i.id=NEW.assessment_item_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessment_problems_program_context_update BEFORE UPDATE ON assessment_problems WHEN NOT EXISTS(SELECT 1 FROM assessment_items i JOIN assessments a ON a.id=i.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE i.id=NEW.assessment_item_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER student_problem_assignments_program_context_insert BEFORE INSERT ON student_problem_assignments WHEN NOT EXISTS(SELECT 1 FROM student_works w JOIN assessment_items i ON i.assessment_id=w.assessment_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE w.id=NEW.student_work_id AND i.id=NEW.assessment_item_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER student_problem_assignments_program_context_update BEFORE UPDATE ON student_problem_assignments WHEN NOT EXISTS(SELECT 1 FROM student_works w JOIN assessment_items i ON i.assessment_id=w.assessment_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE w.id=NEW.student_work_id AND i.id=NEW.assessment_item_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER attempt_skill_results_program_context_insert BEFORE INSERT ON attempt_skill_results WHEN NOT EXISTS(SELECT 1 FROM attempt_item_results r JOIN attempts t ON t.id=r.attempt_id JOIN student_works w ON w.id=t.student_work_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN skills s ON s.course_id=o.course_id WHERE r.id=NEW.attempt_item_result_id AND s.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER attempt_skill_results_program_context_update BEFORE UPDATE ON attempt_skill_results WHEN NOT EXISTS(SELECT 1 FROM attempt_item_results r JOIN attempts t ON t.id=r.attempt_id JOIN student_works w ON w.id=t.student_work_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN skills s ON s.course_id=o.course_id WHERE r.id=NEW.attempt_item_result_id AND s.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_sources_program_context_insert BEFORE INSERT ON knowledge_sources WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN question_cases q ON q.id=NEW.question_case_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE k.id=NEW.knowledge_entry_id AND k.course_id=o.course_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_sources_program_context_update BEFORE UPDATE ON knowledge_sources WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN question_cases q ON q.id=NEW.question_case_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE k.id=NEW.knowledge_entry_id AND k.course_id=o.course_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_materials_program_context_insert BEFORE INSERT ON knowledge_materials WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN methodical_materials m ON m.course_id=k.course_id WHERE k.id=NEW.knowledge_entry_id AND m.id=NEW.methodical_material_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_materials_program_context_update BEFORE UPDATE ON knowledge_materials WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN methodical_materials m ON m.course_id=k.course_id WHERE k.id=NEW.knowledge_entry_id AND m.id=NEW.methodical_material_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_topics_program_context_insert BEFORE INSERT ON program_topics WHEN NOT EXISTS(SELECT 1 FROM work_programs a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.work_program_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_topics_program_context_update BEFORE UPDATE ON program_topics WHEN NOT EXISTS(SELECT 1 FROM work_programs a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.work_program_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_skills_program_context_insert BEFORE INSERT ON program_skills WHEN NOT EXISTS(SELECT 1 FROM work_programs a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.work_program_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_skills_program_context_update BEFORE UPDATE ON program_skills WHEN NOT EXISTS(SELECT 1 FROM work_programs a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.work_program_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER problem_topics_program_context_insert BEFORE INSERT ON problem_topics WHEN NOT EXISTS(SELECT 1 FROM problems a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.problem_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER problem_topics_program_context_update BEFORE UPDATE ON problem_topics WHEN NOT EXISTS(SELECT 1 FROM problems a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.problem_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER problem_skills_program_context_insert BEFORE INSERT ON problem_skills WHEN NOT EXISTS(SELECT 1 FROM problems a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.problem_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER problem_skills_program_context_update BEFORE UPDATE ON problem_skills WHEN NOT EXISTS(SELECT 1 FROM problems a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.problem_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_topics_program_context_insert BEFORE INSERT ON definition_topics WHEN NOT EXISTS(SELECT 1 FROM homework_definitions a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.definition_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_topics_program_context_update BEFORE UPDATE ON definition_topics WHEN NOT EXISTS(SELECT 1 FROM homework_definitions a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.definition_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_skills_program_context_insert BEFORE INSERT ON definition_skills WHEN NOT EXISTS(SELECT 1 FROM homework_definitions a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.definition_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER definition_skills_program_context_update BEFORE UPDATE ON definition_skills WHEN NOT EXISTS(SELECT 1 FROM homework_definitions a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.definition_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_topics_program_context_insert BEFORE INSERT ON methodical_topics WHEN NOT EXISTS(SELECT 1 FROM methodical_materials a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.methodical_material_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_topics_program_context_update BEFORE UPDATE ON methodical_topics WHEN NOT EXISTS(SELECT 1 FROM methodical_materials a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.methodical_material_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_skills_program_context_insert BEFORE INSERT ON methodical_skills WHEN NOT EXISTS(SELECT 1 FROM methodical_materials a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.methodical_material_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_skills_program_context_update BEFORE UPDATE ON methodical_skills WHEN NOT EXISTS(SELECT 1 FROM methodical_materials a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.methodical_material_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_topics_program_context_insert BEFORE INSERT ON knowledge_topics WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.knowledge_entry_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_topics_program_context_update BEFORE UPDATE ON knowledge_topics WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries a JOIN topics b ON b.course_id=a.course_id WHERE a.id=NEW.knowledge_entry_id AND b.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_skills_program_context_insert BEFORE INSERT ON knowledge_skills WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.knowledge_entry_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER knowledge_skills_program_context_update BEFORE UPDATE ON knowledge_skills WHEN NOT EXISTS(SELECT 1 FROM knowledge_entries a JOIN skills b ON b.course_id=a.course_id WHERE a.id=NEW.knowledge_entry_id AND b.id=NEW.skill_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER student_problem_files_program_context_insert BEFORE INSERT ON student_problem_files WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM student_problem_assignments WHERE id=NEW.student_problem_assignment_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER student_problem_files_program_context_update BEFORE UPDATE ON student_problem_files WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM student_problem_assignments WHERE id=NEW.student_problem_assignment_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_attachments_program_context_insert BEFORE INSERT ON program_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM work_programs WHERE id=NEW.work_program_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_attachments_program_context_update BEFORE UPDATE ON program_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM work_programs WHERE id=NEW.work_program_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER homework_pack_attachments_program_context_insert BEFORE INSERT ON homework_pack_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM homework_packs WHERE id=NEW.homework_pack_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER homework_pack_attachments_program_context_update BEFORE UPDATE ON homework_pack_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM homework_packs WHERE id=NEW.homework_pack_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_attachments_program_context_insert BEFORE INSERT ON methodical_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM methodical_materials WHERE id=NEW.methodical_material_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER methodical_attachments_program_context_update BEFORE UPDATE ON methodical_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM methodical_materials WHERE id=NEW.methodical_material_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessment_attachments_program_context_insert BEFORE INSERT ON assessment_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM assessments WHERE id=NEW.assessment_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER assessment_attachments_program_context_update BEFORE UPDATE ON assessment_attachments WHEN NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM assessments WHERE id=NEW.assessment_id AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL)) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_materials_program_context_insert BEFORE INSERT ON program_materials WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN seminar_materials m ON m.course_id=p.course_id WHERE p.id=NEW.work_program_id AND m.id=NEW.seminar_material_id AND (NEW.planned_week IS NULL OR NEW.planned_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules x WHERE x.id=NEW.module_id AND x.work_program_id=p.id))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_materials_program_context_update BEFORE UPDATE ON program_materials WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN seminar_materials m ON m.course_id=p.course_id WHERE p.id=NEW.work_program_id AND m.id=NEW.seminar_material_id AND (NEW.planned_week IS NULL OR NEW.planned_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules x WHERE x.id=NEW.module_id AND x.work_program_id=p.id))) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_literature_program_context_insert BEFORE INSERT ON program_literature WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN literature_items l ON l.course_id IS NULL OR l.course_id=p.course_id WHERE p.id=NEW.work_program_id AND l.id=NEW.literature_item_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER program_literature_program_context_update BEFORE UPDATE ON program_literature WHEN NOT EXISTS(SELECT 1 FROM work_programs p JOIN literature_items l ON l.course_id IS NULL OR l.course_id=p.course_id WHERE p.id=NEW.work_program_id AND l.id=NEW.literature_item_id) BEGIN SELECT RAISE(ABORT, 'link requires matching discipline/program/week'); END;

CREATE TRIGGER attempts_homework_result BEFORE INSERT ON attempts WHEN NEW.result='REJECTED' AND EXISTS(SELECT 1 FROM student_works w JOIN assessments a ON a.id=w.assessment_id WHERE w.id=NEW.student_work_id AND a.type='HOMEWORK') BEGIN SELECT RAISE(ABORT, 'homework requires revision instead of rejection'); END;

CREATE TRIGGER student_problem_assignments_history_lock BEFORE INSERT ON student_problem_assignments WHEN EXISTS(SELECT 1 FROM attempts WHERE student_work_id=NEW.student_work_id) BEGIN SELECT RAISE(ABORT, 'task assignment requires an unattempted work'); END;

CREATE TRIGGER course_offerings_program_lock BEFORE UPDATE ON course_offerings WHEN OLD.work_program_id IS NOT NULL AND NEW.work_program_id IS NOT OLD.work_program_id AND (EXISTS(SELECT 1 FROM assessments WHERE offering_id=OLD.id) OR EXISTS(SELECT 1 FROM lessons WHERE course_offering_id=OLD.id)) BEGIN SELECT RAISE(ABORT, 'immutable historical program context'); END;

CREATE TRIGGER assessments_program_lock BEFORE UPDATE ON assessments WHEN OLD.program_work_id IS NOT NULL AND NEW.program_work_id IS NOT OLD.program_work_id BEGIN SELECT RAISE(ABORT, 'immutable issued program work'); END;

CREATE TRIGGER work_programs_calendar_lock BEFORE UPDATE ON work_programs WHEN (NEW.first_week_start IS NOT OLD.first_week_start OR NEW.week_utc_offset_minutes IS NOT OLD.week_utc_offset_minutes) AND EXISTS(SELECT 1 FROM course_offerings o JOIN assessments a ON a.offering_id=o.id JOIN analytics_locked_assessments l ON l.id=a.id WHERE o.work_program_id=OLD.id) BEGIN SELECT RAISE(ABORT, 'immutable historical program calendar'); END;

CREATE TRIGGER work_programs_duration_guard BEFORE UPDATE ON work_programs WHEN EXISTS(SELECT 1 FROM program_modules WHERE work_program_id=OLD.id AND deleted_at IS NULL AND end_week>NEW.weeks) OR EXISTS(SELECT 1 FROM program_works WHERE work_program_id=OLD.id AND deleted_at IS NULL AND (planned_issue_week>NEW.weeks OR planned_due_week>NEW.weeks)) BEGIN SELECT RAISE(ABORT, 'duration requires retaining planned weeks'); END;

CREATE TRIGGER program_modules_work_bounds BEFORE UPDATE ON program_modules WHEN EXISTS(SELECT 1 FROM program_works WHERE module_id=OLD.id AND deleted_at IS NULL AND planned_due_week IS NOT NULL AND planned_due_week NOT BETWEEN NEW.start_week AND NEW.end_week) BEGIN SELECT RAISE(ABORT, 'module requires retaining planned work weeks'); END;
