from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.auth.models import UserPublic
from app.auth.passwords import hash_password, verify_password
from app.cases.constants import SCHEMA_VERSION, CaseSeverity, CaseStatus, TimelineKind
from app.cases.models import (
    CaseCreate,
    CaseDetail,
    CaseListParams,
    CaseSummary,
    CaseUpdate,
    TimelineEntry,
)
from app.cases.schema import DDL_INITIAL


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw: Optional[str], default: Any) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


class CaseStoreError(Exception):
    """Raised for constraint violations or missing rows."""


class CaseStore:
    """SQLite persistence for investigation cases and timeline entries."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables and metadata if missing.

        Runs the full DDL script only when ``cases_meta`` is absent (brand-new DB).
        Existing databases rely on ``schema_version`` in ``cases_meta`` and forward
        migrations so we never re-apply ``CREATE INDEX`` against legacy tables.
        """

        with self._connect() as conn:
            has_meta = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cases_meta'",
            ).fetchone()
            if has_meta is None:
                conn.executescript(DDL_INITIAL)
            row = conn.execute(
                "SELECT value FROM cases_meta WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO cases_meta (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION)),
                )
            else:
                current = int(row["value"])
                if current < SCHEMA_VERSION:
                    self._migrate(conn, current)

    def _migrate(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Apply forward migrations from from_version to SCHEMA_VERSION."""

        if from_version < 1:
            raise CaseStoreError(f"Unsupported schema version {from_version}")
        if from_version < 2:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                """
            )
            cols = {col[1] for col in conn.execute("PRAGMA table_info(cases)").fetchall()}
            if "user_id" not in cols:
                conn.execute("ALTER TABLE cases ADD COLUMN user_id TEXT REFERENCES users(id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cases_user_updated ON cases (user_id, updated_at DESC)"
            )
        conn.execute(
            "UPDATE cases_meta SET value = ? WHERE key = ?",
            (str(SCHEMA_VERSION), "schema_version"),
        )

    def create_user(
        self,
        username: str,
        password_plain: str,
        display_name: Optional[str] = None,
    ) -> UserPublic:
        uid = uuid.uuid4().hex
        now = _utc_now_iso()
        uname = username.strip().lower()
        disp = display_name.strip() if display_name and display_name.strip() else None
        ph = hash_password(password_plain)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (id, username, password_hash, display_name, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (uid, uname, ph, disp, now),
                )
        except sqlite3.IntegrityError as e:
            raise CaseStoreError("username already registered") from e
        u = self.get_user_public(uid)
        assert u is not None
        return u

    def get_user_public(self, user_id: str) -> Optional[UserPublic]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, display_name, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None or not int(row["is_active"]):
            return None
        return UserPublic(
            id=str(row["id"]),
            username=str(row["username"]),
            display_name=row["display_name"],
        )

    def authenticate_user(self, username: str, password_plain: str) -> Optional[UserPublic]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, username, display_name, password_hash, is_active
                FROM users
                WHERE lower(username) = lower(?)
                """,
                (username.strip(),),
            ).fetchone()
        if row is None or not int(row["is_active"]):
            return None
        if not verify_password(password_plain, str(row["password_hash"])):
            return None
        return UserPublic(
            id=str(row["id"]),
            username=str(row["username"]),
            display_name=row["display_name"],
        )

    def create_case(self, data: CaseCreate, user_id: Optional[str] = None) -> CaseDetail:
        case_id = uuid.uuid4().hex
        now = _utc_now_iso()
        tags = _json_dumps(list(data.tags))
        ext = _json_dumps(dict(data.external_refs)) if data.external_refs else None

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cases (
                    id, title, status, severity, owner, user_id, tags_json, summary,
                    external_refs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    data.title.strip(),
                    data.status.value,
                    data.severity.value if data.severity else None,
                    data.owner.strip() if data.owner else None,
                    user_id,
                    tags,
                    data.summary,
                    ext,
                    now,
                    now,
                ),
            )

        detail = self.get_case(case_id)
        assert detail is not None
        return detail

    def get_case(self, case_id: str, timeline_limit: int = 2000) -> Optional[CaseDetail]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM cases WHERE id = ?",
                (case_id,),
            ).fetchone()
            if row is None:
                return None
            trows = conn.execute(
                """
                SELECT * FROM case_timeline
                WHERE case_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (case_id, timeline_limit),
            ).fetchall()

        return self._row_to_detail(row, trows)

    def _row_to_detail(
        self,
        row: sqlite3.Row,
        timeline_rows: List[sqlite3.Row],
    ) -> CaseDetail:
        tags = _json_loads(row["tags_json"], [])
        if not isinstance(tags, list):
            tags = []
        ext = _json_loads(row["external_refs_json"], {})
        if not isinstance(ext, dict):
            ext = {}
        timeline: List[TimelineEntry] = []
        for tr in timeline_rows:
            payload_raw = tr["payload_json"]
            payload: Optional[Dict[str, Any]] = None
            if payload_raw:
                p = _json_loads(payload_raw, None)
                if isinstance(p, dict):
                    payload = p
            timeline.append(
                TimelineEntry(
                    id=int(tr["id"]),
                    case_id=str(tr["case_id"]),
                    kind=TimelineKind(str(tr["kind"])),
                    title=tr["title"],
                    body=tr["body"],
                    payload=payload,
                    created_at=str(tr["created_at"]),
                )
            )

        sev = row["severity"]
        uid = row["user_id"] if "user_id" in row.keys() else None
        return CaseDetail(
            id=str(row["id"]),
            title=str(row["title"]),
            status=CaseStatus(str(row["status"])),
            severity=CaseSeverity(str(sev)) if sev else None,
            owner=row["owner"],
            user_id=str(uid) if uid else None,
            tags=[str(t) for t in tags],
            summary=row["summary"],
            external_refs={str(k): str(v) for k, v in ext.items()},
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            timeline=timeline,
        )

    def list_cases(self, params: CaseListParams) -> List[CaseSummary]:
        where: List[str] = ["1=1"]
        bind: List[Any] = []
        if params.status is not None:
            where.append("c.status = ?")
            bind.append(params.status.value)
        if params.owner is not None:
            where.append("c.owner = ?")
            bind.append(params.owner.strip())
        if params.title_contains:
            where.append("c.title LIKE ?")
            bind.append(f"%{params.title_contains.strip()}%")
        if params.user_id is not None:
            where.append("c.user_id = ?")
            bind.append(params.user_id)

        sql = f"""
            SELECT
                c.*,
                (SELECT COUNT(*) FROM case_timeline t WHERE t.case_id = c.id) AS timeline_count
            FROM cases c
            WHERE {' AND '.join(where)}
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
        """
        bind.extend([params.limit, params.offset])

        with self._connect() as conn:
            rows = conn.execute(sql, bind).fetchall()

        out: List[CaseSummary] = []
        for row in rows:
            tags = _json_loads(row["tags_json"], [])
            if not isinstance(tags, list):
                tags = []
            sev = row["severity"]
            uid = row["user_id"] if "user_id" in row.keys() else None
            out.append(
                CaseSummary(
                    id=str(row["id"]),
                    title=str(row["title"]),
                    status=CaseStatus(str(row["status"])),
                    severity=CaseSeverity(str(sev)) if sev else None,
                    owner=row["owner"],
                    user_id=str(uid) if uid else None,
                    tags=[str(t) for t in tags],
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                    timeline_count=int(row["timeline_count"] or 0),
                )
            )
        return out

    def update_case(self, case_id: str, data: CaseUpdate) -> CaseDetail:
        existing = self.get_case(case_id, timeline_limit=1)
        if existing is None:
            raise CaseStoreError(f"case not found: {case_id}")

        fields: Dict[str, Any] = {}
        if data.title is not None:
            fields["title"] = data.title.strip()
        if data.status is not None:
            fields["status"] = data.status.value
        if data.severity is not None:
            fields["severity"] = data.severity.value
        if data.owner is not None:
            fields["owner"] = data.owner.strip() if data.owner else None
        if data.tags is not None:
            fields["tags_json"] = _json_dumps(list(data.tags))
        if data.summary is not None:
            fields["summary"] = data.summary
        if data.external_refs is not None:
            fields["external_refs_json"] = _json_dumps(dict(data.external_refs))

        if not fields:
            full = self.get_case(case_id)
            assert full is not None
            return full

        fields["updated_at"] = _utc_now_iso()
        if data.status is not None and data.status != existing.status:
            self.add_timeline(
                case_id,
                kind=TimelineKind.STATUS_CHANGE,
                title=f"Status {existing.status.value} → {data.status.value}",
                body=None,
                payload={"from": existing.status.value, "to": data.status.value},
            )

        assignments = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [case_id]

        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE cases SET {assignments} WHERE id = ?",
                values,
            )
            if cur.rowcount != 1:
                raise CaseStoreError(f"case not found: {case_id}")

        full = self.get_case(case_id)
        assert full is not None
        return full

    def add_timeline(
        self,
        case_id: str,
        *,
        kind: TimelineKind,
        title: Optional[str] = None,
        body: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TimelineEntry:
        now = _utc_now_iso()
        payload_json = _json_dumps(payload) if payload is not None else None

        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM cases WHERE id = ?",
                (case_id,),
            ).fetchone()
            if exists is None:
                raise CaseStoreError(f"case not found: {case_id}")
            cur = conn.execute(
                """
                INSERT INTO case_timeline (case_id, kind, title, body, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (case_id, kind.value, title, body, payload_json, now),
            )
            conn.execute(
                "UPDATE cases SET updated_at = ? WHERE id = ?",
                (now, case_id),
            )
            new_id = int(cur.lastrowid)

        return TimelineEntry(
            id=new_id,
            case_id=case_id,
            kind=kind,
            title=title,
            body=body,
            payload=payload,
            created_at=now,
        )

    def delete_case(self, case_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            return cur.rowcount == 1

    def case_exists(self, case_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM cases WHERE id = ?",
                (case_id,),
            ).fetchone()
            return row is not None
