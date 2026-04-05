from __future__ import annotations

from pathlib import Path
from typing import Any

from .global_overview import extract_overview_features
from .global_overview_hhd_lite import extract_hhd_lite_features


def extract_hybrid_overview_features(run_dir: Path, tail: int = 3) -> dict[str, float]:
    feats: dict[str, float] = {}
    feats.update(extract_overview_features(run_dir, tail=tail))
    feats.update(extract_hhd_lite_features(run_dir))
    return feats
