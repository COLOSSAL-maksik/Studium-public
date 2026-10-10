-- Iteration 4: concrete, additive Seminar/Problem and Module/Topic links.

CREATE TABLE seminar_problems (
	id TEXT NOT NULL, 
	seminar_material_id TEXT NOT NULL, 
	problem_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (seminar_material_id, problem_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(seminar_material_id) REFERENCES seminar_materials (id) ON DELETE RESTRICT, 
	FOREIGN KEY(problem_id) REFERENCES problems (id) ON DELETE RESTRICT
);

CREATE INDEX seminar_problems_problem_id ON seminar_problems (problem_id);

CREATE INDEX seminar_problems_seminar_material_id ON seminar_problems (seminar_material_id);

CREATE TRIGGER seminar_problems_metadata_update BEFORE UPDATE ON seminar_problems WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT,'immutable identity or invalid revision'); END;

CREATE TRIGGER seminar_problems_no_delete BEFORE DELETE ON seminar_problems BEGIN SELECT RAISE(ABORT,'record must be soft deleted'); END;

CREATE TRIGGER seminar_problems_identity_update BEFORE UPDATE ON seminar_problems WHEN NEW.seminar_material_id IS NOT OLD.seminar_material_id OR NEW.problem_id IS NOT OLD.problem_id BEGIN SELECT RAISE(ABORT,'immutable content ownership'); END;

CREATE TRIGGER seminar_problems_scope_insert BEFORE INSERT ON seminar_problems WHEN NOT EXISTS(SELECT 1 FROM seminar_materials s JOIN problems p ON p.course_id=s.course_id WHERE s.id=NEW.seminar_material_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT,'content link requires matching course'); END;

CREATE TRIGGER seminar_problems_scope_update BEFORE UPDATE ON seminar_problems WHEN NOT EXISTS(SELECT 1 FROM seminar_materials s JOIN problems p ON p.course_id=s.course_id WHERE s.id=NEW.seminar_material_id AND p.id=NEW.problem_id) BEGIN SELECT RAISE(ABORT,'content link requires matching course'); END;

CREATE TABLE module_topics (
	id TEXT NOT NULL, 
	module_id TEXT NOT NULL, 
	topic_id TEXT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	deleted_at INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (module_id, topic_id), 
	CHECK (length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'), 
	CHECK (typeof(created_at) = 'integer'), 
	CHECK (typeof(updated_at) = 'integer' AND updated_at >= created_at), 
	CHECK (typeof(revision) = 'integer' AND revision >= 1), 
	CHECK (deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)), 
	FOREIGN KEY(module_id) REFERENCES program_modules (id) ON DELETE RESTRICT, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE RESTRICT
);

CREATE INDEX module_topics_module_id ON module_topics (module_id);

CREATE INDEX module_topics_topic_id ON module_topics (topic_id);

CREATE TRIGGER module_topics_metadata_update BEFORE UPDATE ON module_topics WHEN NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision+1 OR NEW.updated_at < OLD.updated_at BEGIN SELECT RAISE(ABORT,'immutable identity or invalid revision'); END;

CREATE TRIGGER module_topics_no_delete BEFORE DELETE ON module_topics BEGIN SELECT RAISE(ABORT,'record must be soft deleted'); END;

CREATE TRIGGER module_topics_identity_update BEFORE UPDATE ON module_topics WHEN NEW.module_id IS NOT OLD.module_id OR NEW.topic_id IS NOT OLD.topic_id BEGIN SELECT RAISE(ABORT,'immutable content ownership'); END;

CREATE TRIGGER module_topics_scope_insert BEFORE INSERT ON module_topics WHEN NOT EXISTS(SELECT 1 FROM program_modules m JOIN work_programs w ON w.id=m.work_program_id JOIN topics t ON t.course_id=w.course_id WHERE m.id=NEW.module_id AND t.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT,'content link requires matching course'); END;

CREATE TRIGGER module_topics_scope_update BEFORE UPDATE ON module_topics WHEN NOT EXISTS(SELECT 1 FROM program_modules m JOIN work_programs w ON w.id=m.work_program_id JOIN topics t ON t.course_id=w.course_id WHERE m.id=NEW.module_id AND t.id=NEW.topic_id) BEGIN SELECT RAISE(ABORT,'content link requires matching course'); END;
