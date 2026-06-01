"""Lightweight JSON + environment configuration (no cloud-specific overrides)."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "intake_config.json"

DEFAULTS: dict = {
    "SEC_API_DELAY": 0.15,
    "PIPELINE_MAX_DOCUMENTS": 5,
}


def load_config() -> dict:
    data = dict(DEFAULTS)
    override = os.environ.get("INTAKE_CONFIG_PATH", "").strip()
    for path in (override, str(DEFAULT_CONFIG_PATH)):
        if path and Path(path).is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
            break
    delay = float(data.get("SEC_API_DELAY", 0.15))
    data["SEC_API_DELAY"] = max(delay, 0.05)
    return data
