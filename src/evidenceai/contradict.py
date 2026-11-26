from __future__ import annotations

from decimal import Decimal
from typing import Any

from evidenceai.constants import BASELINE_METHOD, RULE_METHOD
from evidenceai.intervals import relation
from evidenceai.units import format_decimal, tolerance_for


def _time_relation(left: dict[str, Any], right: dict[str, Any]) -> str:
    mapped = relation(
        left.get("valid_time_start"),
        left.get("valid_time_end"),
        right.get("valid_time_start"),
        right.get("valid_time_end"),
    )
    if mapped == "non_overlap":
        return "non_overlap"
    if mapped == "unknown":
        return "unknown"
    return "overlap"


def assess(left: dict[str, Any], right: dict[str, Any], method: str) -> dict[str, Any]:
    if method == RULE_METHOD:
        return _rule(left, right)
    if method == BASELINE_METHOD:
        return _baseline(left, right)
    raise ValueError(f"Unknown assessment method: {method}")


def _time_block(time_relation: str) -> dict[str, Any] | None:
    if time_relation == "overlap":
        return None
    if time_relation == "unknown":
        subtype = "valid_time_unknown"
        rationale = (
            "Valid time is missing on at least one claim. "
            "The pair is not classified as a numeric conflict. "
            "Missing time is not treated as overlap."
        )
    else:
        subtype = "temporal_non_overlap"
        rationale = (
            "Valid-time intervals do not overlap. "
            "The pair is not classified as a numeric conflict and is not labeled supersession. "
            "A supersession model is not implemented."
        )
    return {
        "subtype": subtype,
        "predicted_incompatible": 0,
        "valid_time_relation": time_relation,
        "abs_difference": None,
        "tolerance": None,
        "rationale": rationale,
    }


def _rule(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    time_relation = _time_relation(left, right)
    blocked = _time_block(time_relation)
    if blocked:
        return blocked
    if left["dimension"] != right["dimension"]:
        return {
            "subtype": "not_comparable",
            "predicted_incompatible": 0,
            "valid_time_relation": time_relation,
            "abs_difference": None,
            "tolerance": None,
            "rationale": (
                f"Dimensions {left['dimension']} and {right['dimension']} "
                "are not compared. The pair is not called a conflict."
            ),
        }
    left_value = Decimal(left["canonical_value"])
    right_value = Decimal(right["canonical_value"])
    difference = abs(left_value - right_value)
    tolerance = tolerance_for(left["dimension"])
    tolerance_text = "exact" if tolerance is None else format_decimal(tolerance)
    scale = int(left["scale_applied"]) == 1 or int(right["scale_applied"]) == 1
    if left_value == right_value and scale:
        subtype = "scale_resolved"
        predicted = 0
        why = "Canonical values are equal after the registered scale conversion."
    elif left_value == right_value:
        subtype = "equivalent"
        predicted = 0
        why = "Canonical values are equal."
    elif tolerance is not None and difference <= tolerance:
        subtype = "rounding_resolved"
        predicted = 0
        why = (
            "Absolute difference is within the pre-registered rounding tolerance "
            f"({tolerance_text})."
        )
    else:
        subtype = "incompatible_values"
        predicted = 1
        why = (
            "Absolute difference is outside the pre-registered numeric rule. "
            "No source is selected as correct."
        )
    return {
        "subtype": subtype,
        "predicted_incompatible": predicted,
        "valid_time_relation": time_relation,
        "abs_difference": format_decimal(difference),
        "tolerance": tolerance_text,
        "rationale": (
            f"Canonical values {format_decimal(left_value)} and {format_decimal(right_value)} "
            f"({left['dimension']}), absolute difference {format_decimal(difference)}, "
            f"tolerance {tolerance_text}. {why}"
        ),
    }


def _baseline(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    time_relation = _time_relation(left, right)
    blocked = _time_block(time_relation)
    if blocked:
        blocked["rationale"] = (
            "Surface-string baseline skipped the pair because valid time does not support "
            "a conflict classification. " + blocked["rationale"]
        )
        return blocked
    if left["raw_token"] == right["raw_token"]:
        return {
            "subtype": "surface_equal",
            "predicted_incompatible": 0,
            "valid_time_relation": time_relation,
            "abs_difference": None,
            "tolerance": None,
            "rationale": "Surface numeric tokens are identical. Scale and rounding are ignored by design.",
        }
    return {
        "subtype": "surface_string_mismatch",
        "predicted_incompatible": 1,
        "valid_time_relation": time_relation,
        "abs_difference": None,
        "tolerance": None,
        "rationale": (
            f"Surface numeric tokens {left['raw_token']} and {right['raw_token']} differ. "
            "This baseline does not normalize scale, fraction, or rounding."
        ),
    }
