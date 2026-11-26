from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from evidenceai.paths import repo_root


@lru_cache(maxsize=1)
def load_pack() -> dict[str, Any]:
    path = repo_root() / "domain-packs" / "clinical" / "pack.json"
    return json.loads(path.read_text(encoding="utf-8"))


def predicate_record(predicate: str) -> dict[str, Any] | None:
    for item in load_pack()["predicates"]:
        if item["id"] == predicate:
            return item
    return None


def extractor_predicates() -> set[str]:
    return {
        item["id"]
        for item in load_pack()["predicates"]
        if item.get("extractor") == "clinical_pattern_v0"
    }
