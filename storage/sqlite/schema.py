"""SQL schema definitions for SQLite GraphStore and EventStore."""

INIT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT NOT NULL,
    namespace TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    merged_into TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_label ON entities(label);
CREATE INDEX IF NOT EXISTS idx_entities_namespace ON entities(namespace);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT NOT NULL,
    inverse_label TEXT,
    namespace TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_relations_label ON relations(label);

CREATE TABLE IF NOT EXISTS statements (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    relation_id TEXT NOT NULL,
    object_id TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    namespace TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retracted_at TEXT,
    retraction_reason TEXT,
    superseded_by TEXT,
    valid_from TEXT,
    valid_until TEXT,
    epistemic_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_statements_subject ON statements(subject_id);
CREATE INDEX IF NOT EXISTS idx_statements_object ON statements(object_id);
CREATE INDEX IF NOT EXISTS idx_statements_relation ON statements(relation_id);
CREATE INDEX IF NOT EXISTS idx_statements_status ON statements(status);
CREATE INDEX IF NOT EXISTS idx_statements_namespace ON statements(namespace);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    namespace TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_id TEXT,
    reason TEXT,
    metadata_json TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_target ON events(target_id);
CREATE INDEX IF NOT EXISTS idx_events_namespace ON events(namespace);
"""
