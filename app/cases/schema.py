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

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY NOT NULL,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    severity TEXT,
    owner TEXT,
    user_id TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    summary TEXT,
    external_refs_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_status_updated
    ON cases (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_owner_updated
    ON cases (owner, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_cases_user_updated
    ON cases (user_id, updated_at DESC);

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
