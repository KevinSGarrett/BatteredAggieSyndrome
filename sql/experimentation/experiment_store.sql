-- Wave 18 local-first canonical experiment metadata reference schema.
-- This schema intentionally stores metadata/evidence only.  Large training matrices,
-- model binaries, checkpoints, and raw data remain outside the cumulative repository.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS experiment_specs (
    experiment_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    spec_sha256 TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS queue_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL REFERENCES experiment_specs(experiment_id),
    event_index INTEGER NOT NULL,
    state TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE,
    previous_event_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(experiment_id, event_index)
);

CREATE TABLE IF NOT EXISTS result_packets (
    result_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiment_specs(experiment_id),
    attempt INTEGER NOT NULL CHECK(attempt >= 1),
    payload_json TEXT NOT NULL,
    result_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(experiment_id, attempt)
);

CREATE TABLE IF NOT EXISTS artifact_records (
    artifact_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiment_specs(experiment_id),
    attempt INTEGER NOT NULL CHECK(attempt >= 1),
    class_name TEXT NOT NULL,
    uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
    sensitivity TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replay_reports (
    replay_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiment_specs(experiment_id),
    source_result_id TEXT NOT NULL REFERENCES result_packets(result_id),
    payload_json TEXT NOT NULL,
    replay_sha256 TEXT NOT NULL,
    replay_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queue_events_experiment
ON queue_events(experiment_id, event_index);

CREATE INDEX IF NOT EXISTS idx_result_packets_experiment
ON result_packets(experiment_id, attempt);

CREATE INDEX IF NOT EXISTS idx_artifact_records_experiment
ON artifact_records(experiment_id, attempt);
