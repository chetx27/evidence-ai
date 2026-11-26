from evidenceai.verify import numerals, verify_quotation


def test_identifier_digits_are_not_numerals() -> None:
    assert numerals("Trial SYNTH-001 reports 240.") == ["240"]


def test_exact_span_passes() -> None:
    span = "The randomized sample size was 218 participants."
    assert verify_quotation(span, span)["pass"] is True


def test_added_numeral_fails() -> None:
    span = "The randomized sample size was 218 participants."
    checked = verify_quotation(span + " 999", span)
    assert checked["pass"] is False
    assert checked["reason"] == "quotation_is_not_the_span_text"
