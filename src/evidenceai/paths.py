from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("EVIDENCEAI_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").exists() and (candidate / "schemas").exists():
            return candidate
    raise RuntimeError("Could not locate the EvidenceAI repository root.")
