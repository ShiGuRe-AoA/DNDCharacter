CREATE TABLE IF NOT EXISTS rules_classes (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, english_name TEXT NOT NULL, ruleset TEXT NOT NULL,
 source TEXT NOT NULL, source_type TEXT NOT NULL, hit_die INTEGER NOT NULL,
 casting_ability TEXT NOT NULL, source_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules_subclasses (
 id TEXT PRIMARY KEY, class_id TEXT NOT NULL REFERENCES rules_classes(id),
 name TEXT NOT NULL, english_name TEXT NOT NULL, ruleset TEXT NOT NULL, source TEXT NOT NULL,
 source_type TEXT NOT NULL, source_path TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rules_subclasses_class ON rules_subclasses(class_id);
CREATE TABLE IF NOT EXISTS rules_class_features (
 id TEXT PRIMARY KEY, class_id TEXT NOT NULL REFERENCES rules_classes(id), name TEXT NOT NULL,
 level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 20), uses TEXT NOT NULL, uses_by_level TEXT NOT NULL,
 recovery TEXT NOT NULL, description TEXT NOT NULL, source_path TEXT NOT NULL, review_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rules_class_features_level ON rules_class_features(class_id,level);
CREATE TABLE IF NOT EXISTS rules_subclass_features (
 id TEXT PRIMARY KEY, subclass_id TEXT NOT NULL REFERENCES rules_subclasses(id), name TEXT NOT NULL,
 level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 20), uses TEXT NOT NULL, uses_by_level TEXT NOT NULL,
 recovery TEXT NOT NULL, description TEXT NOT NULL, source_path TEXT NOT NULL, review_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rules_subclass_features_level ON rules_subclass_features(subclass_id,level);
