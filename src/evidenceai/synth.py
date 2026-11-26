from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evidenceai.constants import (
    GENERATOR_ID,
    GENERATOR_VERSION,
    REGISTERED_SEED,
    SYNTHETIC_BANNER,
)
from evidenceai.frames import TEMPORAL_FRAME, frames_for, render
from evidenceai.ids import sha256_bytes, stable_id
from evidenceai.units import format_decimal, normalize

DOC_TYPES = (
    "registry",
    "protocol",
    "publication",
    "press_release",
    "regulatory_summary",
)
RESULT_DOCS = ("publication", "press_release", "regulatory_summary")
DATES = {
    "registry": "2021-02-01",
    "protocol": "2021-03-15",
    "publication": "2023-05-20",
    "press_release": "2023-05-21",
    "regulatory_summary": "2023-11-02",
}
PERIOD = ("2021-06-01", "2022-12-31")
INDICATION = "type 2 diabetes mellitus"
SOURCES = {
    "registry": "Synthetic Registry",
    "protocol": "Synthetic Protocol Archive",
    "publication": "Synthetic Journal",
    "press_release": "Synthetic Press Wire",
    "regulatory_summary": "Synthetic Regulator",
}
ENDPOINT_LINE = "The primary endpoint is change in HbA1c at week 24."


@dataclass(frozen=True)
class ClaimSpec:
    doc_type: str
    predicate: str
    token: str
    unit_kind: str
    latent: str


@dataclass(frozen=True)
class UnsupportedSpec:
    doc_type: str
    predicate: str
    sentence: str
    latent: str
    reason: str


@dataclass(frozen=True)
class TrialSpec:
    trial_id: str
    compound: str
    claims: tuple[ClaimSpec, ...]
    unsupported: tuple[UnsupportedSpec, ...] = ()
    extras: tuple[tuple[str, tuple[str, ...]], ...] = ()


def _n(token: str, latent: str | None = None) -> dict[str, ClaimSpec]:
    value = latent if latent is not None else token
    return {doc: ClaimSpec(doc, "sample_size", token, "count", value) for doc in DOC_TYPES}


def _hr(token: str, latent: str | None = None) -> dict[str, ClaimSpec]:
    value = latent if latent is not None else token
    return {doc: ClaimSpec(doc, "hazard_ratio", token, "ratio", value) for doc in RESULT_DOCS}


def _a1c(token: str, latent: str | None = None) -> dict[str, ClaimSpec]:
    value = latent if latent is not None else token
    return {doc: ClaimSpec(doc, "hba1c_change", token, "percent", value) for doc in RESULT_DOCS}


def _merge(*groups: dict[str, ClaimSpec]) -> tuple[ClaimSpec, ...]:
    claims: list[ClaimSpec] = []
    for group in groups:
        claims.extend(group.values())
    return tuple(claims)


def build_trials() -> tuple[TrialSpec, ...]:
    n1 = _n("240")
    hr1 = _hr("0.74")
    hr1["press_release"] = ClaimSpec("press_release", "hazard_ratio", "0.740", "ratio", "0.74")
    a1 = _a1c("-1.2")

    n2 = _n("180")
    n2["press_release"] = ClaimSpec(
        "press_release", "sample_size", "0.180", "count_thousand", "180"
    )
    hr2 = _hr("0.81")
    a2 = _a1c("-0.8")

    n3 = _n("320")
    hr3 = _hr("0.74")
    hr3["press_release"] = ClaimSpec("press_release", "hazard_ratio", "0.742", "ratio", "0.74")
    a3 = _a1c("-1.0")

    n4 = _n("500")
    hr4 = _hr("0.66")
    a4 = _a1c("-1.2")
    a4["regulatory_summary"] = ClaimSpec(
        "regulatory_summary", "hba1c_change", "-0.012", "fraction", "-1.2"
    )

    n5 = _n("240")
    n5["publication"] = ClaimSpec("publication", "sample_size", "218", "count", "218")
    hr5 = _hr("0.90")
    a5 = _a1c("-0.5")

    n6 = _n("400")
    n6["publication"] = ClaimSpec("publication", "sample_size", "360", "count", "360")
    hr6 = _hr("1.02")
    a6 = _a1c("-0.4")

    n7 = _n("150")
    hr7 = _hr("0.74")
    hr7["press_release"] = ClaimSpec("press_release", "hazard_ratio", "1.15", "ratio", "1.15")
    a7 = _a1c("-0.6")

    n8 = _n("240")
    del n8["publication"]
    hr8 = _hr("0.88")
    a8 = _a1c("-0.9")
    unsupported8 = (
        UnsupportedSpec(
            "publication",
            "sample_size",
            "The randomized sample size was two hundred forty participants.",
            "240",
            "spelled_out_number",
        ),
    )

    n9 = _n("275")
    hr9 = _hr("0.74")
    hr9["press_release"] = ClaimSpec("press_release", "hazard_ratio", "0.746", "ratio", "0.74")
    a9 = _a1c("-1.1")

    n10 = _n("1000")
    hr10 = _hr("0.69")
    a10 = _a1c("-1.4")
    extras10 = (
        (
            "publication",
            (
                "The trial was conducted at 24 sites.",
                "The confidence interval was 0.61 to 0.89.",
            ),
        ),
    )

    rows = [
        ("SYNTH-001", "ZQ-17", _merge(n1, hr1, a1), (), ()),
        ("SYNTH-002", "ZQ-18", _merge(n2, hr2, a2), (), ()),
        ("SYNTH-003", "ZQ-19", _merge(n3, hr3, a3), (), ()),
        ("SYNTH-004", "ZQ-20", _merge(n4, hr4, a4), (), ()),
        ("SYNTH-005", "ZQ-21", _merge(n5, hr5, a5), (), ()),
        ("SYNTH-006", "ZQ-22", _merge(n6, hr6, a6), (), ()),
        ("SYNTH-007", "ZQ-23", _merge(n7, hr7, a7), (), ()),
        ("SYNTH-008", "ZQ-24", _merge(n8, hr8, a8), unsupported8, ()),
        ("SYNTH-009", "ZQ-25", _merge(n9, hr9, a9), (), ()),
        ("SYNTH-010", "ZQ-26", _merge(n10, hr10, a10), (), extras10),
    ]
    trials = []
    for trial_id, compound, claims, unsupported, extras in rows:
        trials.append(
            TrialSpec(
                trial_id=trial_id,
                compound=compound,
                claims=claims,
                unsupported=unsupported,
                extras=extras,
            )
        )
    return tuple(trials)


def _frame_for(spec: ClaimSpec):
    matches = [
        frame
        for frame in frames_for(spec.doc_type)
        if frame.predicate == spec.predicate and frame.unit_kind == spec.unit_kind
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one frame for "
            f"{spec.doc_type} {spec.predicate} {spec.unit_kind}, found {len(matches)}."
        )
    return matches[0]


def render_document(trial: TrialSpec, doc_type: str) -> str:
    extras = dict(trial.extras).get(doc_type, ())
    unsupported = [item.sentence for item in trial.unsupported if item.doc_type == doc_type]
    claim_lines = []
    for spec in trial.claims:
        if spec.doc_type != doc_type:
            continue
        frame = _frame_for(spec)
        claim_lines.append(render(frame, num=spec.token))
    lines = [
        "SYNTHETIC DOCUMENT",
        "NOT A REAL TRIAL. NOT A REAL PATIENT RECORD. GENERATED FIXTURE.",
        "Language: en",
        f"Document type: {doc_type}",
        f"Trial: {trial.trial_id}",
        f"Compound: {trial.compound}",
        f"Indication: {INDICATION}",
        f"Document date: {DATES[doc_type]}",
        f"Source: {SOURCES[doc_type]}",
        "",
        render(TEMPORAL_FRAME, start=PERIOD[0], end=PERIOD[1]),
        ENDPOINT_LINE,
        *claim_lines,
        *unsupported,
        *extras,
    ]
    return "\n".join(lines) + "\n"


def doc_key(trial_id: str, doc_type: str) -> str:
    return f"{trial_id}__{doc_type}"


def generate_corpus(corpus_dir: Path) -> dict[str, object]:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    trials = build_trials()
    documents = []
    assertions = []
    unsupported = []
    for trial in trials:
        for doc_type in DOC_TYPES:
            key = doc_key(trial.trial_id, doc_type)
            text = render_document(trial, doc_type)
            data = text.encode("utf-8")
            path = corpus_dir / f"{key}.txt"
            path.write_bytes(data)
            documents.append(
                {
                    "doc_key": key,
                    "trial_id": trial.trial_id,
                    "doc_type": doc_type,
                    "filename": path.name,
                    "content_hash": sha256_bytes(data),
                    "byte_length": len(data),
                }
            )
        for spec in trial.claims:
            key = doc_key(trial.trial_id, spec.doc_type)
            quantity = normalize(spec.token, spec.unit_kind)
            assertions.append(
                {
                    "assertion_id": stable_id(
                        "as", key, spec.predicate, spec.token, spec.unit_kind
                    ),
                    "doc_key": key,
                    "trial_id": trial.trial_id,
                    "doc_type": spec.doc_type,
                    "predicate": spec.predicate,
                    "raw_token": spec.token,
                    "unit_kind": spec.unit_kind,
                    "latent": spec.latent,
                    "expected_canonical": format_decimal(quantity.canonical),
                    "extractable": True,
                }
            )
        for item in trial.unsupported:
            unsupported.append(
                {
                    "doc_key": doc_key(trial.trial_id, item.doc_type),
                    "trial_id": trial.trial_id,
                    "doc_type": item.doc_type,
                    "predicate": item.predicate,
                    "sentence": item.sentence,
                    "latent": item.latent,
                    "reason": item.reason,
                    "extractable": False,
                }
            )
    if len(documents) != 50:
        raise RuntimeError(f"EB-Synth v0 must write 50 documents, wrote {len(documents)}.")
    return {
        "corpus_label": "synthetic",
        "disclaimer": SYNTHETIC_BANNER,
        "generator_id": GENERATOR_ID,
        "generator_version": GENERATOR_VERSION,
        "seed_policy": "specification-fixed",
        "registered_seed": REGISTERED_SEED,
        "rng": None,
        "document_count": len(documents),
        "documents": documents,
        "assertions": assertions,
        "unsupported_frames": unsupported,
    }
