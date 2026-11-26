from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from evidenceai.constants import SCHEMA_VERSION
from evidenceai.ids import canonical_json, stable_id
from evidenceai.paths import repo_root

PROJECTION_TABLES = (
    "pipeline_run_completions",
    "pair_assessments",
    "answers",
    "artifacts",
    "claims",
    "spans",
    "entities",
    "lineage_edges",
    "file_observations",
    "supersessions",
    "document_versions",
    "documents",
    "sources",
    "pipeline_runs",
)

EVENT_TABLE = {
    "pipeline_run_started": "pipeline_runs",
    "pipeline_run_completed": "pipeline_run_completions",
    "source_registered": "sources",
    "document_recorded": "documents",
    "document_version_recorded": "document_versions",
    "supersession_recorded": "supersessions",
    "file_observed": "file_observations",
    "lineage_recorded": "lineage_edges",
    "span_recorded": "spans",
    "entity_recorded": "entities",
    "claim_recorded": "claims",
    "pair_assessed": "pair_assessments",
    "answer_recorded": "answers",
    "artifact_recorded": "artifacts",
}


def insert_row(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> None:
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    names = ", ".join(columns)
    conn.execute(
        f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
        [row[column] for column in columns],
    )


def project(conn: sqlite3.Connection, event_type: str, payload: dict[str, Any]) -> None:
    table = EVENT_TABLE.get(event_type)
    if table is None:
        raise RuntimeError(f"Unknown event type: {event_type}")
    insert_row(conn, table, payload)


class Database:
    def __init__(self, path: Path, readonly: bool = False) -> None:
        self.path = Path(path)
        if readonly:
            if not self.path.exists():
                raise FileNotFoundError(self.path)
            uri = self.path.resolve().as_uri() + "?mode=ro"
            self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path, check_same_thread=False)
            script = (repo_root() / "schemas" / "sql" / "001_init.sql").read_text(encoding="utf-8")
            self.conn.executescript(script)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    def append(
        self,
        event_type: str,
        object_id: str,
        payload: dict[str, Any],
        correlation_id: str,
        system_time: str,
    ) -> bool:
        event_id = stable_id("ev", event_type, object_id)
        existing = self.conn.execute(
            "SELECT 1 FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if existing:
            return False
        self.conn.execute(
            """
            INSERT INTO events (
              event_id, event_type, system_time, schema_version,
              correlation_id, object_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                system_time,
                SCHEMA_VERSION,
                correlation_id,
                object_id,
                canonical_json(payload),
            ),
        )
        project(self.conn, event_type, payload)
        return True

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def rebuild(self) -> None:
        self.conn.execute("PRAGMA foreign_keys = OFF")
        for table in PROJECTION_TABLES:
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.execute("PRAGMA foreign_keys = ON")
        rows = self.conn.execute(
            "SELECT event_type, payload_json FROM events ORDER BY rowid"
        ).fetchall()
        for row in rows:
            project(self.conn, row["event_type"], json.loads(row["payload_json"]))
        self.conn.commit()


def rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    found = conn.execute(sql, params).fetchone()
    if found is None:
        return None
    return dict(found)
