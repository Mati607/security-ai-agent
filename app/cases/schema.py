from __future__ import annotations

from app.cases.constants import SCHEMA_VERSION

# Single-file SQLite schema for investigation cases. Migrations bump SCHEMA_VERSION
# and append conditional DDL in CaseStore._migrate.

DDL_INITIAL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases_meta (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    severity TEXT,
    owner TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    summary TEXT,
    external_refs_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_status_updated
    ON cases (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_owner_updated
    ON cases (owner, updated_at DESC);

CREATE TABLE IF NOT EXISTS case_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT,
    body TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timeline_case_time
    ON case_timeline (case_id, created_at ASC);
"""


def expected_meta_rows() -> list[tuple[str, str]]:
    return [("schema_version", str(SCHEMA_VERSION))]
