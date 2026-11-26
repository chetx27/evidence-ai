from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from evidenceai.ids import sha256_bytes
from evidenceai.store import one, rows

_LATEST = """
NOT EXISTS (
  SELECT 1 FROM supersessions s
  WHERE s.older_document_version_id = v.document_version_id
)
"""


def object_text(db_path: Path, content_hash: str) -> str:
    path = db_path.parent / "objects" / content_hash
    data = path.read_bytes()
    if sha256_bytes(data) != content_hash:
        raise RuntimeError("content_hash_mismatch")
    return data.decode("utf-8")


def artifact(conn: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    row = one(conn, "SELECT * FROM artifacts WHERE name = ?", (name,))
    if row is None:
        return None
    row["body"] = json.loads(row["body_json"])
    return row


def latest_versions(
    conn: sqlite3.Connection,
    trial_id: str | None = None,
) -> list[dict[str, Any]]:
    sql = f"""
        SELECT v.*, d.external_key
        FROM document_versions v
        JOIN documents d ON d.document_id = v.document_id
        WHERE {_LATEST}
    """
    params: list[Any] = []
    if trial_id is not None:
        sql += " AND v.trial_id = ?"
        params.append(trial_id)
    sql += " ORDER BY d.external_key"
    return rows(conn, sql, tuple(params))


def latest_claims(
    conn: sqlite3.Connection,
    trial_id: str | None = None,
    predicate: str | None = None,
    assertion_time_lte: str | None = None,
) -> list[dict[str, Any]]:
    sql = f"""
        SELECT c.*, d.external_key, v.doc_type, v.content_hash, v.language
        FROM claims c
        JOIN document_versions v ON v.document_version_id = c.document_version_id
        JOIN documents d ON d.document_id = c.document_id
        WHERE {_LATEST}
    """
    params: list[Any] = []
    if trial_id is not None:
        sql += " AND c.trial_id = ?"
        params.append(trial_id)
    if predicate is not None:
        sql += " AND c.predicate = ?"
        params.append(predicate)
    if assertion_time_lte is not None:
        sql += " AND c.assertion_time IS NOT NULL AND c.assertion_time <= ?"
        params.append(assertion_time_lte)
    sql += " ORDER BY c.claim_id"
    return rows(conn, sql, tuple(params))


def span(conn: sqlite3.Connection, span_id: str) -> dict[str, Any] | None:
    return one(conn, "SELECT * FROM spans WHERE span_id = ?", (span_id,))


def spans_for_version(conn: sqlite3.Connection, document_version_id: str) -> list[dict[str, Any]]:
    return rows(
        conn,
        "SELECT * FROM spans WHERE document_version_id = ? ORDER BY char_start, span_id",
        (document_version_id,),
    )


def claims_for_version(conn: sqlite3.Connection, document_version_id: str) -> list[dict[str, Any]]:
    return rows(
        conn,
        """
        SELECT c.*
        FROM claims c
        JOIN spans s ON s.span_id = c.span_id
        WHERE c.document_version_id = ?
        ORDER BY s.char_start, c.claim_id
        """,
        (document_version_id,),
    )


def assessments_for_claims(
    conn: sqlite3.Connection,
    claim_ids: list[str],
    method: str,
) -> list[dict[str, Any]]:
    if not claim_ids:
        return []
    placeholders = ", ".join("?" for _ in claim_ids)
    sql = f"""
        SELECT * FROM pair_assessments
        WHERE method = ?
          AND claim_id_a IN ({placeholders})
          AND claim_id_b IN ({placeholders})
        ORDER BY assessment_id
    """
    params = (method, *claim_ids, *claim_ids)
    return rows(conn, sql, params)


def rule_conflicts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return rows(
        conn,
        """
        SELECT a.*,
               cl.trial_id, cl.predicate, cl.raw_token AS raw_token_a,
               cl.canonical_value AS canonical_a,
               cr.raw_token AS raw_token_b, cr.canonical_value AS canonical_b
        FROM pair_assessments a
        JOIN claims cl ON cl.claim_id = a.claim_id_a
        JOIN claims cr ON cr.claim_id = a.claim_id_b
        WHERE a.method = 'numeric_rule_v0' AND a.predicted_incompatible = 1
        ORDER BY a.assessment_id
        """,
    )


def assessment(conn: sqlite3.Connection, assessment_id: str) -> dict[str, Any] | None:
    return one(conn, "SELECT * FROM pair_assessments WHERE assessment_id = ?", (assessment_id,))


def claim(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any] | None:
    return one(
        conn,
        """
        SELECT c.*, d.external_key, v.content_hash, v.doc_type
        FROM claims c
        JOIN documents d ON d.document_id = c.document_id
        JOIN document_versions v ON v.document_version_id = c.document_version_id
        WHERE c.claim_id = ?
        """,
        (claim_id,),
    )


def version_by_id(conn: sqlite3.Connection, document_version_id: str) -> dict[str, Any] | None:
    return one(
        conn,
        """
        SELECT v.*, d.external_key
        FROM document_versions v
        JOIN documents d ON d.document_id = v.document_id
        WHERE v.document_version_id = ?
        """,
        (document_version_id,),
    )


def document_latest(conn: sqlite3.Connection, document_id: str) -> dict[str, Any] | None:
    return one(
        conn,
        f"""
        SELECT v.*, d.external_key
        FROM document_versions v
        JOIN documents d ON d.document_id = v.document_id
        WHERE d.document_id = ? AND {_LATEST}
        """,
        (document_id,),
    )


def stored_answer(conn: sqlite3.Connection, question: str) -> dict[str, Any] | None:
    row = one(conn, "SELECT * FROM answers WHERE question = ?", (question,))
    if row is None:
        return None
    row["body"] = json.loads(row["body_json"])
    return row


def stored_answer_by_id(conn: sqlite3.Connection, answer_id: str) -> dict[str, Any] | None:
    row = one(conn, "SELECT * FROM answers WHERE answer_id = ?", (answer_id,))
    if row is None:
        return None
    row["body"] = json.loads(row["body_json"])
    return row


def completion(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    row = one(conn, "SELECT * FROM pipeline_run_completions WHERE run_id = ?", (run_id,))
    if row is None:
        return None
    row["counts"] = json.loads(row["counts_json"])
    return row


def run_row(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    return one(conn, "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
