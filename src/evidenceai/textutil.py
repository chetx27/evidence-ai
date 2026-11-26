from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineSpan:
    start: int
    end: int
    text: str


def iter_line_spans(text: str) -> list[LineSpan]:
    spans: list[LineSpan] = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        content = raw[:-1] if raw.endswith("\n") else raw
        if content.endswith("\r"):
            content = content[:-1]
        spans.append(LineSpan(offset, offset + len(content), content))
        offset += len(raw)
    return spans
