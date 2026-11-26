from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from evidenceai.constants import (
    CASE_ID,
    EXTRACTOR_ID,
    EXTRACTOR_VERSION,
    GENERATOR_ID,
    GENERATOR_VERSION,
    MAX_BYTES,
    REGISTERED_SEED,
    RUN_ID,
    SCHEMA_VERSION,
    STANDING_DISCLAIMER,
    SYNTHETIC_BANNER,
)
from evidenceai.frames import assert_frames_match_pack
from evidenceai.ids import canonical_json, stable_id
from evidenceai.ingest import ingest_file, iter_corpus_files
from evidenceai.investigate import answer_id_for, build_answer
from evidenceai.materialize import materialize_assessments, materialize_extractions
from evidenceai.pack import load_pack
from evidenceai.prereg import load_prereg, registered_questions
from evidenceai.store import Database
from evidenceai.synth import generate_corpus


class RegistrationDeviation(ValueError):
    """The run would label the fixed fixture with a seed it does not use."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_slice(
    out_dir: Path,
    seed: int = REGISTERED_SEED,
    system_time: str | None = None,
    byte_limit: int = MAX_BYTES,
) -> dict[str, Any]:
    if seed != REGISTERED_SEED:
        raise RegistrationDeviation(
            "EB-Synth v0 is specification-fixed to seed "
            f"{REGISTERED_SEED}. Refusing seed {seed}."
        )
    assert_frames_match_pack()
    system_time = system_time or utc_now()
    started = perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_dir = out_dir / "corpus"
    object_root = out_dir / "objects"
    manifest = generate_corpus(corpus_dir)
    (out_dir / "manifest.json").write_text(
        canonical_json(manifest) + "\n",
        encoding="utf-8",
    )
    db_path = out_dir / "evidence.db"
    db = Database(db_path)
    try:
        prereg = load_prereg()
        pack = load_pack()
        db.append(
            "pipeline_run_started",
            RUN_ID,
            {
                "run_id": RUN_ID,
                "started_at": system_time,
                "seed": seed,
                "generator_id": GENERATOR_ID,
                "generator_version": GENERATOR_VERSION,
                "schema_version": SCHEMA_VERSION,
                "extractor_id": EXTRACTOR_ID,
                "extractor_version": EXTRACTOR_VERSION,
                "pack_id": pack["pack_id"],
                "pack_version": pack["version"],
                "preregistration_id": prereg["id"],
            },
            RUN_ID,
            system_time,
        )
        for path in iter_corpus_files(corpus_dir):
            ingest_file(db, corpus_dir, path, object_root, RUN_ID, system_time, byte_limit)
        materialize_extractions(db, RUN_ID, system_time)
        materialize_assessments(db, RUN_ID, system_time)
        _store_artifact(db, "eb_synth_manifest", manifest, system_time)
        _store_artifact(
            db,
            "case",
            {
                "case_id": CASE_ID,
                "corpus_label": "synthetic",
                "disclaimer": SYNTHETIC_BANNER,
                "standing_disclaimer": STANDING_DISCLAIMER,
                "pack_id": pack["pack_id"],
                "pack_version": pack["version"],
                "preregistration_id": prereg["id"],
                "registered_questions": registered_questions(),
                "schema_version": SCHEMA_VERSION,
                "extractor_id": EXTRACTOR_ID,
                "extractor_version": EXTRACTOR_VERSION,
            },
            system_time,
        )
        for question in registered_questions():
            body = build_answer(db.conn, question, persisted=True)
            db.append(
                "answer_recorded",
                answer_id_for(question),
                {
                    "answer_id": body["answer_id"],
                    "question": question,
                    "state": body["state"],
                    "persisted": 1,
                    "system_time": system_time,
                    "method": body["method"],
                    "body_json": canonical_json(body),
                },
                RUN_ID,
                system_time,
            )
        counts = _counts(db)
        elapsed = perf_counter() - started
        duration = f"{elapsed:.6f}"
        db.append(
            "pipeline_run_completed",
            RUN_ID + ":completed",
            {
                "run_id": RUN_ID,
                "finished_at": system_time,
                "status": "completed",
                "duration_seconds": duration,
                "counts_json": canonical_json(counts),
            },
            RUN_ID,
            system_time,
        )
        db.commit()
        event_count = db.conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return {
        "db_path": db_path,
        "out_dir": out_dir,
        "run_id": RUN_ID,
        "event_count": int(event_count),
        "counts": counts,
        "duration_seconds": duration,
    }


def _store_artifact(db: Database, name: str, body: dict[str, Any], system_time: str) -> None:
    artifact_id = stable_id("art", name)
    db.append(
        "artifact_recorded",
        artifact_id,
        {
            "artifact_id": artifact_id,
            "name": name,
            "media_type": "application/json",
            "body_json": canonical_json(body),
            "system_time": system_time,
        },
        RUN_ID,
        system_time,
    )


def _counts(db: Database) -> dict[str, int]:
    def count(sql: str) -> int:
        return int(db.conn.execute(sql).fetchone()[0])

    return {
        "documents": count("SELECT COUNT(*) FROM documents"),
        "document_versions": count("SELECT COUNT(*) FROM document_versions"),
        "claims": count("SELECT COUNT(*) FROM claims"),
        "spans": count("SELECT COUNT(*) FROM spans"),
        "pair_assessments": count("SELECT COUNT(*) FROM pair_assessments"),
        "answers": count("SELECT COUNT(*) FROM answers"),
        "quarantined_files": count(
            "SELECT COUNT(*) FROM file_observations WHERE status = 'quarantined'"
        ),
        "exact_duplicates": count(
            "SELECT COUNT(*) FROM file_observations WHERE status = 'exact_duplicate'"
        ),
    }
