from __future__ import annotations

from typing import Any

# Product of calibrated components. A null component is excluded.
# A null component is never treated as zero, and no default probability is inserted.
COMPOSITION_FUNCTION = (
    "product of calibrated components; null components are excluded and are not treated as zero"
)

_COMPONENTS = (
    "extraction_confidence",
    "resolution_confidence",
    "source_reliability",
    "corroboration_ess",
    "temporal_consistency",
    "verifier_agreement",
)


def compose(claim: dict[str, Any]) -> dict[str, Any]:
    used: list[str] = []
    excluded: list[str] = []
    for name in _COMPONENTS:
        if claim.get(name) is None:
            excluded.append(name)
        else:
            used.append(name)
    value = None
    if used:
        product = 1.0
        for name in used:
            product *= float(claim[name])
        value = product
    return {
        "value": value,
        "function": COMPOSITION_FUNCTION,
        "inputs_used": used,
        "inputs_excluded": excluded,
        "calibration": "not yet measured",
        "calibration_note": "No reliability diagram, ECE, or Brier score has been computed.",
    }
