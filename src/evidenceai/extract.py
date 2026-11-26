from __future__ import annotations

from dataclasses import dataclass, field

from evidenceai.frames import TEMPORAL_FRAME, Frame, frames_for
from evidenceai.textutil import iter_line_spans
from evidenceai.units import Quantity, normalize

BOILERPLATE_LINES = frozenset(
    {
        "SYNTHETIC DOCUMENT",
        "NOT A REAL TRIAL. NOT A REAL PATIENT RECORD. GENERATED FIXTURE.",
    }
)


@dataclass
class FoundClaim:
    frame: Frame
    line_start: int
    line_end: int
    line_text: str
    quantity: Quantity


@dataclass
class FoundTemporal:
    start: int
    end: int
    text: str
    valid_start: str
    valid_end: str


@dataclass
class Extraction:
    boilerplate: list[tuple[int, int, str]] = field(default_factory=list)
    temporal: list[FoundTemporal] = field(default_factory=list)
    claims: list[FoundClaim] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def extract_text(text: str, doc_type: str | None, language: str | None) -> Extraction:
    found = Extraction()
    claim_frames = frames_for(doc_type) if language == "en" and doc_type else []
    for line in iter_line_spans(text):
        if line.text in BOILERPLATE_LINES:
            found.boilerplate.append((line.start, line.end, line.text))
            continue
        if line.text == "":
            continue
        temporal_match = TEMPORAL_FRAME.regex().match(line.text)
        claim_hits = []
        for frame in claim_frames:
            match = frame.regex().match(line.text)
            if match:
                claim_hits.append((frame, match))
        if temporal_match and claim_hits:
            found.errors.append(f"line_matched_temporal_and_claim:{line.start}")
            continue
        if temporal_match:
            found.temporal.append(
                FoundTemporal(
                    start=line.start,
                    end=line.end,
                    text=line.text,
                    valid_start=temporal_match.group("start"),
                    valid_end=temporal_match.group("end"),
                )
            )
            continue
        if len(claim_hits) > 1:
            found.errors.append(f"line_matched_multiple_frames:{line.start}")
            continue
        if len(claim_hits) == 1:
            frame, match = claim_hits[0]
            token = match.group("num")
            assert frame.unit_kind is not None
            found.claims.append(
                FoundClaim(
                    frame=frame,
                    line_start=line.start,
                    line_end=line.end,
                    line_text=line.text,
                    quantity=normalize(token, frame.unit_kind),
                )
            )
    return found
