from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from evidenceai.prereg import percent_tolerance, ratio_tolerance


@dataclass(frozen=True)
class Quantity:
    canonical: Decimal
    dimension: str
    scale_applied: bool
    raw_token: str
    unit_kind: str


def normalize(token: str, unit_kind: str) -> Quantity:
    raw = Decimal(token)
    if unit_kind == "count":
        return Quantity(raw, "count", False, token, unit_kind)
    if unit_kind == "count_thousand":
        return Quantity(raw * Decimal("1000"), "count", True, token, unit_kind)
    if unit_kind == "ratio":
        return Quantity(raw, "ratio", False, token, unit_kind)
    if unit_kind == "percent":
        return Quantity(raw, "percent", False, token, unit_kind)
    if unit_kind == "fraction":
        return Quantity(raw * Decimal("100"), "percent", True, token, unit_kind)
    raise ValueError(f"Unknown unit kind: {unit_kind}")


def tolerance_for(dimension: str) -> Decimal | None:
    if dimension == "count":
        return None
    if dimension == "ratio":
        return ratio_tolerance()
    if dimension == "percent":
        return percent_tolerance()
    raise ValueError(f"Unknown dimension: {dimension}")


def format_decimal(value: Decimal) -> str:
    return format(value, "f")
