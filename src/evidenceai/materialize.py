from __future__ import annotations

import json

from evidenceai.constants import (
    BASELINE_METHOD,
    EXTRACTOR_ID,
    EXTRACTOR_VERSION,
    IMPLEMENTED_LANGUAGE,
    PROBABILITY_NOTE,
    RELIABILITY_NOTE,
    RULE_METHOD,
    SCHEMA_VERSION,
)
from evidenceai.contradict import assess
from evidenceai.extract import extract_text
from evidenceai.ids import sha256_text, stable_id
from evidenceai.readmodel import latest_claims, latest_versions, object_text
from evidenceai.store import Database
from evidenceai.units import format_decimal

_EXTRACTION_NOTE = (
    "Matched a registered sentence frame. Modality, polarity, and hedging come from the frame "
    "definition, not from a classifier. Calibrated extraction probability is not yet measured."
)
_RESOLUTION_NOTE = (
    "Exact trial-identifier match. Calibrated resolution probability is not yet measured."
)


def materialize_extractions(db: Database, run_id: str, system_time: str) -> None:
    for version in latest_versions(db.conn):
        text = object_text(db.path, version["content_hash"])
        language = version["language"]
        extracted = extract_text(
            text,
            version["doc_type"],
            language if language == IMPLEMENTED_LANGUAGE else None,
        )
        if extracted.errors:
            raise RuntimeError(
                "Extractor refused an ambiguous line in "
                f"{version['external_key']}: {extracted.errors}"
            )
        _spans(db, version, extracted.boilerplate, "boilerplate", 1, run_id, system_time, text)
        temporal_ids: list[str] = []
        temporal_bounds: list[tuple[str, str]] = []
        for item in extracted.temporal:
            span_id = _span_row(
                db,
                version["document_version_id"],
                item.start,
                item.end,
                item.text,
                "temporal",
                0,
                run_id,
                system_time,
                text,
            )
            temporal_ids.append(span_id)
            temporal_bounds.append((item.valid_start, item.valid_end))
        if version["trial_id"]:
            _entity(db, version["trial_id"], run_id, system_time)
        if language != IMPLEMENTED_LANGUAGE or not version["trial_id"]:
            continue
        if len(temporal_bounds) == 1:
            valid_start, valid_end = temporal_bounds[0]
            valid_uncertainty = "explicit"
            temporal_span_id = temporal_ids[0]
            temporal_note = "Valid time is the single study-period frame in this document."
        elif len(temporal_bounds) == 0:
            valid_start, valid_end = None, None
            valid_uncertainty = "unknown"
            temporal_span_id = None
            temporal_note = "No study-period frame was found. Valid time was not invented."
        else:
            valid_start, valid_end = None, None
            valid_uncertainty = "ambiguous"
            temporal_span_id = None
            temporal_note = "More than one study-period frame was found. No interval was selected."
        entity_id = stable_id("ent", "trial", version["trial_id"])
        for found in extracted.claims:
            span_id = _span_row(
                db,
                version["document_version_id"],
                found.line_start,
                found.line_end,
                found.line_text,
                "evidence",
                0,
                run_id,
                system_time,
                text,
            )
            claim_id = stable_id(
                "cl",
                version["document_version_id"],
                found.frame.frame_id,
                found.quantity.raw_token,
                str(found.line_start),
            )
            db.append(
                "claim_recorded",
                claim_id,
                {
                    "claim_id": claim_id,
                    "entity_id": entity_id,
                    "trial_id": version["trial_id"],
                    "predicate": found.frame.predicate,
                    "polarity": found.frame.polarity,
                    "modality": found.frame.modality,
                    "hedging": found.frame.hedging,
                    "canonical_value": format_decimal(found.quantity.canonical),
                    "dimension": found.quantity.dimension,
                    "unit_kind": found.quantity.unit_kind,
                    "raw_token": found.quantity.raw_token,
                    "scale_applied": 1 if found.quantity.scale_applied else 0,
                    "valid_time_start": valid_start,
                    "valid_time_end": valid_end,
                    "valid_time_uncertainty": valid_uncertainty,
                    "valid_time_span_id": temporal_span_id,
                    "assertion_time": version["document_date"],
                    "assertion_time_uncertainty": version["document_date_uncertainty"],
                    "span_id": span_id,
                    "document_version_id": version["document_version_id"],
                    "document_id": version["document_id"],
                    "extractor_id": EXTRACTOR_ID,
                    "extractor_version": EXTRACTOR_VERSION,
                    "prompt_hash": None,
                    "schema_version": SCHEMA_VERSION,
                    "frame_id": found.frame.frame_id,
                    "extraction_confidence": None,
                    "extraction_note": _EXTRACTION_NOTE,
                    "resolution_confidence": None,
                    "resolution_note": _RESOLUTION_NOTE,
                    "source_reliability": None,
                    "source_reliability_note": RELIABILITY_NOTE,
                    "corroboration_ess": None,
                    "corroboration_note": "Effective independent sample size is not yet measured.",
                    "temporal_consistency": None,
                    "temporal_note": temporal_note + " " + PROBABILITY_NOTE,
                    "verifier_agreement": None,
                    "verifier_note": (
                        "Claim-level verifier agreement is not yet measured. "
                        "Quotation checks are recorded on answers."
                    ),
                    "system_time": system_time,
                },
                run_id,
                system_time,
            )


def materialize_assessments(db: Database, run_id: str, system_time: str) -> None:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for claim_row in latest_claims(db.conn):
        grouped.setdefault((claim_row["trial_id"], claim_row["predicate"]), []).append(claim_row)
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item["claim_id"])
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if left["document_id"] == right["document_id"]:
                    continue
                for method in (RULE_METHOD, BASELINE_METHOD):
                    judged = assess(left, right, method)
                    assessment_id = stable_id("pa", left["claim_id"], right["claim_id"], method)
                    db.append(
                        "pair_assessed",
                        assessment_id,
                        {
                            "assessment_id": assessment_id,
                            "claim_id_a": left["claim_id"],
                            "claim_id_b": right["claim_id"],
                            "method": method,
                            "subtype": judged["subtype"],
                            "predicted_incompatible": judged["predicted_incompatible"],
                            "valid_time_relation": judged["valid_time_relation"],
                            "abs_difference": judged["abs_difference"],
                            "tolerance": judged["tolerance"],
                            "rationale": judged["rationale"],
                            "system_time": system_time,
                            "schema_version": SCHEMA_VERSION,
                        },
                        run_id,
                        system_time,
                    )


def _entity(db: Database, trial_id: str, run_id: str, system_time: str) -> None:
    entity_id = stable_id("ent", "trial", trial_id)
    db.append(
        "entity_recorded",
        entity_id,
        {
            "entity_id": entity_id,
            "entity_type": "trial",
            "canonical_name": trial_id,
            "trial_id": trial_id,
            "resolution_state": "identifier_match",
            "resolution_method": "exact_trial_identifier",
            "resolution_confidence": None,
            "resolution_note": _RESOLUTION_NOTE,
            "system_time": system_time,
        },
        run_id,
        system_time,
    )


def _spans(
    db: Database,
    version: dict,
    spans: list[tuple[int, int, str]],
    role: str,
    boilerplate: int,
    run_id: str,
    system_time: str,
    text: str,
) -> None:
    for start, end, line in spans:
        _span_row(
            db,
            version["document_version_id"],
            start,
            end,
            line,
            role,
            boilerplate,
            run_id,
            system_time,
            text,
        )


def _span_row(
    db: Database,
    document_version_id: str,
    start: int,
    end: int,
    line: str,
    role: str,
    boilerplate: int,
    run_id: str,
    system_time: str,
    text: str,
) -> str:
    if text[start:end] != line:
        raise RuntimeError("Span offsets do not match the original document bytes.")
    span_id = stable_id("sp", document_version_id, str(start), str(end), role)
    db.append(
        "span_recorded",
        span_id,
        {
            "span_id": span_id,
            "document_version_id": document_version_id,
            "char_start": start,
            "char_end": end,
            "text": line,
            "text_hash": sha256_text(line),
            "role": role,
            "boilerplate": boilerplate,
            "page": None,
            "bbox_json": None,
            "system_time": system_time,
        },
        run_id,
        system_time,
    )
    return span_id


def json_dumps(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
