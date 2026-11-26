from __future__ import annotations

import re

from evidenceai.constants import VERIFIER_METHOD

_NUMBER = re.compile(r"(?<![A-Za-z0-9-])[+-]?\d+(?:\.\d+)?(?![A-Za-z0-9])")


def numerals(text: str) -> list[str]:
    return _NUMBER.findall(text)


def verify_quotation(quotation: str, span_text: str) -> dict[str, object]:
    """Gate 1 verifier: a shipped factual sentence must be the cited span, numerals included.

    This is not a neural entailment model. Agreement is boolean. No probability is emitted.
    """
    if quotation != span_text:
        return {
            "pass": False,
            "method": VERIFIER_METHOD,
            "reason": "quotation_is_not_the_span_text",
        }
    found = numerals(quotation)
    if not found:
        return {
            "pass": False,
            "method": VERIFIER_METHOD,
            "reason": "quotation_has_no_numeral",
        }
    span_found = set(numerals(span_text))
    missing = [token for token in found if token not in span_found]
    if missing:
        return {
            "pass": False,
            "method": VERIFIER_METHOD,
            "reason": "numeral_absent_from_span",
            "missing": missing,
        }
    return {
        "pass": True,
        "method": VERIFIER_METHOD,
        "reason": "span_quoted_and_numerals_covered",
    }
