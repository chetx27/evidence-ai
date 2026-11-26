"""Version identifiers for Gate 1. These are release labels, not measured results."""

SCHEMA_VERSION = "ceg-0.1.0"
EXTRACTOR_ID = "clinical_pattern_v0"
EXTRACTOR_VERSION = "0.1.0"
GENERATOR_ID = "eb-synth"
GENERATOR_VERSION = "0.1.0"
PARSER_ID = "utf8_text_v0"
PARSER_VERSION = "0.1.0"
RULE_METHOD = "numeric_rule_v0"
BASELINE_METHOD = "surface_string_baseline"
VERIFIER_METHOD = "quoted_span_numeric_subset_v0"
ANSWER_METHOD = "gate1_quote_and_numeric_rule"
REGISTERED_SEED = 20261126
CASE_ID = "case_ebsynth_v0"
RUN_ID = "run_ebsynth_v0_20261126"
MAX_BYTES = 1_000_000
IMPLEMENTED_LANGUAGE = "en"

STANDING_DISCLAIMER = (
    "EvidenceAI outputs are investigative aids, not adjudications. "
    "Gate 1 does not select a winning source. "
    "Calibrated probabilities are not yet measured."
)

SYNTHETIC_BANNER = (
    "Synthetic fixture. Not real trials. Not real patients. Not real publications."
)

RELIABILITY_NOTE = (
    "Source reliability is not yet measured. No hand-set prior is applied."
)

PROBABILITY_NOTE = "Calibrated probability is not yet measured."
