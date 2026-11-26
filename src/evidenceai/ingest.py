from __future__ import annotations

import re
from pathlib import Path

from evidenceai.constants import (
    PARSER_ID,
    PARSER_VERSION,
    PROBABILITY_NOTE,
    RELIABILITY_NOTE,
)
from evidenceai.ids import sha256_bytes, stable_id
from evidenceai.store import Database, one

_FIELDS = {
    "language": re.compile(r"^Language: (?P<value>[a-z]{2})$"),
    "doc_type": re.compile(r"^Document type: (?P<value>[a-z_]+)$"),
    "trial_id": re.compile(r"^Trial: (?P<value>SYNTH-\d{3})$"),
    "document_date": re.compile(r"^Document date: (?P<value>\d{4}-\d{2}-\d{2})$"),
    "source": re.compile(r"^Source: (?P<value>\S(?:.*\S)?)$"),
    "compound": re.compile(r"^Compound: (?P<value>\S(?:.*\S)?)$"),
    "indication": re.compile(r"^Indication: (?P<value>\S(?:.*\S)?)$"),
}
_PREFIXES = {
    "Language: ": "language",
    "Document type: ": "doc_type",
    "Trial: ": "trial_id",
    "Document date: ": "document_date",
    "Source: ": "source",
    "Compound: ": "compound",
    "Indication: ": "indication",
}


class UnsafePath(ValueError):
    pass


def assert_inside(root: Path, path: Path) -> Path:
    root_resolved = root.resolve()
    resolved = path.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise UnsafePath(f"{path} resolves outside {root}")
    return resolved


def iter_corpus_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            assert_inside(root, path)
            files.append(path)
    return files


def parse_metadata(text: str) -> tuple[dict[str, str], list[str]]:
    found: dict[str, str] = {}
    warnings: list[str] = []
    for line in text.splitlines():
        prefix_name = None
        for prefix, name in _PREFIXES.items():
            if line.startswith(prefix):
                prefix_name = name
                break
        if prefix_name is None:
            continue
        match = _FIELDS[prefix_name].match(line)
        if match is None:
            warnings.append(f"malformed_{prefix_name}")
            continue
        found[prefix_name] = match.group("value")
    return found, warnings


def _limitations() -> list[str]:
    return [
        "bounding_box_unavailable",
        "page_not_applicable",
        "ocr_not_applicable",
        "parse_quality_not_measured",
    ]


def ingest_file(
    db: Database,
    corpus_root: Path,
    path: Path,
    object_root: Path,
    run_id: str,
    system_time: str,
    byte_limit: int,
) -> str:
    relative = path.relative_to(corpus_root).as_posix()
    if path.suffix.lower() != ".txt":
        _observe(
            db,
            relative,
            None,
            "quarantined",
            "unsupported_suffix",
            None,
            run_id,
            system_time,
        )
        return "quarantined"
    size = path.stat().st_size
    if size == 0:
        _observe(db, relative, None, "quarantined", "empty_file", None, run_id, system_time)
        return "quarantined"
    if size > byte_limit:
        _observe(
            db,
            relative,
            None,
            "quarantined",
            f"too_large:{size}",
            None,
            run_id,
            system_time,
        )
        return "quarantined"
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        digest = sha256_bytes(data)
        _observe(db, relative, digest, "quarantined", "not_utf8", None, run_id, system_time)
        return "quarantined"
    digest = sha256_bytes(data)
    object_root.mkdir(parents=True, exist_ok=True)
    target = object_root / digest
    if not target.exists():
        target.write_bytes(data)
    existing = one(
        db.conn,
        "SELECT document_version_id FROM document_versions WHERE content_hash = ? ORDER BY version_index",
        (digest,),
    )
    observation_id = stable_id("obs", relative, digest)
    already = one(
        db.conn,
        "SELECT observation_id FROM file_observations WHERE observation_id = ?",
        (observation_id,),
    )
    if already:
        return "idempotent"
    if existing:
        _observe(
            db,
            relative,
            digest,
            "exact_duplicate",
            "byte_identical_to_existing_version",
            existing["document_version_id"],
            run_id,
            system_time,
        )
        db.append(
            "lineage_recorded",
            stable_id("lin", existing["document_version_id"], relative),
            {
                "edge_id": stable_id("lin", existing["document_version_id"], relative),
                "relation": "exact_byte_duplicate",
                "surviving_document_version_id": existing["document_version_id"],
                "duplicate_relative_path": relative,
                "content_hash": digest,
                "system_time": system_time,
            },
            run_id,
            system_time,
        )
        return "exact_duplicate"
    meta, parse_warnings = parse_metadata(text)
    warnings = list(parse_warnings)
    language = meta.get("language")
    if language is None:
        warnings.append("language_unknown")
        language_uncertainty = "unknown"
    elif language != "en":
        warnings.append("language_not_supported")
        language_uncertainty = "explicit"
    else:
        language_uncertainty = "explicit"
    if "document_date" not in meta:
        warnings.append("document_date_unknown")
        date_uncertainty = "unknown"
    else:
        date_uncertainty = "explicit"
    if "trial_id" not in meta:
        warnings.append("trial_id_missing")
    external_key = Path(relative).stem
    document_id = stable_id("doc", external_key)
    if one(db.conn, "SELECT document_id FROM documents WHERE document_id = ?", (document_id,)) is None:
        db.append(
            "document_recorded",
            document_id,
            {
                "document_id": document_id,
                "external_key": external_key,
                "created_system_time": system_time,
            },
            run_id,
            system_time,
        )
    source_id = None
    if "source" in meta:
        source_id = stable_id("src", meta["source"])
        if one(db.conn, "SELECT source_id FROM sources WHERE source_id = ?", (source_id,)) is None:
            db.append(
                "source_registered",
                source_id,
                {
                    "source_id": source_id,
                    "name": meta["source"],
                    "source_type": meta.get("doc_type") or "unspecified",
                    "reliability_estimate": None,
                    "reliability_note": RELIABILITY_NOTE,
                    "system_time": system_time,
                },
                run_id,
                system_time,
            )
    version_rows = one(
        db.conn,
        "SELECT COUNT(*) AS n FROM document_versions WHERE document_id = ?",
        (document_id,),
    )
    version_index = int(version_rows["n"] if version_rows else 0) + 1
    version_id = stable_id("dv", document_id, digest)
    older_id = None
    if version_index > 1:
        older = one(
            db.conn,
            """
            SELECT document_version_id FROM document_versions
            WHERE document_id = ?
              AND document_version_id NOT IN (
                SELECT older_document_version_id FROM supersessions
              )
            """,
            (document_id,),
        )
        if older:
            older_id = older["document_version_id"]
    db.append(
        "document_version_recorded",
        version_id,
        {
            "document_version_id": version_id,
            "document_id": document_id,
            "version_index": version_index,
            "content_hash": digest,
            "byte_length": len(data),
            "media_type": "text/plain",
            "language": language,
            "language_uncertainty": language_uncertainty,
            "document_date": meta.get("document_date"),
            "document_date_uncertainty": date_uncertainty,
            "doc_type": meta.get("doc_type"),
            "trial_id": meta.get("trial_id"),
            "source_id": source_id,
            "compound": meta.get("compound"),
            "indication": meta.get("indication"),
            "parser_id": PARSER_ID,
            "parser_version": PARSER_VERSION,
            "parse_status": "decoded",
            "parse_quality": None,
            "parse_quality_note": PROBABILITY_NOTE,
            "ocr_confidence": None,
            "ocr_note": "OCR was not run. The file is text/plain.",
            "ingestion_time": system_time,
            "limitations_json": _json_list(_limitations()),
            "warnings_json": _json_list(warnings),
        },
        run_id,
        system_time,
    )
    if older_id is not None:
        supersession_id = stable_id("sup", older_id, version_id)
        db.append(
            "supersession_recorded",
            supersession_id,
            {
                "supersession_id": supersession_id,
                "document_id": document_id,
                "older_document_version_id": older_id,
                "newer_document_version_id": version_id,
                "system_time": system_time,
            },
            run_id,
            system_time,
        )
    _observe(db, relative, digest, "ingested", None, version_id, run_id, system_time)
    return "ingested"


def _json_list(values: list[str]) -> str:
    import json

    return json.dumps(values, ensure_ascii=False)


def _observe(
    db: Database,
    relative: str,
    digest: str | None,
    status: str,
    reason: str | None,
    version_id: str | None,
    run_id: str,
    system_time: str,
) -> None:
    identity = digest or reason or "none"
    observation_id = stable_id("obs", relative, identity)
    db.append(
        "file_observed",
        observation_id,
        {
            "observation_id": observation_id,
            "relative_path": relative,
            "content_hash": digest,
            "status": status,
            "reason": reason,
            "document_version_id": version_id,
            "run_id": run_id,
            "system_time": system_time,
        },
        run_id,
        system_time,
    )
