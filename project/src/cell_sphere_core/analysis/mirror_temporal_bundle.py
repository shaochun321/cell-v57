from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import numpy as np

MODES = ("static_like", "translation_like", "rotation_like")
PHASES = ("baseline", "onset", "active", "offset", "recovery")


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _phase_presence(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("phase", "baseline")) for row in rows)
    return {phase: int(counts.get(phase, 0)) for phase in PHASES if counts.get(phase, 0) > 0}


def _mode_presence(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("dominant_mode", "mixed")) for row in rows)
    return {mode: int(counts.get(mode, 0)) for mode in set(counts)}


def _sign_consistency(values: list[float], *, min_abs: float = 1e-4) -> float:
    active = [float(v) for v in values if abs(float(v)) >= min_abs]
    if not active:
        return 0.0
    pos = sum(1 for v in active if v > 0.0)
    neg = sum(1 for v in active if v < 0.0)
    return float(max(pos, neg) / max(1, len(active)))


def _axis_consistency(rows: list[dict[str, Any]], axis: str) -> float:
    if not rows:
        return 0.0
    matches = sum(1 for row in rows if str(row.get("axis", "none")) == axis)
    return float(matches / len(rows))


def _bundle_scores(rows: list[dict[str, Any]]) -> dict[str, float]:
    active_rows = [row for row in rows if str(row.get("phase", "baseline")) == "active"]
    baseline_rows = [row for row in rows if str(row.get("phase", "baseline")) == "baseline"]
    recovery_rows = [row for row in rows if str(row.get("phase", "baseline")) == "recovery"]

    active_pair_strength = _mean([float(row.get("pair_strength", 0.0)) for row in active_rows])
    active_translation = _mean([float(row.get("mode_scores", {}).get("translation_like", 0.0)) for row in active_rows])
    active_rotation = _mean([float(row.get("mode_scores", {}).get("rotation_like", 0.0)) for row in active_rows])
    baseline_static = _mean([float(row.get("mode_scores", {}).get("static_like", 0.0)) for row in baseline_rows])
    recovery_static = _mean([float(row.get("mode_scores", {}).get("static_like", 0.0)) for row in recovery_rows])

    polarity_values = [float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in active_rows]
    circulation_values = [float(row.get("differential_channels", {}).get("circulation_projection", 0.0)) for row in active_rows]
    axis = str(rows[0].get("axis", "none")) if rows else "none"
    axis_consistency = _axis_consistency(active_rows, axis)
    polarity_consistency = _sign_consistency(polarity_values)
    circulation_consistency = _sign_consistency(circulation_values)

    translation = _clip01(
        0.45 * active_translation
        + 0.20 * active_pair_strength
        + 0.20 * polarity_consistency
        + 0.15 * axis_consistency
    )
    rotation = _clip01(
        0.45 * active_rotation
        + 0.20 * active_pair_strength
        + 0.20 * circulation_consistency
        + 0.15 * axis_consistency
    )
    static = _clip01(
        0.40 * baseline_static
        + 0.40 * recovery_static
        + 0.20 * max(0.0, 1.0 - active_pair_strength)
    )
    return {
        "static_like": static,
        "translation_like": translation,
        "rotation_like": rotation,
    }


def _dominant_mode(scores: dict[str, float], *, min_score: float = 0.16, min_margin: float = 0.02) -> tuple[str, float]:
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_mode, best_score = ordered[0]
    second_score = ordered[1][1]
    margin = float(best_score - second_score)
    if best_score < min_score or margin < min_margin:
        return "mixed", margin
    return best_mode, margin


def _bundle_record(pair_key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = sorted(rows, key=lambda row: float(row.get("window_start", 0.0)))
    axis = str(rows[0].get("axis", "none")) if rows else "none"
    shell_index = int(rows[0].get("shell_index", -1)) if rows else -1
    scores = _bundle_scores(rows)
    mode, margin = _dominant_mode(scores)
    active_rows = [row for row in rows if str(row.get("phase", "baseline")) == "active"]
    baseline_rows = [row for row in rows if str(row.get("phase", "baseline")) == "baseline"]
    recovery_rows = [row for row in rows if str(row.get("phase", "baseline")) == "recovery"]
    polarity_active = _mean([float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in active_rows])
    circulation_active = _mean([float(row.get("differential_channels", {}).get("circulation_projection", 0.0)) for row in active_rows])
    polarity_recovery = _mean([float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in recovery_rows])
    circulation_recovery = _mean([float(row.get("differential_channels", {}).get("circulation_projection", 0.0)) for row in recovery_rows])
    active_strength = _mean([float(row.get("pair_strength", 0.0)) for row in active_rows])
    baseline_strength = _mean([float(row.get("pair_strength", 0.0)) for row in baseline_rows])
    recovery_strength = _mean([float(row.get("pair_strength", 0.0)) for row in recovery_rows])
    recovery_ratio = _clip01(recovery_strength / max(active_strength, 1e-6)) if active_strength > 0.0 else 0.0
    sign_signal = polarity_active if mode == "translation_like" else circulation_active if mode == "rotation_like" else 0.0
    return {
        "pair_key": pair_key,
        "shell_index": shell_index,
        "axis": axis,
        "phase_counts": _phase_presence(rows),
        "mode_counts": _mode_presence(rows),
        "mode_scores": scores,
        "dominant_mode": mode,
        "dominant_axis": axis if mode in {"translation_like", "rotation_like"} else "none",
        "mode_margin": float(margin),
        "active_pair_strength": float(active_strength),
        "baseline_pair_strength": float(baseline_strength),
        "recovery_pair_strength": float(recovery_strength),
        "recovery_ratio": float(recovery_ratio),
        "active_polarity_projection": float(polarity_active),
        "active_circulation_projection": float(circulation_active),
        "recovery_polarity_projection": float(polarity_recovery),
        "recovery_circulation_projection": float(circulation_recovery),
        "polarity_consistency": float(_sign_consistency([float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in active_rows])),
        "circulation_consistency": float(_sign_consistency([float(row.get("differential_channels", {}).get("circulation_projection", 0.0)) for row in active_rows])),
        "direction_sign": float(np.sign(sign_signal)) if abs(sign_signal) >= 1e-12 else 0.0,
        "window_start": float(rows[0].get("window_start", 0.0)) if rows else 0.0,
        "window_end": float(rows[-1].get("window_end", 0.0)) if rows else 0.0,
    }


def _window_rows_to_pair_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in atlas_trace:
        phase = str(window.get("phase", "baseline"))
        window_start = float(window.get("window_start", 0.0))
        window_end = float(window.get("window_end", 0.0))
        for pair in window.get("pair_summaries", []):
            row = dict(pair)
            row["phase"] = phase
            row["window_start"] = window_start
            row["window_end"] = window_end
            rows.append(row)
    return rows


def build_mirror_temporal_bundle_trace(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _window_rows_to_pair_rows(atlas_trace):
        grouped[str(row.get("pair_key", "none"))].append(row)
    bundles = [_bundle_record(pair_key, rows) for pair_key, rows in sorted(grouped.items())]
    bundles.sort(key=lambda row: (row.get("shell_index", -1), row.get("axis", "none")))
    return bundles


def build_mirror_temporal_bundle_trace_from_files(*, atlas_trace_path: str | Path) -> list[dict[str, Any]]:
    return build_mirror_temporal_bundle_trace(_load_json(atlas_trace_path))


def _bundle_support(row: dict[str, Any], mode: str) -> float:
    if mode == "translation_like":
        return float(row.get("mode_scores", {}).get("translation_like", 0.0)) + 0.35 * abs(float(row.get("active_polarity_projection", 0.0)))
    if mode == "rotation_like":
        return float(row.get("mode_scores", {}).get("rotation_like", 0.0)) + 0.35 * abs(float(row.get("active_circulation_projection", 0.0)))
    if mode == "static_like":
        return float(row.get("mode_scores", {}).get("static_like", 0.0)) + 0.20 * float(row.get("recovery_pair_strength", 0.0))
    return float(row.get("active_pair_strength", 0.0))


def summarize_mirror_temporal_bundle_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_bundles": 0,
            "dominant_mode": "none",
            "dominant_axis": "none",
            "phase_coverage": {},
            "overall_scores": {},
            "active_summary": {},
            "mean_active_pair_strength": 0.0,
            "bundle_count_by_mode": {},
        }

    mode_counts = Counter(str(row.get("dominant_mode", "mixed")) for row in trace)
    phase_coverage: Counter[str] = Counter()
    for row in trace:
        for phase, count in dict(row.get("phase_counts", {})).items():
            phase_coverage[str(phase)] += int(count)

    overall_scores = {mode: 0.0 for mode in MODES}
    for row in trace:
        mode_scores = dict(row.get("mode_scores", {}))
        active_strength = float(row.get("active_pair_strength", 0.0))
        recovery_strength = float(row.get("recovery_pair_strength", 0.0))
        overall_scores["static_like"] += 0.65 * float(mode_scores.get("static_like", 0.0)) + 0.10 * recovery_strength
        overall_scores["translation_like"] += (
            0.60 * float(mode_scores.get("translation_like", 0.0))
            + 0.20 * active_strength
            + 0.20 * abs(float(row.get("active_polarity_projection", 0.0)))
        )
        overall_scores["rotation_like"] += (
            0.60 * float(mode_scores.get("rotation_like", 0.0))
            + 0.20 * active_strength
            + 0.20 * abs(float(row.get("active_circulation_projection", 0.0)))
        )
    dominant_mode, _ = _dominant_mode(overall_scores, min_score=0.25, min_margin=0.015)
    if dominant_mode == "mixed":
        dominant_mode = max(overall_scores.items(), key=lambda kv: kv[1])[0]

    support_by_axis = defaultdict(float)
    axis_mode = dominant_mode if dominant_mode in {"translation_like", "rotation_like"} else "static_like"
    for row in trace:
        axis = str(row.get("axis", "none"))
        if axis == "none":
            continue
        mode_scores = dict(row.get("mode_scores", {}))
        active_strength = float(row.get("active_pair_strength", 0.0))
        support_by_axis[axis] += float(mode_scores.get(axis_mode, 0.0)) * (0.35 + active_strength)
    dominant_axis = max(support_by_axis.items(), key=lambda kv: kv[1])[0] if support_by_axis and axis_mode != "static_like" else "none"

    active_candidates = [
        row for row in trace
        if int(dict(row.get("phase_counts", {})).get("active", 0)) > 0
    ]
    if not active_candidates:
        active_candidates = trace

    support_by_mode = defaultdict(float)
    for row in active_candidates:
        for mode in MODES:
            support_by_mode[mode] += _bundle_support(row, mode)
    active_mode = max(support_by_mode.items(), key=lambda kv: kv[1])[0] if support_by_mode else dominant_mode
    mode_candidates = [row for row in active_candidates if str(row.get("dominant_mode", "mixed")) == active_mode]
    if not mode_candidates:
        mode_candidates = active_candidates
    strongest_bundle = max(mode_candidates, key=lambda row: _bundle_support(row, active_mode))
    active_summary = {
        "dominant_mode": str(strongest_bundle.get("dominant_mode", "none")),
        "dominant_axis": str(strongest_bundle.get("dominant_axis", "none")),
        "strongest_bundle": strongest_bundle,
    }
    return {
        "num_bundles": int(len(trace)),
        "dominant_mode": dominant_mode,
        "dominant_axis": dominant_axis,
        "phase_coverage": {phase: int(count) for phase, count in phase_coverage.items()},
        "overall_scores": {mode: float(score) for mode, score in overall_scores.items()},
        "active_summary": active_summary,
        "mean_active_pair_strength": _mean([float(row.get("active_pair_strength", 0.0)) for row in trace]),
        "bundle_count_by_mode": {mode: int(count) for mode, count in mode_counts.items()},
    }
