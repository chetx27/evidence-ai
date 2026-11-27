export type CasePayload = {
  case_id: string;
  corpus_label: string;
  disclaimer: string;
  standing_disclaimer: string;
  pack_id: string;
  pack_version: string;
  schema_version: string;
  extractor_id: string;
  preregistration_id: string;
  registered_questions: string[];
  counts: Record<string, number> | null;
  run_status: string;
  duration_seconds: string | null;
  triage_conflicts: number;
  seed: number | null;
};

export type DocumentSummary = {
  document_id: string;
  external_key: string;
  doc_type: string | null;
  trial_id: string | null;
  language: string | null;
  document_date: string | null;
  content_hash: string;
  byte_length: number;
  warnings: string[];
  limitations: string[];
};

export type SpanRecord = {
  span_id: string;
  char_start: number;
  char_end: number;
  text: string;
  role: string;
  boilerplate: boolean;
};

export type Confidence = {
  value: number | null;
  function: string;
  inputs_used: string[];
  inputs_excluded: string[];
  calibration: string;
  calibration_note: string;
};

export type ClaimRecord = {
  claim_id: string;
  predicate: string;
  raw_token: string;
  canonical_value: string;
  dimension: string;
  span_id: string;
  assertion_time: string | null;
  valid_time_start: string | null;
  valid_time_end: string | null;
  valid_time_uncertainty: string;
  frame_id: string;
  extractor_id: string;
  confidence: Confidence;
  extraction_note: string;
};

export type DocumentDetail = DocumentSummary & {
  text: string;
  page: null;
  page_note: string;
  bounding_box: null;
  spans: SpanRecord[];
  claims: ClaimRecord[];
};

export type ContradictionSummary = {
  assessment_id: string;
  trial_id: string;
  predicate: string;
  subtype: string;
  raw_token_a: string;
  raw_token_b: string;
  canonical_a: string;
  canonical_b: string;
  abs_difference: string | null;
  tolerance: string | null;
  rationale: string;
};

export type ContradictionSide = {
  claim_id: string;
  document_id: string;
  external_key: string;
  doc_type: string;
  content_hash: string;
  predicate: string;
  raw_token: string;
  canonical_value: string;
  char_start: number;
  char_end: number;
  span_text: string;
  confidence: Confidence;
};

export type ContradictionDetail = {
  assessment_id: string;
  method: string;
  subtype: string;
  rationale: string;
  abs_difference: string | null;
  tolerance: string | null;
  valid_time_relation: string;
  left: ContradictionSide;
  right: ContradictionSide;
};

export type Quotation = {
  text: string;
  span_id: string;
  document_id: string;
  external_key: string;
  content_hash: string;
  char_start: number;
  char_end: number;
  verifier_pass: boolean;
  verifier_method: string;
};

export type AnswerPayload = {
  answer_id: string;
  question: string;
  state: string;
  state_definition: string;
  reason: string;
  persisted: boolean;
  audit_note: string;
  quotations: Quotation[];
  what_would_change: string;
  system_notes: string[];
  limitations: string[];
  pair_assessments: { assessment_id: string; subtype: string; rationale: string }[];
};

export type Rate = { numerator: number; denominator: number; value: string } | null;

export type EvaluationPayload = {
  fixture: string;
  fixture_role: string;
  corpus_label: string;
  directional_expectation_met: boolean;
  methods: Record<
    string,
    {
      tp: number;
      fp: number;
      tn: number;
      fn: number;
      false_conflict_rate: Rate;
      recall: Rate;
      precision: Rate;
    }
  >;
  extraction: Record<string, number>;
  not_measured: { metric: string; reason: string }[];
  quotation_check: {
    shipped_quotations: number;
    verifier_pass: number;
    pass_rate: Rate;
    note: string;
  };
};
