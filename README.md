# EvidenceAI

EvidenceAI is claim-centric evidence infrastructure. A finding is a claim with a span, a time interval, a provenance record, and a visible uncertainty, not a paragraph retrieved for a chat model.

The atomic unit is the claim: who asserted what, when, with what hedging, and whether separate sources agree. Documents, entities, and passages are supporting structure.

This repository is version **0.1.0**. It is the Gate 1 library for one flagship slice: synthetic clinical trial documents. The fixture diagnostic is the logged run in `eval/logs/gate1.json`. That log is a census of EB-Synth v0, not a generalization claim.

## Status

Present in this commit:

- An append-only SQLite event log and a relational projection for documents, spans, sources, entities, claims, and numeric pair assessments (`schemas/sql/001_init.sql`).
- EB-Synth v0, a specification-fixed generator of 50 synthetic English trial texts (10 fictional trials, five document types each). The generator does not call a language model. Seed `20261126` is registered and is not a random draw.
- A frame-bound extractor, `clinical_pattern_v0`, for `sample_size`, `hazard_ratio`, and `hba1c_change`.
- A numeric rule (`numeric_rule_v0`) and a surface-string baseline. Tolerances live in `eval/preregistration_ebsynth_v0.json` and were written before any measurement.
- A quotation check that accepts a factual sentence only when the sentence is the cited span.
- Clinical domain pack `0.1.0`. Source reliability priors are not applied. Hindi and Kannada are named as planned languages and are not implemented.

Present as of the pipeline commit:

- `evidenceai.cli slice` builds the corpus, the event log, the graph projection, and the three registered answers.
- `evidenceai.cli harness` scores that database and writes `eval/logs/gate1.json`. The numbers in that file are the run. This README does not copy them.
- Tests in `tests/` cover unit normalization, the quotation check, quarantine, exact-byte duplicates, unsupported language, the 50-document slice, idempotent replay, and assertion-time filtering.

Present as of the read-interface commit:

- A loopback HTTP API. `python -m evidenceai serve` binds `127.0.0.1:8000` and refuses other hosts unless `--allow-remote` is set. There is still no authentication.
- A React interface in `frontend/` with document span highlights, numeric triage, investigate, and the fixture diagnostic.
- GitHub Actions workflow `.github/workflows/ci.yml` runs pytest and the frontend build.

Later Gate 1 work, absent from this commit:

- Research charter, architecture decision records, and the semantics document.
- PDF, OCR, learned extractors, entity-resolution models, and any non-English corpus.

No number in this file is an experimental result.

## Flagship slice

The year-1 flagship used here is clinical evidence: registry entry, protocol, publication, press release, and regulatory summary for the same fictional trial.

Every generated document is labeled synthetic. Compounds are named `ZQ-17` onward. Indications, dates, and outcomes are fixture data. They are not real trials, real patients, or real publications.

| Item | Value |
| --- | --- |
| Pack | `clinical` `0.1.0` |
| Language implemented | English |
| Documents per run of the generator | 50 |
| Registered seed | `20261126` |
| Schema | `ceg-0.1.0` |
| Headline metric | false-conflict rate, logged in `eval/logs/gate1.json` |
| Ratio rounding tolerance | `0.005` absolute |
| Percent rounding tolerance | `0.05` absolute |
| Counts | exact after scale normalization |

Scale rules, also pre-registered: a token marked "thousand" is multiplied by 1000 and compared as a count; a fraction is multiplied by 100 and compared as a percent. Pairs whose valid-time intervals are missing or disjoint are not called numeric conflicts.

The fixture includes reporting traps (trailing zeros, thousands, percent versus fraction, rounding inside and outside the tolerance) and real numeric disagreements (sample size, hazard ratio). One sample size is spelled out in words so the frame extractor misses it on purpose. That miss is part of the registered fixture, not a hidden failure.

## Repository layout

```text
domain-packs/clinical/pack.json          ontology, predicates, expected slots
eval/preregistration_ebsynth_v0.json     authoritative numeric pre-registration
schemas/sql/001_init.sql                 event log and projections
src/evidenceai/                          library
frontend/                                read interface
.github/workflows/ci.yml                 pytest and the frontend build
```

| Module | Role |
| --- | --- |
| `synth.py` | Writes the 50-document fixture and its manifest |
| `ingest.py` | Content-addressed ingest, exact-byte duplicates, quarantine |
| `extract.py` | Line frames to spans and quantities |
| `materialize.py` | Spans, claims, and pair assessments as events |
| `contradict.py` | Numeric rule and surface-string baseline |
| `investigate.py` | Answers limited to registered question forms, quoted spans only |
| `verify.py` | Quotation check |
| `confidence.py` | Composition of calibrated components; nulls stay null |
| `store.py` | Append-only events and rebuildable projections |
| `api.py` | Read-only HTTP API over the projection |

Objects are inserted. A replacement document version is a new row plus a supersession event. Confidence fields stay null until a calibration run exists. Null is not stored as zero.

## Local setup

Requires Python 3.9 or newer. This tree was developed on Python 3.9.6.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
export PYTHONPATH=src
```

Import check:

```bash
python -c "import evidenceai; print(evidenceai.__version__)"
```

That prints `0.1.0`.

Run the slice and the fixture diagnostic:

```bash
python -m evidenceai slice --out data/slice
python -m evidenceai harness --db data/slice/evidence.db --out eval/logs/gate1.json
python -m evidenceai serve --db data/slice/evidence.db
```

In another shell, from `frontend/`:

```bash
npm install
npm run dev
```

The dev server is `http://127.0.0.1:5173` and proxies `/api` to the loopback API. `make test` lints and runs pytest. `data/` is gitignored. The harness JSON is the logged result for that working tree.

## Models and deployment

Extraction is the sentence-frame matcher. An open-weights or API model gateway is future work. The read API binds to loopback. It has no authentication, so leave `--allow-remote` unset.

## License

`pyproject.toml` declares Apache-2.0. The full license text is not yet vendored in the repository.
