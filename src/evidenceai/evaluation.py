from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

from evidenceai.constants import BASELINE_METHOD, RULE_METHOD
from evidenceai.ids import canonical_json
from evidenceai.prereg import load_prereg
from evidenceai.readmodel import artifact, latest_claims
from evidenceai.store import Database, rows

_NOT_MEASURED = (
    {
        "metric": "calibration_ece",
        "reason": "No labeled probability set has been scored.",
    },
    {
        "metric": "brier",
        "reason": "No labeled probability set has been scored.",
    },
    {
        "metric": "llm_only_baseline",
        "reason": "No model endpoint is configured and no weights are installed.",
    },
    {
        "metric": "research_hypotheses_h1_through_h6",
        "reason": "This fixture run does not test those hypotheses.",
    },
    {
        "metric": "multilingual_disparity",
        "reason": "The fixture is English only.",
    },
    {
        "metric": "user_study",
        "reason": "No participant session has been run.",
    },
)


def evaluate(db: Database) -> dict[str, Any]:
    prereg = load_prereg()
    stored = artifact(db.conn, "eb_synth_manifest")
    if stored is None:
        raise RuntimeError("The slice manifest artifact is missing.")
    manifest = stored["body"]
    claims = latest_claims(db.conn)
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    ambiguous: list[str] = []
    for claim in claims:
        key = (claim["external_key"], claim["predicate"], claim["raw_token"])
        if key in index:
            ambiguous.append(claim["claim_id"])
        else:
            index[key] = claim
    assertion_keys = {
        (item["doc_key"], item["predicate"], item["raw_token"]) for item in manifest["assertions"]
    }
    hits = 0
    unexpected_misses = 0
    value_mismatches = 0
    aligned: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for assertion in manifest["assertions"]:
        key = (assertion["doc_key"], assertion["predicate"], assertion["raw_token"])
        claim = index.get(key)
        if claim is None:
            unexpected_misses += 1
            continue
        if Decimal(claim["canonical_value"]) != Decimal(assertion["expected_canonical"]):
            value_mismatches += 1
            continue
        hits += 1
        aligned.append((assertion, claim))
    false_extractions = 0
    for claim in claims:
        key = (claim["external_key"], claim["predicate"], claim["raw_token"])
        if key not in assertion_keys:
            false_extractions += 1
    accidental = 0
    for item in manifest["unsupported_frames"]:
        if any(
            claim["external_key"] == item["doc_key"] and claim["predicate"] == item["predicate"]
            for claim in claims
        ):
            accidental += 1
    assessments = rows(db.conn, "SELECT * FROM pair_assessments")
    by_pair = {
        (row["claim_id_a"], row["claim_id_b"], row["method"]): row for row in assessments
    }
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for assertion in manifest["assertions"]:
        grouped.setdefault((assertion["trial_id"], assertion["predicate"]), []).append(assertion)
    aligned_by_id = {assertion["assertion_id"]: claim for assertion, claim in aligned}
    methods = {
        RULE_METHOD: _blank_confusion(),
        BASELINE_METHOD: _blank_confusion(),
    }
    excluded_extraction_miss = 0
    excluded_valid_time = 0
    unassessed = 0
    false_positive_pairs: list[dict[str, Any]] = []
    for group in grouped.values():
        for left, right in combinations(group, 2):
            left_claim = aligned_by_id.get(left["assertion_id"])
            right_claim = aligned_by_id.get(right["assertion_id"])
            if left_claim is None or right_claim is None:
                excluded_extraction_miss += 1
                continue
            truth_incompatible = Decimal(left["latent"]) != Decimal(right["latent"])
            claim_a, claim_b = sorted((left_claim["claim_id"], right_claim["claim_id"]))
            judged_rows = []
            missing = False
            non_overlap = False
            for method in methods:
                judged = by_pair.get((claim_a, claim_b, method))
                if judged is None:
                    missing = True
                    break
                if judged["valid_time_relation"] != "overlap":
                    non_overlap = True
                judged_rows.append(judged)
            if missing:
                unassessed += 1
                continue
            if non_overlap:
                excluded_valid_time += 1
                continue
            for judged in judged_rows:
                predicted = judged["predicted_incompatible"] == 1
                _tally(methods[judged["method"]], truth_incompatible, predicted)
                if judged["method"] == RULE_METHOD and predicted and not truth_incompatible:
                    false_positive_pairs.append(
                        {
                            "trial_id": left["trial_id"],
                            "predicate": left["predicate"],
                            "raw_tokens": [left["raw_token"], right["raw_token"]],
                            "latent_values": [left["latent"], right["latent"]],
                            "canonical_values": [
                                left_claim["canonical_value"],
                                right_claim["canonical_value"],
                            ],
                            "subtype": judged["subtype"],
                        }
                    )
    scored_methods = {}
    for name, confusion in methods.items():
        fp_tn = confusion["fp"] + confusion["tn"]
        tp_fn = confusion["tp"] + confusion["fn"]
        tp_fp = confusion["tp"] + confusion["fp"]
        scored_methods[name] = {
            **confusion,
            "false_conflict_rate": _rate(confusion["fp"], fp_tn),
            "recall": _rate(confusion["tp"], tp_fn),
            "precision": _rate(confusion["tp"], tp_fp),
        }
    rule = scored_methods[RULE_METHOD]
    baseline = scored_methods[BASELINE_METHOD]
    directional = _directional(rule, baseline) and unassessed == 0
    answers = []
    quotation_total = 0
    quotation_pass = 0
    for row in rows(db.conn, "SELECT body_json FROM answers ORDER BY question"):
        body = json.loads(row["body_json"])
        quotations = body.get("quotations", [])
        passed = sum(1 for item in quotations if item.get("verifier_pass") is True)
        quotation_total += len(quotations)
        quotation_pass += passed
        answers.append(
            {
                "question": body["question"],
                "state": body["state"],
                "quotation_count": len(quotations),
                "verifier_failures": len(quotations) - passed,
            }
        )
    return {
        "preregistration_id": prereg["id"],
        "corpus_label": manifest["corpus_label"],
        "fixture": prereg["fixture"],
        "fixture_role": prereg["fixture_role"],
        "fixture_latent_note": (
            "Latent values exist only because this corpus is synthetic. "
            "The answer path does not read them."
        ),
        "extraction": {
            "declared_frames": len(manifest["assertions"]),
            "declared_hits": hits,
            "unexpected_misses": unexpected_misses,
            "value_mismatches": value_mismatches,
            "false_extractions": false_extractions,
            "alignment_ambiguous_claims": len(ambiguous),
            "known_unsupported_frames": len(manifest["unsupported_frames"]),
            "unsupported_frames_accidentally_extracted": accidental,
        },
        "pairs": {
            "excluded_extraction_miss": excluded_extraction_miss,
            "excluded_valid_time": excluded_valid_time,
            "unassessed": unassessed,
        },
        "methods": scored_methods,
        "directional_expectation_met": directional,
        "rule_false_positives_at_least_one": rule["fp"] >= 1,
        "rule_false_positive_pairs": false_positive_pairs,
        "answers": answers,
        "quotation_check": {
            "shipped_quotations": quotation_total,
            "verifier_pass": quotation_pass,
            "pass_rate": _rate(quotation_pass, quotation_total),
            "note": "Exact span quotation check. Not a human faithfulness judgment.",
        },
        "not_measured": list(_NOT_MEASURED),
    }


def write_report(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(summary) + "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(_markdown(summary), encoding="utf-8")


def _blank_confusion() -> dict[str, int]:
    return {"tp": 0, "fp": 0, "tn": 0, "fn": 0}


def _tally(confusion: dict[str, int], truth_incompatible: bool, predicted: bool) -> None:
    if truth_incompatible and predicted:
        confusion["tp"] += 1
    elif truth_incompatible and not predicted:
        confusion["fn"] += 1
    elif predicted:
        confusion["fp"] += 1
    else:
        confusion["tn"] += 1


def _rate(numerator: int, denominator: int) -> dict[str, Any] | None:
    if denominator == 0:
        return None
    value = (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )
    return {"numerator": numerator, "denominator": denominator, "value": format(value, "f")}


def _directional(rule: dict[str, Any], baseline: dict[str, Any]) -> bool:
    rule_fcr = rule["false_conflict_rate"]
    base_fcr = baseline["false_conflict_rate"]
    rule_recall = rule["recall"]
    base_recall = baseline["recall"]
    if not rule_fcr or not base_fcr or not rule_recall or not base_recall:
        return False
    return Decimal(rule_fcr["value"]) < Decimal(base_fcr["value"]) and Decimal(
        rule_recall["value"]
    ) >= Decimal(base_recall["value"])


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Gate 1 fixture diagnostic",
        "",
        "Generated by evidenceai.cli harness. Do not edit by hand.",
        "",
        f"Pre-registration: {summary['preregistration_id']}",
        f"Corpus label: {summary['corpus_label']}",
        f"Fixture role: {summary['fixture_role']}",
        "",
        "## Extraction counts",
        "",
    ]
    for key, value in summary["extraction"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Pair scoring", ""])
    for name, block in summary["methods"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(
            f"- tp {block['tp']}, fp {block['fp']}, tn {block['tn']}, fn {block['fn']}"
        )
        for metric in ("false_conflict_rate", "recall", "precision"):
            lines.append(f"- {metric}: {_fmt_rate(block[metric])}")
        lines.append("")
    lines.append(
        f"Directional expectation met: {str(summary['directional_expectation_met']).lower()}"
    )
    lines.append(
        "This comparison is a census of the fixed fixture. It is not a significance claim."
    )
    lines.extend(["", "## Not measured", ""])
    for item in summary["not_measured"]:
        lines.append(f"- {item['metric']}: {item['reason']}")
    lines.append("")
    return "\n".join(lines)


def _fmt_rate(rate: dict[str, Any] | None) -> str:
    if rate is None:
        return "undefined"
    return f"{rate['numerator']}/{rate['denominator']} ({rate['value']})"
