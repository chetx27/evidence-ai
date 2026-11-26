from __future__ import annotations

import re
from dataclasses import dataclass

from evidenceai.pack import extractor_predicates

_NUM = {
    "count": r"\d+",
    "count_thousand": r"\d+\.\d+",
    "ratio": r"[+-]?\d+(?:\.\d+)?",
    "percent": r"[+-]?\d+(?:\.\d+)?",
    "fraction": r"[+-]?\d+(?:\.\d+)?",
}
_DATE = r"\d{4}-\d{2}-\d{2}"


@dataclass(frozen=True)
class Frame:
    frame_id: str
    kind: str
    predicate: str | None
    doc_type: str | None
    unit_kind: str | None
    modality: str
    polarity: str
    hedging: str
    template: str

    def regex(self) -> re.Pattern[str]:
        pattern = re.escape(self.template)
        if self.kind == "temporal":
            pattern = pattern.replace(re.escape("{start}"), f"(?P<start>{_DATE})")
            pattern = pattern.replace(re.escape("{end}"), f"(?P<end>{_DATE})")
        else:
            assert self.unit_kind is not None
            pattern = pattern.replace(
                re.escape("{num}"),
                f"(?P<num>{_NUM[self.unit_kind]})",
            )
        return re.compile("^" + pattern + "$")


def _claim(
    frame_id: str,
    predicate: str,
    doc_type: str,
    unit_kind: str,
    template: str,
) -> Frame:
    return Frame(
        frame_id=frame_id,
        kind="claim",
        predicate=predicate,
        doc_type=doc_type,
        unit_kind=unit_kind,
        modality="asserted",
        polarity="affirmative",
        hedging="none",
        template=template,
    )


FRAMES: tuple[Frame, ...] = (
    _claim(
        "registry_sample_count",
        "sample_size",
        "registry",
        "count",
        "This registry entry records planned enrollment of {num} participants.",
    ),
    _claim(
        "protocol_sample_count",
        "sample_size",
        "protocol",
        "count",
        "The protocol sets the planned sample size at {num} participants.",
    ),
    _claim(
        "publication_sample_count",
        "sample_size",
        "publication",
        "count",
        "The randomized sample size was {num} participants.",
    ),
    _claim(
        "press_sample_count",
        "sample_size",
        "press_release",
        "count",
        "The sponsor announced that the study enrolled {num} participants.",
    ),
    _claim(
        "press_sample_thousand",
        "sample_size",
        "press_release",
        "count_thousand",
        "The sponsor announced that the study enrolled {num} thousand participants.",
    ),
    _claim(
        "regulatory_sample_count",
        "sample_size",
        "regulatory_summary",
        "count",
        "The regulatory summary records a sample size of {num} participants.",
    ),
    _claim(
        "publication_hr",
        "hazard_ratio",
        "publication",
        "ratio",
        "The hazard ratio for the primary comparison was {num}.",
    ),
    _claim(
        "press_hr",
        "hazard_ratio",
        "press_release",
        "ratio",
        "The press release states a hazard ratio of {num}.",
    ),
    _claim(
        "regulatory_hr",
        "hazard_ratio",
        "regulatory_summary",
        "ratio",
        "The regulatory summary states a hazard ratio of {num}.",
    ),
    _claim(
        "publication_hba1c",
        "hba1c_change",
        "publication",
        "percent",
        "The primary endpoint result was a change of {num} percent in HbA1c.",
    ),
    _claim(
        "press_hba1c",
        "hba1c_change",
        "press_release",
        "percent",
        "The press release reports an HbA1c change of {num} percent.",
    ),
    _claim(
        "regulatory_hba1c_percent",
        "hba1c_change",
        "regulatory_summary",
        "percent",
        "The regulatory summary reports an HbA1c change of {num} percent.",
    ),
    _claim(
        "regulatory_hba1c_fraction",
        "hba1c_change",
        "regulatory_summary",
        "fraction",
        "The regulatory summary reports an HbA1c change of {num} fraction.",
    ),
)

TEMPORAL_FRAME = Frame(
    frame_id="study_period",
    kind="temporal",
    predicate=None,
    doc_type=None,
    unit_kind=None,
    modality="asserted",
    polarity="affirmative",
    hedging="none",
    template="The study period was {start} to {end}.",
)


def assert_frames_match_pack() -> None:
    allowed = extractor_predicates()
    for frame in FRAMES:
        if frame.predicate not in allowed:
            raise RuntimeError(
                f"Frame {frame.frame_id} uses predicate {frame.predicate}, "
                "which the clinical pack does not assign to clinical_pattern_v0."
            )


def render(frame: Frame, **values: str) -> str:
    line = frame.template.format(**values)
    if frame.regex().match(line) is None:
        raise RuntimeError(f"Rendered frame {frame.frame_id} does not match its derived pattern.")
    return line


def frames_for(doc_type: str | None) -> list[Frame]:
    return [frame for frame in FRAMES if frame.doc_type == doc_type]
