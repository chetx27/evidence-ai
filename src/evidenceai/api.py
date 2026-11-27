from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from evidenceai import __version__
from evidenceai.confidence import compose
from evidenceai.constants import RULE_METHOD, SCHEMA_VERSION
from evidenceai.evaluation import evaluate
from evidenceai.investigate import build_answer
from evidenceai.readmodel import (
    artifact,
    assessment,
    claim,
    completion,
    document_latest,
    latest_versions,
    object_text,
    rule_conflicts,
    run_row,
    spans_for_version,
    stored_answer,
    stored_answer_by_id,
)
from evidenceai.readmodel import (
    span as load_span,
)
from evidenceai.store import Database, rows

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class InvestigateBody(BaseModel):
    question: str = Field(min_length=1)
    assertion_time_lte: Optional[str] = None


def bind_is_allowed(host: str, allow_remote: bool) -> bool:
    return allow_remote or host in LOOPBACK_HOSTS


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="EvidenceAI", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def open_db() -> Database:
        if not Path(db_path).exists():
            raise HTTPException(status_code=503, detail="slice_database_missing")
        return Database(db_path, readonly=True)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        ready = Path(db_path).exists()
        return {
            "status": "ok",
            "version": __version__,
            "schema_version": SCHEMA_VERSION,
            "database": "ready" if ready else "missing",
        }

    @app.get("/api/case")
    def case() -> dict[str, Any]:
        db = open_db()
        try:
            stored = artifact(db.conn, "case")
            if stored is None:
                raise HTTPException(status_code=503, detail="case_artifact_missing")
            body = stored["body"]
            run = run_row(db.conn, "run_ebsynth_v0_20261126")
            done = completion(db.conn, "run_ebsynth_v0_20261126")
            conflicts = rule_conflicts(db.conn)
            return {
                "case_id": body["case_id"],
                "corpus_label": body["corpus_label"],
                "disclaimer": body["disclaimer"],
                "standing_disclaimer": body["standing_disclaimer"],
                "pack_id": body["pack_id"],
                "pack_version": body["pack_version"],
                "schema_version": body["schema_version"],
                "extractor_id": body["extractor_id"],
                "preregistration_id": body["preregistration_id"],
                "registered_questions": body["registered_questions"],
                "counts": done["counts"] if done else None,
                "run_status": done["status"] if done else "not_completed",
                "duration_seconds": done["duration_seconds"] if done else None,
                "triage_conflicts": len(conflicts),
                "seed": run["seed"] if run else None,
            }
        finally:
            db.close()

    @app.get("/api/documents")
    def documents() -> dict[str, Any]:
        db = open_db()
        try:
            items = []
            for version in latest_versions(db.conn):
                items.append(_document_summary(version))
            return {"documents": items}
        finally:
            db.close()

    @app.get("/api/documents/{document_id}")
    def document_detail(document_id: str) -> dict[str, Any]:
        db = open_db()
        try:
            version = document_latest(db.conn, document_id)
            if version is None:
                raise HTTPException(status_code=404, detail="document_not_found")
            try:
                text = object_text(db.path, version["content_hash"])
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            span_rows = spans_for_version(db.conn, version["document_version_id"])
            claim_rows = rows(
                db.conn,
                """
                SELECT c.* FROM claims c
                WHERE c.document_version_id = ?
                ORDER BY c.claim_id
                """,
                (version["document_version_id"],),
            )
            return {
                **_document_summary(version),
                "text": text,
                "page": None,
                "page_note": "text/plain has no pages. Highlights use character offsets.",
                "bounding_box": None,
                "spans": [_span_public(row) for row in span_rows],
                "claims": [_claim_public(row) for row in claim_rows],
            }
        finally:
            db.close()

    @app.get("/api/contradictions")
    def contradictions() -> dict[str, Any]:
        db = open_db()
        try:
            items = []
            for row in rule_conflicts(db.conn):
                items.append(
                    {
                        "assessment_id": row["assessment_id"],
                        "trial_id": row["trial_id"],
                        "predicate": row["predicate"],
                        "subtype": row["subtype"],
                        "raw_token_a": row["raw_token_a"],
                        "raw_token_b": row["raw_token_b"],
                        "canonical_a": row["canonical_a"],
                        "canonical_b": row["canonical_b"],
                        "abs_difference": row["abs_difference"],
                        "tolerance": row["tolerance"],
                        "rationale": row["rationale"],
                    }
                )
            return {
                "method": RULE_METHOD,
                "note": (
                    "Triage lists pairs the numeric rule classified as incompatible_values. "
                    "Resolved scale and rounding pairs are excluded. "
                    "No source is selected as correct."
                ),
                "contradictions": items,
            }
        finally:
            db.close()

    @app.get("/api/contradictions/{assessment_id}")
    def contradiction_detail(assessment_id: str) -> dict[str, Any]:
        db = open_db()
        try:
            row = assessment(db.conn, assessment_id)
            if row is None or row["method"] != RULE_METHOD:
                raise HTTPException(status_code=404, detail="contradiction_not_found")
            if row["predicted_incompatible"] != 1:
                raise HTTPException(status_code=404, detail="contradiction_not_in_triage")
            return {
                "assessment_id": row["assessment_id"],
                "method": row["method"],
                "subtype": row["subtype"],
                "rationale": row["rationale"],
                "abs_difference": row["abs_difference"],
                "tolerance": row["tolerance"],
                "valid_time_relation": row["valid_time_relation"],
                "left": _side(db, row["claim_id_a"]),
                "right": _side(db, row["claim_id_b"]),
            }
        finally:
            db.close()

    @app.post("/api/investigate")
    def investigate(body: InvestigateBody) -> dict[str, Any]:
        if body.assertion_time_lte is not None and _DATE.match(body.assertion_time_lte) is None:
            raise HTTPException(status_code=400, detail="assertion_time_lte_must_be_iso_date")
        db = open_db()
        try:
            existing = stored_answer(db.conn, body.question)
            persisted = existing is not None and body.assertion_time_lte is None
            return build_answer(
                db.conn,
                body.question,
                assertion_time_lte=body.assertion_time_lte,
                persisted=persisted,
            )
        finally:
            db.close()

    @app.get("/api/evaluation")
    def evaluation() -> dict[str, Any]:
        db = open_db()
        try:
            return evaluate(db)
        finally:
            db.close()

    @app.get("/api/answers/{answer_id}/receipt")
    def receipt(answer_id: str) -> dict[str, Any]:
        db = open_db()
        try:
            row = stored_answer_by_id(db.conn, answer_id)
            if row is None:
                raise HTTPException(status_code=404, detail="answer_not_in_event_log")
            body = row["body"]
            return {
                "type": "EvidenceReceipt",
                "schema_version": SCHEMA_VERSION,
                "signature": None,
                "signature_note": "Unsigned. A signature scheme is not implemented.",
                "vocabulary_note": (
                    "Field names are aligned with W3C PROV concepts. "
                    "This is not a registered JSON-LD vocabulary."
                ),
                "answer_id": body["answer_id"],
                "question": body["question"],
                "state": body["state"],
                "method": body["method"],
                "quotations": body.get("quotations", []),
                "limitations": body.get("limitations", []),
            }
        finally:
            db.close()

    return app


def _document_summary(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": version["document_id"],
        "document_version_id": version["document_version_id"],
        "external_key": version["external_key"],
        "doc_type": version["doc_type"],
        "trial_id": version["trial_id"],
        "language": version["language"],
        "language_uncertainty": version["language_uncertainty"],
        "document_date": version["document_date"],
        "document_date_uncertainty": version["document_date_uncertainty"],
        "content_hash": version["content_hash"],
        "byte_length": version["byte_length"],
        "media_type": version["media_type"],
        "parse_quality": version["parse_quality"],
        "parse_quality_note": version["parse_quality_note"],
        "warnings": json.loads(version["warnings_json"]),
        "limitations": json.loads(version["limitations_json"]),
    }


def _span_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "span_id": row["span_id"],
        "char_start": row["char_start"],
        "char_end": row["char_end"],
        "text": row["text"],
        "role": row["role"],
        "boilerplate": bool(row["boilerplate"]),
        "page": row["page"],
        "bbox": None,
    }


def _claim_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": row["claim_id"],
        "predicate": row["predicate"],
        "trial_id": row["trial_id"],
        "raw_token": row["raw_token"],
        "canonical_value": row["canonical_value"],
        "dimension": row["dimension"],
        "unit_kind": row["unit_kind"],
        "span_id": row["span_id"],
        "assertion_time": row["assertion_time"],
        "valid_time_start": row["valid_time_start"],
        "valid_time_end": row["valid_time_end"],
        "valid_time_uncertainty": row["valid_time_uncertainty"],
        "modality": row["modality"],
        "polarity": row["polarity"],
        "hedging": row["hedging"],
        "extractor_id": row["extractor_id"],
        "frame_id": row["frame_id"],
        "confidence": compose(row),
        "extraction_note": row["extraction_note"],
    }


def _side(db: Database, claim_id: str) -> dict[str, Any]:
    row = claim(db.conn, claim_id)
    if row is None:
        raise HTTPException(status_code=500, detail="claim_missing_for_assessment")
    evidence = load_span(db.conn, row["span_id"])
    if evidence is None:
        raise HTTPException(status_code=500, detail="span_missing_for_claim")
    return {
        "claim_id": row["claim_id"],
        "document_id": row["document_id"],
        "external_key": row["external_key"],
        "doc_type": row["doc_type"],
        "content_hash": row["content_hash"],
        "predicate": row["predicate"],
        "raw_token": row["raw_token"],
        "canonical_value": row["canonical_value"],
        "char_start": evidence["char_start"],
        "char_end": evidence["char_end"],
        "span_text": evidence["text"],
        "confidence": compose(row),
    }
