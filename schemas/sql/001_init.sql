PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  system_time TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  object_id TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  seed INTEGER NOT NULL,
  generator_id TEXT NOT NULL,
  generator_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  extractor_id TEXT NOT NULL,
  extractor_version TEXT NOT NULL,
  pack_id TEXT NOT NULL,
  pack_version TEXT NOT NULL,
  preregistration_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_run_completions (
  run_id TEXT PRIMARY KEY,
  finished_at TEXT NOT NULL,
  status TEXT NOT NULL,
  duration_seconds TEXT NOT NULL,
  counts_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  source_type TEXT NOT NULL,
  reliability_estimate REAL,
  reliability_note TEXT NOT NULL,
  system_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY,
  external_key TEXT NOT NULL UNIQUE,
  created_system_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_versions (
  document_version_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  version_index INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  byte_length INTEGER NOT NULL,
  media_type TEXT NOT NULL,
  language TEXT,
  language_uncertainty TEXT NOT NULL,
  document_date TEXT,
  document_date_uncertainty TEXT NOT NULL,
  doc_type TEXT,
  trial_id TEXT,
  source_id TEXT,
  compound TEXT,
  indication TEXT,
  parser_id TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  parse_status TEXT NOT NULL,
  parse_quality REAL,
  parse_quality_note TEXT NOT NULL,
  ocr_confidence REAL,
  ocr_note TEXT NOT NULL,
  ingestion_time TEXT NOT NULL,
  limitations_json TEXT NOT NULL,
  warnings_json TEXT NOT NULL,
  FOREIGN KEY (document_id) REFERENCES documents(document_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS supersessions (
  supersession_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  older_document_version_id TEXT NOT NULL,
  newer_document_version_id TEXT NOT NULL,
  system_time TEXT NOT NULL,
  FOREIGN KEY (document_id) REFERENCES documents(document_id),
  FOREIGN KEY (older_document_version_id) REFERENCES document_versions(document_version_id),
  FOREIGN KEY (newer_document_version_id) REFERENCES document_versions(document_version_id)
);

CREATE TABLE IF NOT EXISTS file_observations (
  observation_id TEXT PRIMARY KEY,
  relative_path TEXT NOT NULL,
  content_hash TEXT,
  status TEXT NOT NULL,
  reason TEXT,
  document_version_id TEXT,
  run_id TEXT NOT NULL,
  system_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage_edges (
  edge_id TEXT PRIMARY KEY,
  relation TEXT NOT NULL,
  surviving_document_version_id TEXT NOT NULL,
  duplicate_relative_path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  system_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spans (
  span_id TEXT PRIMARY KEY,
  document_version_id TEXT NOT NULL,
  char_start INTEGER NOT NULL,
  char_end INTEGER NOT NULL,
  text TEXT NOT NULL,
  text_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  boilerplate INTEGER NOT NULL,
  page INTEGER,
  bbox_json TEXT,
  system_time TEXT NOT NULL,
  FOREIGN KEY (document_version_id) REFERENCES document_versions(document_version_id)
);

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  trial_id TEXT NOT NULL UNIQUE,
  resolution_state TEXT NOT NULL,
  resolution_method TEXT NOT NULL,
  resolution_confidence REAL,
  resolution_note TEXT NOT NULL,
  system_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  trial_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  polarity TEXT NOT NULL,
  modality TEXT NOT NULL,
  hedging TEXT NOT NULL,
  canonical_value TEXT NOT NULL,
  dimension TEXT NOT NULL,
  unit_kind TEXT NOT NULL,
  raw_token TEXT NOT NULL,
  scale_applied INTEGER NOT NULL,
  valid_time_start TEXT,
  valid_time_end TEXT,
  valid_time_uncertainty TEXT NOT NULL,
  valid_time_span_id TEXT,
  assertion_time TEXT,
  assertion_time_uncertainty TEXT NOT NULL,
  span_id TEXT NOT NULL,
  document_version_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  extractor_id TEXT NOT NULL,
  extractor_version TEXT NOT NULL,
  prompt_hash TEXT,
  schema_version TEXT NOT NULL,
  frame_id TEXT NOT NULL,
  extraction_confidence REAL,
  extraction_note TEXT NOT NULL,
  resolution_confidence REAL,
  resolution_note TEXT NOT NULL,
  source_reliability REAL,
  source_reliability_note TEXT NOT NULL,
  corroboration_ess REAL,
  corroboration_note TEXT NOT NULL,
  temporal_consistency REAL,
  temporal_note TEXT NOT NULL,
  verifier_agreement REAL,
  verifier_note TEXT NOT NULL,
  system_time TEXT NOT NULL,
  FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
  FOREIGN KEY (span_id) REFERENCES spans(span_id),
  FOREIGN KEY (document_version_id) REFERENCES document_versions(document_version_id),
  FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS pair_assessments (
  assessment_id TEXT PRIMARY KEY,
  claim_id_a TEXT NOT NULL,
  claim_id_b TEXT NOT NULL,
  method TEXT NOT NULL,
  subtype TEXT NOT NULL,
  predicted_incompatible INTEGER NOT NULL,
  valid_time_relation TEXT NOT NULL,
  abs_difference TEXT,
  tolerance TEXT,
  rationale TEXT NOT NULL,
  system_time TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  UNIQUE (claim_id_a, claim_id_b, method),
  FOREIGN KEY (claim_id_a) REFERENCES claims(claim_id),
  FOREIGN KEY (claim_id_b) REFERENCES claims(claim_id)
);

CREATE TABLE IF NOT EXISTS answers (
  answer_id TEXT PRIMARY KEY,
  question TEXT NOT NULL,
  state TEXT NOT NULL,
  persisted INTEGER NOT NULL,
  system_time TEXT NOT NULL,
  method TEXT NOT NULL,
  body_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  media_type TEXT NOT NULL,
  body_json TEXT NOT NULL,
  system_time TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_trial_predicate ON claims (trial_id, predicate);
CREATE INDEX IF NOT EXISTS idx_claims_document ON claims (document_id);
CREATE INDEX IF NOT EXISTS idx_spans_version ON spans (document_version_id);
CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions (document_id);
CREATE INDEX IF NOT EXISTS idx_versions_hash ON document_versions (content_hash);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type);
