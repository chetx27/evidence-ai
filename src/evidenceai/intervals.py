from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Interval:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("Interval start is after interval end.")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def overlaps(left: Interval, right: Interval) -> bool:
    return left.start <= right.end and right.start <= left.end


def relation(
    left_start: str | None,
    left_end: str | None,
    right_start: str | None,
    right_end: str | None,
) -> str:
    if not left_start or not left_end or not right_start or not right_end:
        return "unknown"
    left = Interval(parse_date(left_start), parse_date(left_end))
    right = Interval(parse_date(right_start), parse_date(right_end))
    if overlaps(left, right):
        return "overlap"
    return "non_overlap"
