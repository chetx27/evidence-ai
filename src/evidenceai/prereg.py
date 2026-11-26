from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from typing import Any

from evidenceai.paths import repo_root


@lru_cache(maxsize=1)
def load_prereg() -> dict[str, Any]:
    path = repo_root() / "eval" / "preregistration_ebsynth_v0.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ratio_tolerance() -> Decimal:
    return Decimal(str(load_prereg()["ratio_rounding_abs"]))


def percent_tolerance() -> Decimal:
    return Decimal(str(load_prereg()["percent_rounding_abs"]))


def registered_questions() -> list[str]:
    return list(load_prereg()["registered_questions"])
