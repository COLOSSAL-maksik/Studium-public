-- Additive only: all v7 columns, IDs, metadata and snapshot rows remain unchanged.
ALTER TABLE problems ADD COLUMN purposes_json TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(purposes_json) AND json_type(purposes_json) = 'array');
ALTER TABLE problems ADD COLUMN is_family BOOLEAN NOT NULL DEFAULT 0 CHECK (is_family IN (0,1));
ALTER TABLE problems ADD COLUMN family_id TEXT REFERENCES problems(id);
ALTER TABLE problems ADD COLUMN variant_code TEXT NOT NULL DEFAULT '';
ALTER TABLE problems ADD COLUMN parameters TEXT NOT NULL DEFAULT '';
CREATE INDEX problems_family_id ON problems(family_id);
CREATE UNIQUE INDEX uq_problem_variant_code ON problems(family_id,variant_code) WHERE family_id IS NOT NULL;
CREATE TRIGGER problems_family_insert BEFORE INSERT ON problems BEGIN
    SELECT CASE WHEN EXISTS (SELECT 1 FROM json_each(NEW.purposes_json) WHERE type != 'text' OR value NOT IN ('SEMINAR','CONTROL','EXAM','CONSULTATION')) THEN RAISE(ABORT,'invalid problem purpose') END;
    SELECT CASE WHEN NEW.family_id IS NULL AND NEW.variant_code != '' THEN RAISE(ABORT,'variant requires family') END;
    SELECT CASE WHEN NEW.family_id IS NOT NULL AND (
        NEW.is_family != 0 OR length(trim(NEW.variant_code)) = 0 OR NEW.statement != '' OR NEW.tags_json != '[]' OR NEW.purposes_json != '[]' OR NEW.identifier != '' OR
        NOT EXISTS (SELECT 1 FROM problems p WHERE p.id=NEW.family_id AND p.is_family=1 AND p.family_id IS NULL AND p.course_id=NEW.course_id AND p.deleted_at IS NULL)
    ) THEN RAISE(ABORT,'invalid problem variant') END;
END;
CREATE TRIGGER problems_family_update BEFORE UPDATE ON problems BEGIN
    SELECT CASE WHEN NEW.family_id IS NOT OLD.family_id OR NEW.is_family != OLD.is_family THEN RAISE(ABORT,'problem family structure is immutable') END;
    SELECT CASE WHEN EXISTS (SELECT 1 FROM json_each(NEW.purposes_json) WHERE type != 'text' OR value NOT IN ('SEMINAR','CONTROL','EXAM','CONSULTATION')) THEN RAISE(ABORT,'invalid problem purpose') END;
    SELECT CASE WHEN NEW.family_id IS NOT NULL AND (length(trim(NEW.variant_code)) = 0 OR NEW.statement != '' OR NEW.tags_json != '[]' OR NEW.purposes_json != '[]' OR NEW.identifier != '') THEN RAISE(ABORT,'variant inherits classification') END;
END;
