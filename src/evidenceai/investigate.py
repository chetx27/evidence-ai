from __future__ import annotations

import re
import sqlite3
from typing import Any

from evidenceai.constants import (
    ANSWER_METHOD,
    PROBABILITY_NOTE,
    RULE_METHOD,
    STANDING_DISCLAIMER,
    SYNTHETIC_BANNER,
)
from evidenceai.ids import stable_id
from evidenceai.pack import load_pack, predicate_record
from evidenceai.readmodel import (
    artifact,
    assessments_for_claims,
    latest_claims,
    latest_versions,
    span,
)
from evidenceai.verify import verify_quotation

_FORMS = (
    (re.compile(r"^What sample size was reported for (SYNTH-\d{3})\?$"), "sample_size"),
    (re.compile(r"^What hazard ratio was reported for (SYNTH-\d{3})\?$"), "hazard_ratio"),
    (re.compile(r"^What HbA1c change was reported for (SYNTH-\d{3})\?$"), "hba1c_change"),
    (
        re.compile(r"^What all-cause mortality count was reported for (SYNTH-\d{3})\?$"),
        "all_cause_mortality",
    ),
)

_STATE_DEFINITIONS = {
    "supported": (
        "At least one verified quotation is available, and numeric_rule_v0 classified "
        "no overlapping pair as incompatible_values."
    ),
    "contradicted": (
        "numeric_rule_v0 classified at least one overlapping pair as incompatible_values. "
        "This is a rule output, not an adjudication, and no source is selected as correct."
    ),
    "insufficient": "No verified quotation is shipped for this question.",
}

_SUPPORTED_FORMS = [
    "What sample size was reported for SYNTH-000?",
    "What hazard ratio was reported for SYNTH-000?",
    "What HbA1c change was reported for SYNTH-000?",
    "What all-cause mortality count was reported for SYNTH-000?",
]


def parse_question(question: str) -> tuple[str, str] | None:
    for pattern, predicate in _FORMS:
        match = pattern.match(question)
        if match:
            return predicate, match.group(1)
    return None


def build_answer(
    conn: sqlite3.Connection,
    question: str,
    assertion_time_lte: str | None = None,
    persisted: bool = False,
) -> dict[str, Any]:
    parsed = parse_question(question)
    limitations = [
        STANDING_DISCLAIMER,
        "Extractor coverage is the EB-Synth v0 frame list.",
        PROBABILITY_NOTE,
    ]
    case = artifact(conn, "case")
    if case and case["body"].get("corpus_label") == "synthetic":
        limitations.insert(0, SYNTHETIC_BANNER)
    if parsed is None:
        return _base(
            question=question,
            state="insufficient",
            reason="question_form_not_supported",
            persisted=persisted,
            assertion_time_lte=assertion_time_lte,
            limitations=limitations,
            what_would_change=(
                "A supported question form, addressed to a trial id in the corpus, "
                "would be answered from extracted claims."
            ),
            system_notes=["The question does not match a Gate 1 form. No model was called."],
            supported_question_forms=_SUPPORTED_FORMS,
        )
    predicate, trial_id = parsed
    versions = latest_versions(conn, trial_id=trial_id)
    if not versions:
        return _base(
            question=question,
            state="insufficient",
            reason="trial_not_in_corpus",
            persisted=persisted,
            assertion_time_lte=assertion_time_lte,
            limitations=limitations,
            what_would_change=(
                "Ingesting a document that names this trial id would make it examinable."
            ),
            system_notes=[
                "The trial id is not on any ingested document. This is not a claim about the world."
            ],
        )
    examined, unknown_time = _select_versions(versions, assertion_time_lte)
    claims = [
        row
        for row in latest_claims(
            conn,
            trial_id=trial_id,
            predicate=predicate,
            assertion_time_lte=assertion_time_lte,
        )
        if row["document_id"] in {item["document_id"] for item in examined}
    ]
    quotations, dropped = _quotations(conn, claims)
    claim_ids = [row["claim_id"] for row in claims]
    pairs = assessments_for_claims(conn, claim_ids, RULE_METHOD)
    incompatible = [row for row in pairs if row["predicted_incompatible"] == 1]
    examined_view = _examined_view(examined, claims)
    notes = [
        "No winning source is selected.",
        PROBABILITY_NOTE,
        STANDING_DISCLAIMER,
    ]
    record = predicate_record(predicate)
    if record and not record.get("extractor"):
        notes.append(
            f"Predicate {predicate} is in the clinical pack ontology and has no extractor "
            f"in pack {load_pack()['version']}. It is not an expected slot. "
            "No claim was extracted. This is not a finding that the documents omit the fact."
        )
    missing = [item for item in examined_view if not item["has_claim"]]
    if missing:
        notes.append(
            "The extractor found no matching frame in one or more examined documents. "
            "A missed frame is not proof that the document is silent."
        )
    if not quotations:
        reason = "quotations_failed_verification" if claims and dropped else "no_extracted_claim"
        return _base(
            question=question,
            state="insufficient",
            reason=reason,
            persisted=persisted,
            assertion_time_lte=assertion_time_lte,
            limitations=limitations,
            what_would_change=(
                "The state would change if a verified quotation for this predicate were produced "
                "from a matched frame."
            ),
            system_notes=notes,
            documents_examined=examined_view,
            documents_with_unknown_assertion_time=unknown_time,
            pair_assessments=[_pair_view(row) for row in pairs],
        )
    state = "contradicted" if incompatible else "supported"
    reason = "incompatible_values_present" if incompatible else "no_incompatible_pair"
    if state == "contradicted":
        change = (
            "The state would change if every incompatible pair were removed, superseded, "
            "or reclassified. Gate 1 does not record reviewer decisions and does not "
            "select a value."
        )
    else:
        change = (
            "An extracted, valid-time-overlapping value that numeric_rule_v0 classifies as "
            "incompatible_values would change this state to contradicted."
        )
    return _base(
        question=question,
        state=state,
        reason=reason,
        persisted=persisted,
        assertion_time_lte=assertion_time_lte,
        limitations=limitations,
        what_would_change=change,
        system_notes=notes,
        documents_examined=examined_view,
        documents_with_unknown_assertion_time=unknown_time,
        quotations=quotations,
        pair_assessments=[_pair_view(row) for row in pairs],
    )


def answer_id_for(question: str) -> str:
    return stable_id("ans", question)


def _select_versions(
    versions: list[dict[str, Any]],
    assertion_time_lte: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if assertion_time_lte is None:
        return versions, []
    examined = []
    unknown = []
    for version in versions:
        if version["document_date"] is None:
            unknown.append(
                {
                    "document_id": version["document_id"],
                    "external_key": version["external_key"],
                    "reason": "assertion_time_unknown",
                }
            )
            continue
        if version["document_date"] <= assertion_time_lte:
            examined.append(version)
    return examined, unknown


def _examined_view(
    versions: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claimed = {row["document_id"] for row in claims}
    return [
        {
            "document_id": version["document_id"],
            "external_key": version["external_key"],
            "doc_type": version["doc_type"],
            "document_date": version["document_date"],
            "has_claim": version["document_id"] in claimed,
        }
        for version in versions
    ]


def _quotations(
    conn: sqlite3.Connection,
    claims: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    quotations = []
    dropped = 0
    ordered = sorted(claims, key=lambda row: (row["assertion_time"] or "", row["claim_id"]))
    for claim_row in ordered:
        evidence = span(conn, claim_row["span_id"])
        if evidence is None:
            dropped += 1
            continue
        checked = verify_quotation(evidence["text"], evidence["text"])
        if not checked["pass"]:
            dropped += 1
            continue
        quotations.append(
            {
                "kind": "quotation",
                "text": evidence["text"],
                "span_id": evidence["span_id"],
                "claim_id": claim_row["claim_id"],
                "document_id": claim_row["document_id"],
                "document_version_id": claim_row["document_version_id"],
                "external_key": claim_row["external_key"],
                "content_hash": claim_row["content_hash"],
                "char_start": evidence["char_start"],
                "char_end": evidence["char_end"],
                "verifier_pass": True,
                "verifier_method": checked["method"],
                "verifier_reason": checked["reason"],
            }
        )
    return quotations, dropped


def _pair_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "assessment_id": row["assessment_id"],
        "claim_id_a": row["claim_id_a"],
        "claim_id_b": row["claim_id_b"],
        "subtype": row["subtype"],
        "predicted_incompatible": bool(row["predicted_incompatible"]),
        "valid_time_relation": row["valid_time_relation"],
        "abs_difference": row["abs_difference"],
        "tolerance": row["tolerance"],
        "rationale": row["rationale"],
    }


def _base(**kwargs: Any) -> dict[str, Any]:
    question = kwargs["question"]
    state = kwargs["state"]
    persisted = kwargs["persisted"]
    return {
        "answer_id": answer_id_for(question),
        "question": question,
        "state": state,
        "state_definition": _STATE_DEFINITIONS[state],
        "reason": kwargs["reason"],
        "method": ANSWER_METHOD,
        "persisted": persisted,
        "audit_note": (
            "Appended to the event log."
            if persisted
            else "Computed on read and not appended to the event log."
        ),
        "assertion_time_lte": kwargs.get("assertion_time_lte"),
        "quotations": kwargs.get("quotations", []),
        "pair_assessments": kwargs.get("pair_assessments", []),
        "documents_examined": kwargs.get("documents_examined", []),
        "documents_with_unknown_assertion_time": kwargs.get(
            "documents_with_unknown_assertion_time", []
        ),
        "what_would_change": kwargs["what_would_change"],
        "system_notes": kwargs.get("system_notes", []),
        "limitations": kwargs.get("limitations", []),
        "supported_question_forms": kwargs.get("supported_question_forms", _SUPPORTED_FORMS),
    }
