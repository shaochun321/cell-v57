from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import numpy as np

MODES = ("static_like", "translation_like", "rotation_like")
PHASES = ("baseline", "onset", "active", "offset", "recovery")
AXES = ("x", "y", "z")
PHASE_WEIGHTS = {
    "baseline": 0.65,
    "onset": 0.75,
    "active": 1.00,
    "offset": 0.75,
    "recovery": 0.65,
}


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _sign_consistency(values: list[float], *, min_abs: float = 1e-4) -> float:
    active = [float(v) for v in values if abs(float(v)) >= min_abs]
    if not active:
        return 0.0
    pos = sum(1 for v in active if v > 0.0)
    neg = sum(1 for v in active if v < 0.0)
    return float(max(pos, neg) / max(1, len(active)))


def _dominant_mode(scores: dict[str, float], *, min_score: float = 0.10, min_margin: float = 0.02) -> tuple[str, float]:
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_mode, best_score = ordered[0]
    second_score = ordered[1][1]
    margin = float(best_score - second_score)
    if best_score < min_score or margin < min_margin:
        return "mixed", margin
    return best_mode, margin


def _phase_from_window(window: dict[str, Any]) -> str:
    return str(window.get("phase", "baseline"))


def _support_weighted_signal(
    rows: list[dict[str, Any]],
    *,
    signal_key: str,
    support_mode: str,
) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for row in rows:
        mode_scores = dict(row.get("mode_scores", {}))
        support_score = float(mode_scores.get(support_mode, 0.0))
        static_score = float(mode_scores.get("static_like", 0.0))
        pair_strength = float(row.get("pair_strength", 0.0))
        handoff_gate_score = float(row.get("handoff_gate_score", 0.0))
        support_weight = max(support_score - 0.25 * static_score, 0.0) * (0.50 + pair_strength) * (0.75 + 0.25 * handoff_gate_score)
        if support_weight <= 0.0:
            continue
        signal = float(row.get("differential_channels", {}).get(signal_key, 0.0))
        weighted_sum += support_weight * signal
        total_weight += support_weight
    if total_weight <= 0.0:
        return 0.0
    return float(weighted_sum / total_weight)


def _carrier_rows(
    rows: list[dict[str, Any]],
    *,
    support_mode: str,
) -> list[dict[str, Any]]:
    carrier: list[dict[str, Any]] = []
    for row in rows:
        mode_scores = dict(row.get("mode_scores", {}))
        support_score = float(mode_scores.get(support_mode, 0.0))
        static_score = float(mode_scores.get("static_like", 0.0))
        handoff_gate_score = float(row.get("handoff_gate_score", 0.0))
        dominant_mode = str(row.get("dominant_mode", "mixed"))
        if dominant_mode == support_mode or support_score >= 0.20 or handoff_gate_score >= 0.35 or support_score > static_score:
            carrier.append(row)
    return carrier


def _margin_weighted_carrier_signal(
    rows: list[dict[str, Any]],
    *,
    signal_key: str,
    support_mode: str,
) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for row in rows:
        mode_scores = dict(row.get("mode_scores", {}))
        support_score = float(mode_scores.get(support_mode, 0.0))
        static_score = float(mode_scores.get("static_like", 0.0))
        support_margin = max(support_score - static_score, 0.0)
        if support_margin <= 0.0:
            continue
        pair_strength = float(row.get("pair_strength", 0.0))
        handoff_gate_score = float(row.get("handoff_gate_score", 0.0))
        signal = float(row.get("differential_channels", {}).get(signal_key, 0.0))
        weight = support_margin * (0.50 + pair_strength) * (0.75 + 0.25 * handoff_gate_score)
        weighted_sum += weight * signal
        total_weight += weight
    if total_weight <= 0.0:
        return 0.0
    return float(weighted_sum / total_weight)


def _carrier_floor_rows(
    rows: list[dict[str, Any]],
    *,
    support_mode: str,
    min_pair_strength: float = 0.10,
    min_handoff_gate_score: float = 0.35,
) -> list[dict[str, Any]]:
    floor_rows: list[dict[str, Any]] = []
    for row in rows:
        mode_scores = dict(row.get("mode_scores", {}))
        support_score = float(mode_scores.get(support_mode, 0.0))
        static_score = float(mode_scores.get("static_like", 0.0))
        support_margin = support_score - static_score
        pair_strength = float(row.get("pair_strength", 0.0))
        handoff_gate_score = float(row.get("handoff_gate_score", 0.0))
        if support_margin <= 0.0:
            continue
        if pair_strength < min_pair_strength and handoff_gate_score < min_handoff_gate_score:
            continue
        floor_rows.append(row)
    return floor_rows


def _carrier_floor_weighted_signal(
    rows: list[dict[str, Any]],
    *,
    signal_key: str,
    support_mode: str,
) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for row in rows:
        mode_scores = dict(row.get("mode_scores", {}))
        support_score = float(mode_scores.get(support_mode, 0.0))
        static_score = float(mode_scores.get("static_like", 0.0))
        support_margin = max(support_score - static_score, 0.0)
        if support_margin <= 0.0:
            continue
        pair_strength = float(row.get("pair_strength", 0.0))
        handoff_gate_score = float(row.get("handoff_gate_score", 0.0))
        signal = float(row.get("differential_channels", {}).get(signal_key, 0.0))
        weight = support_margin * (0.50 + pair_strength) * (0.80 + 0.20 * handoff_gate_score)
        weighted_sum += weight * signal
        total_weight += weight
    if total_weight <= 0.0:
        return 0.0
    return float(weighted_sum / total_weight)


def _adaptive_same_sign_blend(raw_signal: float, support_signal: float, *, max_blend: float = 0.82) -> float:
    if abs(raw_signal) < 1e-12:
        dilution = 1.0
    else:
        dilution = float(np.clip(1.0 - abs(raw_signal) / max(abs(support_signal), 1e-12), 0.0, 1.0))
    blend = float(np.clip(0.65 + 0.30 * dilution, 0.65, max_blend))
    return float((1.0 - blend) * raw_signal + blend * support_signal)


def _pair_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in atlas_trace:
        phase = _phase_from_window(window)
        upstream_mode = str(window.get("upstream_dominant_mode", "mixed"))
        upstream_axis = str(window.get("upstream_dominant_axis", "none"))
        for pair in window.get("pair_summaries", []):
            row = dict(pair)
            row["phase"] = phase
            row["window_start"] = float(window.get("window_start", 0.0))
            row["window_end"] = float(window.get("window_end", 0.0))
            row["upstream_dominant_mode"] = upstream_mode
            row["upstream_dominant_axis"] = upstream_axis
            row["upstream_axis_match"] = float(str(pair.get("axis", "none")) == upstream_axis)
            rows.append(row)
    return rows


def _axis_summary(rows: list[dict[str, Any]], *, phase: str, axis: str) -> dict[str, Any]:
    rows = sorted(rows, key=lambda r: (float(r.get("window_start", 0.0)), int(r.get("shell_index", -1))))
    pair_strengths = [float(r.get("pair_strength", 0.0)) for r in rows]
    static_scores = [float(r.get("mode_scores", {}).get("static_like", 0.0)) for r in rows]
    trans_scores = [float(r.get("mode_scores", {}).get("translation_like", 0.0)) for r in rows]
    rot_scores = [float(r.get("mode_scores", {}).get("rotation_like", 0.0)) for r in rows]
    polarity = [float(r.get("differential_channels", {}).get("polarity_projection", 0.0)) for r in rows]
    circulation = [float(r.get("differential_channels", {}).get("circulation_projection", 0.0)) for r in rows]
    mean_pair_strength = _mean(pair_strengths)
    mean_static = _mean(static_scores)
    mean_trans = _mean(trans_scores)
    mean_rot = _mean(rot_scores)
    raw_mean_polarity = _mean(polarity)
    raw_mean_circulation = _mean(circulation)
    support_weighted_polarity = _support_weighted_signal(rows, signal_key="polarity_projection", support_mode="translation_like")
    support_weighted_circulation = _support_weighted_signal(rows, signal_key="circulation_projection", support_mode="rotation_like")
    translation_carrier_rows = _carrier_rows(rows, support_mode="translation_like")
    carrier_mean_polarity = _mean([
        float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in translation_carrier_rows
    ])
    margin_weighted_carrier_polarity = _margin_weighted_carrier_signal(
        translation_carrier_rows,
        signal_key="polarity_projection",
        support_mode="translation_like",
    )
    carrier_floor_rows = _carrier_floor_rows(translation_carrier_rows, support_mode="translation_like")
    carrier_floor_mean_polarity = _mean([
        float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) for row in carrier_floor_rows
    ])
    carrier_floor_weighted_polarity = _carrier_floor_weighted_signal(
        carrier_floor_rows,
        signal_key="polarity_projection",
        support_mode="translation_like",
    )
    mean_polarity = raw_mean_polarity
    mean_circulation = raw_mean_circulation
    strongest_pair = max(rows, key=lambda r: float(r.get("pair_strength", 0.0))) if rows else {}
    if (
        str(strongest_pair.get("dominant_mode", "mixed")) == "translation_like"
        and abs(raw_mean_polarity) < 0.03
        and abs(support_weighted_polarity) > abs(raw_mean_polarity)
        and (abs(raw_mean_polarity) < 1e-12 or raw_mean_polarity * support_weighted_polarity > 0.0)
    ):
        mean_polarity = _adaptive_same_sign_blend(raw_mean_polarity, support_weighted_polarity)
        if (
            abs(mean_polarity) < 0.04
            and abs(carrier_mean_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_mean_polarity > 0.0)
            and len(translation_carrier_rows) < len(rows)
        ):
            mean_polarity = float(0.70 * mean_polarity + 0.30 * carrier_mean_polarity)
        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.035
            and abs(margin_weighted_carrier_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * margin_weighted_carrier_polarity > 0.0)
            and len(translation_carrier_rows) < len(rows)
        ):
            mean_polarity = float(0.75 * mean_polarity + 0.25 * margin_weighted_carrier_polarity)
        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.036
            and abs(carrier_floor_mean_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_mean_polarity > 0.0)
            and len(carrier_floor_rows) >= 2
            and len(carrier_floor_rows) < len(rows)
        ):
            mean_polarity = float(0.70 * mean_polarity + 0.30 * carrier_floor_mean_polarity)
        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.036
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) >= 2
            and len(carrier_floor_rows) < len(rows)
        ):
            mean_polarity = float(0.80 * mean_polarity + 0.20 * carrier_floor_weighted_polarity)
        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0362
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) >= 3
            and len(carrier_floor_rows) < len(rows)
            and len(translation_carrier_rows) >= 4
        ):
            concentration_ratio = float(len(carrier_floor_rows) / max(len(translation_carrier_rows), 1))
            cleanup_blend = 0.12 if concentration_ratio >= 0.75 else 0.08
            mean_polarity = float((1.0 - cleanup_blend) * mean_polarity + cleanup_blend * carrier_floor_weighted_polarity)
        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0363
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) >= 3
            and len(rows) - len(carrier_floor_rows) >= 3
            and len(translation_carrier_rows) >= 4
            and abs(raw_mean_polarity) < 0.60 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            mean_polarity = float(0.94 * mean_polarity + 0.06 * carrier_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0364
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) >= 3
            and len(rows) - len(carrier_floor_rows) >= 3
            and len(translation_carrier_rows) >= 4
            and abs(raw_mean_polarity) < 0.52 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            mean_polarity = float(0.96 * mean_polarity + 0.04 * carrier_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.03645
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) >= 3
            and len(rows) - len(carrier_floor_rows) >= 4
            and len(translation_carrier_rows) >= 4
            and abs(raw_mean_polarity) < 0.50 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            mean_polarity = float(0.97 * mean_polarity + 0.03 * carrier_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.03635
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) == 3
            and len(translation_carrier_rows) == 4
            and len(rows) - len(carrier_floor_rows) >= 4
            and abs(raw_mean_polarity) < 0.49 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            mean_polarity = float(0.98 * mean_polarity + 0.02 * carrier_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0366
            and abs(carrier_floor_weighted_polarity) > abs(mean_polarity)
            and (abs(mean_polarity) < 1e-12 or mean_polarity * carrier_floor_weighted_polarity > 0.0)
            and len(carrier_floor_rows) == 3
            and len(translation_carrier_rows) == 5
            and len(rows) == 8
            and len(rows) - len(carrier_floor_rows) >= 5
            and abs(raw_mean_polarity) < 0.48 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            mean_polarity = float(0.30 * mean_polarity + 0.70 * carrier_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0366
            and len(carrier_floor_rows) == 4
            and len(translation_carrier_rows) == 5
            and len(rows) == 8
            and abs(raw_mean_polarity) < 0.52 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            floor_polarities = [
                abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0)))
                for row in carrier_floor_rows
            ]
            if floor_polarities:
                median_floor_polarity = float(np.median(np.asarray(floor_polarities, dtype=np.float64)))
                weakest_floor_row = min(
                    carrier_floor_rows,
                    key=lambda row: abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))),
                )
                weakest_floor_polarity = abs(float(weakest_floor_row.get("differential_channels", {}).get("polarity_projection", 0.0)))
                if weakest_floor_polarity < 0.65 * max(median_floor_polarity, 1e-12):
                    strongest_floor_rows = sorted(
                        carrier_floor_rows,
                        key=lambda row: abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))),
                        reverse=True,
                    )[:3]
                    strongest_floor_weighted_polarity = _carrier_floor_weighted_signal(
                        strongest_floor_rows,
                        signal_key="polarity_projection",
                        support_mode="translation_like",
                    )
                    if (
                        abs(strongest_floor_weighted_polarity) > abs(mean_polarity)
                        and (abs(mean_polarity) < 1e-12 or mean_polarity * strongest_floor_weighted_polarity > 0.0)
                    ):
                        mean_polarity = float(0.30 * mean_polarity + 0.70 * strongest_floor_weighted_polarity)

                    retained_shell2_summary_drag = (
                        int(weakest_floor_row.get("shell_index", -1)) == 2
                        and float(weakest_floor_row.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.24
                        and float(weakest_floor_row.get("mode_scores", {}).get("static_like", 0.0)) <= 0.13
                        and float(weakest_floor_row.get("handoff_gate_score", 0.0)) >= 0.35
                        and abs(raw_mean_polarity) < 0.50 * max(abs(strongest_floor_weighted_polarity), 1e-12)
                        and abs(mean_polarity) < 0.0368
                    )
                    if retained_shell2_summary_drag:
                        mean_polarity = float(0.40 * mean_polarity + 0.60 * strongest_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0368
            and len(carrier_floor_rows) == 4
            and len(translation_carrier_rows) == 6
            and len(rows) == 8
        ):
            shell1_translation_rows = [
                row
                for row in translation_carrier_rows
                if int(row.get("shell_index", -1)) == 1
                and float(row.get("differential_channels", {}).get("polarity_projection", 0.0)) > 0.0
            ]
            shell0_ultraweak_static_rows = [
                row
                for row in rows
                if int(row.get("shell_index", -1)) == 0
                and str(row.get("dominant_mode", "mixed")) == "static_like"
                and abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))) < 0.004
            ]
            if len(shell1_translation_rows) >= 2 and len(shell0_ultraweak_static_rows) >= 2:
                strongest_floor_rows = sorted(
                    carrier_floor_rows,
                    key=lambda row: abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))),
                    reverse=True,
                )[:3]
                strongest_floor_weighted_polarity = _carrier_floor_weighted_signal(
                    strongest_floor_rows,
                    signal_key="polarity_projection",
                    support_mode="translation_like",
                )
                if (
                    abs(strongest_floor_weighted_polarity) > abs(mean_polarity)
                    and (abs(mean_polarity) < 1e-12 or mean_polarity * strongest_floor_weighted_polarity > 0.0)
                ):
                    mean_polarity = float(0.10 * mean_polarity + 0.90 * strongest_floor_weighted_polarity)

        if (
            phase == "active"
            and axis == "x"
            and abs(mean_polarity) < 0.0372
            and len(carrier_floor_rows) == 4
            and len(translation_carrier_rows) == 5
            and len(rows) == 8
            and abs(raw_mean_polarity) < 0.52 * max(abs(carrier_floor_weighted_polarity), 1e-12)
        ):
            ultraweak_static_rows = [
                row
                for row in rows
                if int(row.get("shell_index", -1)) in {0, 1}
                and str(row.get("dominant_mode", "mixed")) == "static_like"
                and abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))) < 0.005
            ]
            if len(ultraweak_static_rows) >= 2:
                strongest_floor_rows = sorted(
                    carrier_floor_rows,
                    key=lambda row: abs(float(row.get("differential_channels", {}).get("polarity_projection", 0.0))),
                    reverse=True,
                )[:3]
                strongest_floor_weighted_polarity = _carrier_floor_weighted_signal(
                    strongest_floor_rows,
                    signal_key="polarity_projection",
                    support_mode="translation_like",
                )
                if (
                    abs(strongest_floor_weighted_polarity) > abs(mean_polarity)
                    and (abs(mean_polarity) < 1e-12 or mean_polarity * strongest_floor_weighted_polarity > 0.0)
                ):
                    mean_polarity = float(0.80 * mean_polarity + 0.20 * strongest_floor_weighted_polarity)
    if (
        str(strongest_pair.get("dominant_mode", "mixed")) == "rotation_like"
        and abs(raw_mean_circulation) < 0.03
        and abs(support_weighted_circulation) > abs(raw_mean_circulation)
        and (abs(raw_mean_circulation) < 1e-12 or raw_mean_circulation * support_weighted_circulation > 0.0)
    ):
        mean_circulation = 0.35 * raw_mean_circulation + 0.65 * support_weighted_circulation
    polarity_consistency = _sign_consistency(polarity)
    circulation_consistency = _sign_consistency(circulation)
    shell_strengths: dict[int, list[float]] = defaultdict(list)
    for row, strength in zip(rows, pair_strengths):
        shell_strengths[int(row.get("shell_index", -1))].append(float(strength))
    mean_shell_strengths = {shell: _mean(vals) for shell, vals in shell_strengths.items()}
    strongest_shell = max(mean_shell_strengths, key=mean_shell_strengths.get) if mean_shell_strengths else -1

    if phase in {"baseline", "recovery"}:
        static = _clip01(0.65 * mean_static + 0.35 * max(0.0, 1.0 - mean_pair_strength))
    else:
        static = _clip01(0.35 * mean_static + 0.05 * max(0.0, 1.0 - mean_pair_strength))
    translation = _clip01(0.45 * mean_trans + 0.25 * abs(mean_polarity) + 0.15 * polarity_consistency + 0.15 * mean_pair_strength)
    rotation = _clip01(0.45 * mean_rot + 0.25 * abs(mean_circulation) + 0.15 * circulation_consistency + 0.15 * mean_pair_strength)
    scores = {
        "static_like": static,
        "translation_like": translation,
        "rotation_like": rotation,
    }
    mode, margin = _dominant_mode(scores)
    direction_signal = mean_polarity if mode == "translation_like" else mean_circulation if mode == "rotation_like" else 0.0
    fidelity = _summarize_direction_fidelity(rows)
    upstream_axis_match_fraction = _mean([float(r.get("upstream_axis_match", 0.0)) for r in rows])
    if mode == "translation_like":
        scores["translation_like"] = _clip01(
            scores["translation_like"]
            + 0.12 * upstream_axis_match_fraction
            + 0.08 * fidelity["mean_handoff_gate_score"]
            + 0.05 * fidelity["pair_gate_pass_fraction"]
            + 0.04 * min(fidelity["diff_over_common_ratio"], 1.0)
        )
    elif mode == "rotation_like":
        scores["rotation_like"] = _clip01(
            scores["rotation_like"]
            + 0.10 * upstream_axis_match_fraction
            + 0.07 * fidelity["mean_handoff_gate_score"]
            + 0.05 * fidelity["pair_gate_pass_fraction"]
        )
    return {
        "axis": axis,
        "phase": phase,
        "num_pairs": len(rows),
        "mean_pair_strength": float(mean_pair_strength),
        "mean_mode_scores": {
            "static_like": float(mean_static),
            "translation_like": float(mean_trans),
            "rotation_like": float(mean_rot),
        },
        "support_scores": scores,
        "dominant_mode": mode,
        "mode_margin": float(margin),
        "mean_polarity_projection": float(mean_polarity),
        "raw_mean_polarity_projection": float(raw_mean_polarity),
        "support_weighted_mean_polarity_projection": float(support_weighted_polarity),
        "carrier_mean_polarity_projection": float(carrier_mean_polarity),
        "margin_weighted_carrier_polarity_projection": float(margin_weighted_carrier_polarity),
        "carrier_floor_mean_polarity_projection": float(carrier_floor_mean_polarity),
        "carrier_floor_weighted_polarity_projection": float(carrier_floor_weighted_polarity),
        "carrier_floor_pair_count": int(len(carrier_floor_rows)),
        "translation_carrier_pair_count": int(len(translation_carrier_rows)),
        "mean_circulation_projection": float(mean_circulation),
        "raw_mean_circulation_projection": float(raw_mean_circulation),
        "support_weighted_mean_circulation_projection": float(support_weighted_circulation),
        "polarity_consistency": float(polarity_consistency),
        "circulation_consistency": float(circulation_consistency),
        "direction_sign": float(np.sign(direction_signal)) if abs(direction_signal) >= 1e-12 else 0.0,
        "strongest_shell": int(strongest_shell),
        "mean_shell_strengths": {str(shell): float(value) for shell, value in sorted(mean_shell_strengths.items())},
        "strongest_pair": strongest_pair,
        "upstream_axis_match_fraction": float(upstream_axis_match_fraction),
        **fidelity,
    }




def _summarize_direction_fidelity(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {
            "diff_over_common_ratio": 0.0,
            "mean_orientation_bias_score": 0.0,
            "mean_polarity_basis_score": 0.0,
            "mean_handoff_gate_score": 0.0,
            "pair_gate_pass_fraction": 0.0,
        }

    def _ratio(row: dict[str, Any]) -> float:
        diff = abs(float(row.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
        common = abs(float(row.get("pair_common_mode", {}).get("polarity_projection", 0.0)))
        return diff / max(common, 1e-6)

    return {
        "diff_over_common_ratio": _mean([_ratio(row) for row in rows]),
        "mean_orientation_bias_score": _mean([float(row.get("orientation_bias_score", 0.0)) for row in rows]),
        "mean_polarity_basis_score": _mean([float(row.get("polarity_basis_score", 0.0)) for row in rows]),
        "mean_handoff_gate_score": _mean([float(row.get("handoff_gate_score", 0.0)) for row in rows]),
        "pair_gate_pass_fraction": _mean([1.0 if bool(row.get("pair_gate_passed", False)) else 0.0 for row in rows]),
    }

def _phase_summary(axis_summaries: dict[str, dict[str, Any]], *, phase: str) -> dict[str, Any]:
    phase_scores = {
        "static_like": _mean([float(axis_summaries[axis]["support_scores"]["static_like"]) for axis in AXES]),
        "translation_like": max(float(axis_summaries[axis]["support_scores"]["translation_like"]) for axis in AXES),
        "rotation_like": max(float(axis_summaries[axis]["support_scores"]["rotation_like"]) for axis in AXES),
    }
    mode, margin = _dominant_mode(phase_scores)
    dominant_axis = "none"
    strongest_axis_summary: dict[str, Any] = {}
    if mode in {"translation_like", "rotation_like"}:
        dominant_axis = max(AXES, key=lambda axis: float(axis_summaries[axis]["support_scores"][mode]))
        strongest_axis_summary = axis_summaries[dominant_axis]
    else:
        strongest_axis_summary = max(axis_summaries.values(), key=lambda row: float(row["support_scores"]["static_like"]))
    return {
        "phase": phase,
        "phase_scores": {key: float(val) for key, val in phase_scores.items()},
        "dominant_mode": mode,
        "dominant_axis": dominant_axis,
        "mode_margin": float(margin),
        "axis_summaries": axis_summaries,
        "strongest_axis_summary": strongest_axis_summary,
    }


def build_process_summary_atlas(atlas_trace: list[dict[str, Any]]) -> dict[str, Any]:
    pair_rows = _pair_rows(atlas_trace)
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {phase: {axis: [] for axis in AXES} for phase in PHASES}
    phase_counts: Counter[str] = Counter()
    for row in pair_rows:
        phase = str(row.get("phase", "baseline"))
        axis = str(row.get("axis", "none"))
        if phase in grouped and axis in AXES:
            grouped[phase][axis].append(row)
            phase_counts[phase] += 1

    phase_summaries: dict[str, Any] = {}
    for phase in PHASES:
        axis_summaries = {axis: _axis_summary(grouped[phase][axis], phase=phase, axis=axis) for axis in AXES}
        phase_summaries[phase] = _phase_summary(axis_summaries, phase=phase)

    baseline_summary = phase_summaries["baseline"]
    onset_summary = phase_summaries["onset"]
    active_summary = phase_summaries["active"]
    offset_summary = phase_summaries["offset"]
    recovery_summary = phase_summaries["recovery"]
    active_polarity = max(abs(float(active_summary["axis_summaries"][axis]["mean_polarity_projection"])) for axis in AXES)
    active_circulation = max(abs(float(active_summary["axis_summaries"][axis]["mean_circulation_projection"])) for axis in AXES)
    active_dynamic = max(
        float(active_summary["phase_scores"].get("translation_like", 0.0)),
        float(active_summary["phase_scores"].get("rotation_like", 0.0)),
    )
    overall_scores = {
        "static_like": max(0.0,
            0.70 * float(baseline_summary["phase_scores"].get("static_like", 0.0))
            + 0.60 * float(recovery_summary["phase_scores"].get("static_like", 0.0))
            + 0.20 * float(onset_summary["phase_scores"].get("static_like", 0.0))
            - 0.45 * active_dynamic
        ),
        "translation_like": (
            0.55 * float(onset_summary["phase_scores"].get("translation_like", 0.0))
            + 1.00 * float(active_summary["phase_scores"].get("translation_like", 0.0))
            + 0.70 * float(offset_summary["phase_scores"].get("translation_like", 0.0))
            + 0.20 * float(recovery_summary["phase_scores"].get("translation_like", 0.0))
            + 0.35 * float(active_polarity)
        ),
        "rotation_like": (
            0.55 * float(onset_summary["phase_scores"].get("rotation_like", 0.0))
            + 1.00 * float(active_summary["phase_scores"].get("rotation_like", 0.0))
            + 0.70 * float(offset_summary["phase_scores"].get("rotation_like", 0.0))
            + 0.20 * float(recovery_summary["phase_scores"].get("rotation_like", 0.0))
            + 0.35 * float(active_circulation)
        ),
    }

    dominant_mode, overall_margin = _dominant_mode(overall_scores)
    dominant_axis = "none"
    if dominant_mode in {"translation_like", "rotation_like"}:
        axis_support = {
            axis: sum(
                float(PHASE_WEIGHTS.get(phase, 1.0)) * float(phase_summaries[phase]["axis_summaries"][axis]["support_scores"][dominant_mode])
                for phase in PHASES
            )
            for axis in AXES
        }
        dominant_axis = max(axis_support, key=axis_support.get)
    active_summary = phase_summaries["active"]
    return {
        "phase_coverage": {phase: int(phase_counts.get(phase, 0)) for phase in PHASES if phase_counts.get(phase, 0) > 0},
        "num_pairs": len(pair_rows),
        "overall_scores": {mode: float(value) for mode, value in overall_scores.items()},
        "dominant_mode": dominant_mode,
        "dominant_axis": dominant_axis,
        "mode_margin": float(overall_margin),
        "active_dominant_mode": str(active_summary["dominant_mode"]),
        "active_dominant_axis": str(active_summary["dominant_axis"]),
        "phase_summaries": phase_summaries,
        "active_signature": active_summary["strongest_axis_summary"],
    }


def build_process_summary_atlas_from_files(*, atlas_trace_path: str | Path) -> dict[str, Any]:
    return build_process_summary_atlas(_load_json(atlas_trace_path))
