# EvidenceAI

EvidenceAI is claim-centric evidence infrastructure. A finding is a claim with a span, a time interval, a provenance record, and a visible uncertainty, not a paragraph retrieved for a chat model.

The atomic unit is the claim: who asserted what, when, with what hedging, and whether separate sources agree. Documents, entities, and passages are supporting structure.

This repository is version **0.1.0**. It is the Gate 1 library for one flagship slice: synthetic clinical trial documents. Scores on that slice are **not yet measured**.

## Status

Present in this commit:

- An append-only SQLite event log and a relational projection for documents, spans, sources, entities, claims, and numeric pair assessments (`schemas/sql/001_init.sql`).
- EB-Synth v0, a specification-fixed generator of 50 synthetic English trial texts (10 fictional trials, five document types each). The generator does not call a language model. Seed `20261126` is registered and is not a random draw.
- A frame-bound extractor, `clinical_pattern_v0`, for `sample_size`, `hazard_ratio`, and `hba1c_change`.
- A numeric rule (`numeric_rule_v0`) and a surface-string baseline. Tolerances live in `eval/preregistration_ebsynth_v0.json` and were written before any measurement.
- A quotation check that accepts a factual sentence only when the sentence is the cited span.
- Clinical domain pack `0.1.0`. Source reliability priors are not applied. Hindi and Kannada are named as planned languages and are not implemented.

Later Gate 1 work, absent from this commit:

- `evidenceai.cli`, the HTTP service, the interface, the test suite, and CI.
- A logged harness report. `make slice`, `make harness`, `make serve`, `make ui`, and `make ci` name those entrypoints. Running them fails until those files exist.
- `python -m evidenceai` imports `evidenceai.cli`, which is not in the tree.
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
| Headline metric (pre-registered, not yet measured) | false-conflict rate |
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

That prints `0.1.0`. It does not run a corpus.

Generate the fixture only (writes text files, does not open the database):

```bash
python -c "from pathlib import Path; from evidenceai.synth import generate_corpus; print(generate_corpus(Path('data/slice/corpus'))['document_count'])"
```

`data/` is gitignored. The printed document count is the generator's own manifest field for that call.

## Models and deployment

This commit makes no network call and loads no weights. Extraction is the sentence-frame matcher. An open-weights or API model gateway is future work. The intended Gate 1 process bind is loopback only; that server is not in this commit.

There is no authentication layer here. Do not expose a later server beyond localhost until that layer exists.

## License

`pyproject.toml` declares Apache-2.0. The full license text is not yet vendored in the repository.
