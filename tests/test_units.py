from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from evidenceai.contradict import assess
from evidenceai.units import normalize


def _claim(token: str, unit_kind: str, start: str = "2021-06-01", end: str = "2022-12-31") -> dict:
    quantity = normalize(token, unit_kind)
    return {
        "canonical_value": format(quantity.canonical, "f"),
        "dimension": quantity.dimension,
        "scale_applied": 1 if quantity.scale_applied else 0,
        "raw_token": token,
        "valid_time_start": start,
        "valid_time_end": end,
    }


def test_thousand_and_fraction_normalize() -> None:
    thousand = normalize("0.180", "count_thousand")
    fraction = normalize("-0.012", "fraction")
    assert thousand.canonical == Decimal("180")
    assert thousand.dimension == "count"
    assert fraction.canonical == Decimal("-1.2")
    assert fraction.dimension == "percent"


def test_rounding_boundary_is_the_registered_tolerance() -> None:
    inside = assess(_claim("0.742", "ratio"), _claim("0.74", "ratio"), "numeric_rule_v0")
    outside = assess(_claim("0.746", "ratio"), _claim("0.74", "ratio"), "numeric_rule_v0")
    assert inside["subtype"] == "rounding_resolved"
    assert inside["predicted_incompatible"] == 0
    assert outside["subtype"] == "incompatible_values"
    assert outside["predicted_incompatible"] == 1


def test_missing_valid_time_is_not_a_conflict() -> None:
    left = _claim("240", "count")
    right = _claim("218", "count", start=None, end=None)
    judged = assess(left, right, "numeric_rule_v0")
    assert judged["subtype"] == "valid_time_unknown"
    assert judged["predicted_incompatible"] == 0


@given(st.integers(min_value=1, max_value=5000))
def test_thousand_round_trip(value: int) -> None:
    token = format(Decimal(value) / Decimal(1000), "f")
    quantity = normalize(token, "count_thousand")
    assert quantity.canonical == Decimal(value)
    assert quantity.scale_applied is True


@given(
    st.decimals(
        min_value="-5",
        max_value="5",
        places=3,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_fraction_scales_to_percent(value: Decimal) -> None:
    quantity = normalize(format(value, "f"), "fraction")
    assert quantity.canonical == value * Decimal(100)
    assert quantity.dimension == "percent"
