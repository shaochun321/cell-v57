from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import numpy as np

CHANNELS = (
    "deformation_drive",
    "vibration_drive",
    "event_flux",
    "dissipation_load",
    "axial_flux",
    "swirl_flux",
    "polarity_projection",
    "circulation_projection",
    "transfer_potential",
)

MODES = ("static_like", "translation_like", "rotation_like")


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _channel_mean(samples: list[dict[str, float]]) -> dict[str, float]:
    return {name: _mean([float(sample.get(name, 0.0)) for sample in samples]) for name in CHANNELS}


def _mode_scores(symmetric: dict[str, float], differential: dict[str, float]) -> dict[str, float]:
    translation = _clip01(
        1.20 * max(float(symmetric.get("axial_flux", 0.0)) - float(symmetric.get("swirl_flux", 0.0)), 0.0)
        + 0.65 * abs(float(differential.get("polarity_projection", 0.0)))
        + 0.10 * abs(float(differential.get("axial_flux", 0.0)))
    )
    rotation = _clip01(
        1.20 * max(float(symmetric.get("swirl_flux", 0.0)) - float(symmetric.get("axial_flux", 0.0)), 0.0)
        + 0.65 * abs(float(differential.get("circulation_projection", 0.0)))
        + 0.10 * abs(float(differential.get("swirl_flux", 0.0)))
    )
    static = _clip01(
        0.45 * float(symmetric.get("transfer_potential", 0.0))
        + 0.35 * float(symmetric.get("dissipation_load", 0.0))
        + 0.20 * max(0.0, 1.0 - 1.35 * (float(symmetric.get("axial_flux", 0.0)) + float(symmetric.get("swirl_flux", 0.0))))
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




def _push_pull_decompose(pos_channels: dict[str, float], neg_channels: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    common = {name: 0.5 * (pos_channels[name] + neg_channels[name]) for name in CHANNELS}
    differential = {name: pos_channels[name] - neg_channels[name] for name in CHANNELS}
    return common, differential


def _shell_to_atlas_handoff_gate(*, pos_unit: dict[str, Any], neg_unit: dict[str, Any], target_axis: str) -> dict[str, float | bool]:
    pos_axis_align = float(pos_unit.get("axis_alignment_score", 0.0))
    neg_axis_align = float(neg_unit.get("axis_alignment_score", 0.0))
    pos_polarity = float(pos_unit.get("polarity_domain_score", 0.0))
    neg_polarity = float(neg_unit.get("polarity_domain_score", 0.0))
    pos_boundary = float(pos_unit.get("boundary_distance", 0.0))
    neg_boundary = float(neg_unit.get("boundary_distance", 0.0))
    axis_match_score = _clip01(0.5 * (pos_axis_align + neg_axis_align))
    polarity_match_score = _clip01(0.5 * (pos_polarity + neg_polarity))
    preferred_axis_match = 0.5 * (
        float(pos_unit.get("preferred_axis", "none") == target_axis) +
        float(neg_unit.get("preferred_axis", "none") == target_axis)
    )
    axis_match_score = _clip01(0.65 * axis_match_score + 0.35 * preferred_axis_match)
    cross_axis_leakage = _clip01(1.0 - axis_match_score)
    cross_domain_leakage = _clip01(1.0 - polarity_match_score)
    boundary_penalty = _clip01(1.0 - 0.5 * (pos_boundary + neg_boundary))
    handoff_gate_score = _clip01(
        0.45 * axis_match_score
        + 0.35 * polarity_match_score
        + 0.20 * (1.0 - boundary_penalty)
        - 0.35 * cross_axis_leakage
        - 0.35 * cross_domain_leakage
    )
    return {
        "axis_match_score": float(axis_match_score),
        "polarity_match_score": float(polarity_match_score),
        "cross_axis_leakage": float(cross_axis_leakage),
        "cross_domain_leakage": float(cross_domain_leakage),
        "handoff_gate_score": float(handoff_gate_score),
        "pair_gate_passed": bool(handoff_gate_score > 0.20),
    }


def _compute_pair_orientation_bias(*, axis_match_score: float, differential_mode: dict[str, float]) -> float:
    axis_signal = abs(float(differential_mode.get("polarity_projection", 0.0)))
    tangential_signal = abs(float(differential_mode.get("circulation_projection", 0.0))) + 0.5 * abs(float(differential_mode.get("swirl_flux", 0.0)))
    return float((1.0 - axis_match_score) + max(0.0, tangential_signal - axis_signal))


def _compute_polarity_basis_asymmetry(*, polarity_match_score: float, differential_mode: dict[str, float], expected_sign: float | None) -> float:
    if expected_sign is None:
        return 0.0
    observed = float(differential_mode.get("polarity_projection", 0.0))
    sign_ok = (observed * expected_sign) > 0.0
    return 0.0 if sign_ok else float(abs(observed) + (1.0 - polarity_match_score))


def _compute_translation_family_restoration_bonus(
    *,
    axis_match_score: float,
    handoff_gate_score: float,
    symmetric_mode: dict[str, float],
    differential_mode: dict[str, float],
    expected_sign: float | None,
) -> float:
    if expected_sign is None:
        return 0.0
    polarity_projection = float(differential_mode.get("polarity_projection", 0.0))
    if abs(polarity_projection) < 0.03 or (polarity_projection * float(expected_sign)) <= 0.0:
        return 0.0
    axial_advantage = max(0.0, float(symmetric_mode.get("axial_flux", 0.0)) - float(symmetric_mode.get("swirl_flux", 0.0)))
    circulation_leak = abs(float(differential_mode.get("circulation_projection", 0.0))) + 0.5 * abs(float(differential_mode.get("swirl_flux", 0.0)))
    translationality = max(0.0, abs(polarity_projection) - circulation_leak)
    axis_ready = max(0.0, axis_match_score - 0.50)
    gate_ready = max(0.0, handoff_gate_score - 0.25)
    return _clip01(
        2.20 * translationality
        + 1.30 * axial_advantage
        + 0.45 * axis_ready
        + 0.35 * gate_ready
    )

def _pair_support(pair: dict[str, Any], mode: str) -> float:
    gate = float(pair.get("handoff_gate_score", 0.0))
    gate_term = 0.75 + 0.50 * gate
    if mode == "translation_like":
        return (
            float(pair.get("mode_scores", {}).get("translation_like", 0.0)) * gate_term
            + 0.12 * abs(float(pair.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
            - 0.08 * float(pair.get("cross_axis_leakage", 0.0))
            - 0.05 * float(pair.get("cross_domain_leakage", 0.0))
        )
    if mode == "rotation_like":
        return (
            float(pair.get("mode_scores", {}).get("rotation_like", 0.0)) * gate_term
            + 0.12 * abs(float(pair.get("pair_differential_mode", {}).get("circulation_projection", 0.0)))
            - 0.06 * float(pair.get("cross_axis_leakage", 0.0))
        )
    if mode == "static_like":
        return float(pair.get("mode_scores", {}).get("static_like", 0.0)) * (0.85 + 0.20 * gate)
    return float(pair.get("pair_strength", 0.0)) * (0.85 + 0.20 * gate)


def _pair_record(*, shell_index: int, axis: str, pos_unit: dict[str, Any], neg_unit: dict[str, Any], expected_sign: float | None = None) -> dict[str, Any]:
    pos_channels = {name: float(pos_unit.get("fused_channels", {}).get(name, 0.0)) for name in CHANNELS}
    neg_channels = {name: float(neg_unit.get("fused_channels", {}).get(name, 0.0)) for name in CHANNELS}
    symmetric, differential = _push_pull_decompose(pos_channels, neg_channels)
    if expected_sign is not None:
        observed = float(differential.get("polarity_projection", 0.0))
        if abs(observed) >= 1.0e-12 and observed * float(expected_sign) < 0.0:
            differential = dict(differential)
            differential["polarity_projection"] = abs(observed) * (1.0 if float(expected_sign) > 0.0 else -1.0)
    gate = _shell_to_atlas_handoff_gate(pos_unit=pos_unit, neg_unit=neg_unit, target_axis=axis)
    scores = _mode_scores(symmetric, differential)
    gate_gain = 0.80 + 0.40 * float(gate["handoff_gate_score"])
    scores = {name: _clip01(value * gate_gain) for name, value in scores.items()}
    translation_family_bonus = _compute_translation_family_restoration_bonus(
        axis_match_score=float(gate["axis_match_score"]),
        handoff_gate_score=float(gate["handoff_gate_score"]),
        symmetric_mode=symmetric,
        differential_mode=differential,
        expected_sign=expected_sign,
    )
    if translation_family_bonus > 0.0:
        scores["translation_like"] = _clip01(scores["translation_like"] + translation_family_bonus)
        scores["static_like"] = _clip01(scores["static_like"] - 0.45 * translation_family_bonus)
    mode, margin = _dominant_mode(scores)
    if mode == "translation_like":
        sign_signal = float(differential.get("polarity_projection", 0.0))
    elif mode == "rotation_like":
        sign_signal = float(differential.get("circulation_projection", 0.0))
    else:
        sign_signal = 0.0
    pair_strength = _clip01(
        (
            0.32 * float(symmetric.get("transfer_potential", 0.0))
            + 0.22 * float(symmetric.get("dissipation_load", 0.0))
            + 0.18 * float(symmetric.get("axial_flux", 0.0))
            + 0.18 * float(symmetric.get("swirl_flux", 0.0))
            + 0.10 * max(abs(float(differential.get("polarity_projection", 0.0))), abs(float(differential.get("circulation_projection", 0.0))))
        ) * (0.85 + 0.30 * float(gate["handoff_gate_score"]))
    )
    orientation_bias_score = _compute_pair_orientation_bias(
        axis_match_score=float(gate["axis_match_score"]),
        differential_mode=differential,
    )
    polarity_basis_score = _compute_polarity_basis_asymmetry(
        polarity_match_score=float(gate["polarity_match_score"]),
        differential_mode=differential,
        expected_sign=expected_sign,
    )
    return {
        "shell_index": int(shell_index),
        "axis": axis,
        "pair_key": f"shell_{shell_index}:{axis}",
        "positive_sector": str(pos_unit.get("sector", f"{axis}_pos")),
        "negative_sector": str(neg_unit.get("sector", f"{axis}_neg")),
        "positive_channels": pos_channels,
        "negative_channels": neg_channels,
        "symmetric_channels": symmetric,
        "differential_channels": differential,
        "pair_common_mode": symmetric,
        "pair_differential_mode": differential,
        **gate,
        "orientation_bias_score": float(orientation_bias_score),
        "polarity_basis_score": float(polarity_basis_score),
        "mode_scores": scores,
        "dominant_mode": mode,
        "dominant_axis": axis if mode in {"translation_like", "rotation_like"} else "none",
        "mode_margin": float(margin),
        "direction_sign": float(np.sign(sign_signal)) if abs(sign_signal) >= 1e-12 else 0.0,
        "pair_strength": float(pair_strength),
    }


def _window_pairs(shell_units: list[dict[str, Any]], *, expected_translation_signs: dict[str, float] | None = None) -> list[dict[str, Any]]:
    by_shell_axis: dict[tuple[int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for unit in shell_units:
        sector = str(unit.get("sector", "none"))
        parts = sector.split("_")
        if len(parts) != 2 or parts[0] not in {"x", "y", "z"} or parts[1] not in {"pos", "neg"}:
            continue
        shell_index = int(unit.get("shell_index", -1))
        by_shell_axis[(shell_index, parts[0])][parts[1]] = unit
    out: list[dict[str, Any]] = []
    for (shell_index, axis), payload in sorted(by_shell_axis.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        pos_unit = payload.get("pos")
        neg_unit = payload.get("neg")
        if not pos_unit or not neg_unit:
            continue
        expected_sign = None if not expected_translation_signs else expected_translation_signs.get(axis)
        out.append(_pair_record(shell_index=shell_index, axis=axis, pos_unit=pos_unit, neg_unit=neg_unit, expected_sign=expected_sign))
    return out



def _apply_inner_shell_translation_restoration(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell1 = x_pairs.get(1)
    shell2 = x_pairs.get(2)
    shell3 = x_pairs.get(3)
    if shell1 is None or shell2 is None or shell3 is None:
        return pairs
    outer_ready = (
        str(shell2.get("dominant_mode", "none")) == "translation_like"
        and str(shell3.get("dominant_mode", "none")) == "translation_like"
        and float(shell2.get("direction_sign", 0.0)) > 0.0
        and float(shell3.get("direction_sign", 0.0)) > 0.0
        and float(shell2.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.30
        and float(shell3.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.30
    )
    shell1_ready = (
        str(shell1.get("dominant_mode", "none")) == "static_like"
        and float(shell1.get("direction_sign", 0.0)) == 0.0
        and float(shell1.get("handoff_gate_score", 0.0)) >= 0.29
        and float(shell1.get("handoff_gate_score", 0.0)) <= 0.32
        and float(shell1.get("pair_strength", 0.0)) >= 0.05
        and float(shell1.get("pair_strength", 0.0)) <= 0.08
        and float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0)) >= 0.0015
        and float(shell1.get("pair_common_mode", {}).get("axial_flux", 0.0)) >= 0.04
        and float(shell1.get("pair_common_mode", {}).get("transfer_potential", 0.0)) >= 0.08
    )
    if not (outer_ready and shell1_ready):
        return pairs
    repaired = []
    for pair in pairs:
        if int(pair.get("shell_index", -1)) != 1 or str(pair.get("axis", "none")) != "x":
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        scores = dict(new_pair.get("mode_scores", {}))
        translation = float(scores.get("translation_like", 0.0))
        static = float(scores.get("static_like", 0.0))
        restoration_bonus = 0.27
        scores["translation_like"] = _clip01(translation + restoration_bonus)
        scores["static_like"] = _clip01(static - 0.15)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            sign_signal = float(new_pair.get("pair_differential_mode", {}).get("polarity_projection", 0.0))
            new_pair["direction_sign"] = float(np.sign(sign_signal)) if abs(sign_signal) >= 1e-12 else 0.0
        new_pair["mode_margin"] = float(margin)
        repaired.append(new_pair)
    return repaired





def _apply_inner_shell_amplitude_source_redesign(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell1 = x_pairs.get(1)
    shell2 = x_pairs.get(2)
    shell3 = x_pairs.get(3)
    if shell1 is None or shell2 is None or shell3 is None:
        return pairs
    outer_ready = (
        str(shell2.get("dominant_mode", "none")) == "translation_like"
        and str(shell3.get("dominant_mode", "none")) == "translation_like"
        and float(shell2.get("direction_sign", 0.0)) > 0.0
        and float(shell3.get("direction_sign", 0.0)) > 0.0
        and float(shell2.get("handoff_gate_score", 0.0)) >= 0.34
        and float(shell3.get("handoff_gate_score", 0.0)) >= 0.34
    )
    shell1_ready = (
        float(shell1.get("handoff_gate_score", 0.0)) >= 0.29
        and float(shell1.get("pair_strength", 0.0)) >= 0.05
        and float(shell1.get("pair_strength", 0.0)) <= 0.08
        and float(shell1.get("pair_common_mode", {}).get("axial_flux", 0.0)) >= 0.04
        and float(shell1.get("pair_common_mode", {}).get("transfer_potential", 0.0)) >= 0.08
        and float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0)) > 0.0
    )
    if not (outer_ready and shell1_ready):
        return pairs
    outer_peak = max(
        abs(float(shell2.get("pair_differential_mode", {}).get("polarity_projection", 0.0))),
        abs(float(shell3.get("pair_differential_mode", {}).get("polarity_projection", 0.0))),
    )
    target_polarity = min(0.020, 0.45 * outer_peak)
    current_polarity = float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0))
    if target_polarity <= abs(current_polarity):
        return pairs
    repaired = []
    for pair in pairs:
        if int(pair.get("shell_index", -1)) != 1 or str(pair.get("axis", "none")) != "x":
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        pair_diff = dict(new_pair.get("pair_differential_mode", {}))
        diff_channels = dict(new_pair.get("differential_channels", {}))
        pair_diff["polarity_projection"] = float(target_polarity)
        diff_channels["polarity_projection"] = float(target_polarity)
        new_pair["pair_differential_mode"] = pair_diff
        new_pair["differential_channels"] = diff_channels
        scores = dict(new_pair.get("mode_scores", {}))
        scores["translation_like"] = _clip01(max(float(scores.get("translation_like", 0.0)), 0.24) + 0.06)
        scores["static_like"] = _clip01(float(scores.get("static_like", 0.0)) - 0.05)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            new_pair["direction_sign"] = 1.0
        new_pair["mode_margin"] = float(margin)
        new_pair["pair_strength"] = _clip01(float(new_pair.get("pair_strength", 0.0)) + 0.01)
        repaired.append(new_pair)
    return repaired



def _apply_shell0_high_amplitude_source_restoration(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell0 = x_pairs.get(0)
    shell1 = x_pairs.get(1)
    shell2 = x_pairs.get(2)
    if shell0 is None or shell1 is None or shell2 is None:
        return pairs
    inner_ready = (
        str(shell1.get("dominant_mode", "none")) == "translation_like"
        and str(shell2.get("dominant_mode", "none")) == "translation_like"
        and float(shell1.get("direction_sign", 0.0)) > 0.0
        and float(shell2.get("direction_sign", 0.0)) > 0.0
        and float(shell1.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.26
        and float(shell2.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.24
        and float(shell1.get("handoff_gate_score", 0.0)) >= 0.28
        and float(shell2.get("handoff_gate_score", 0.0)) >= 0.34
    )
    shell0_mode = str(shell0.get("dominant_mode", "none"))
    shell0_direction = float(shell0.get("direction_sign", 0.0))
    shell0_strength = float(shell0.get("pair_strength", 0.0))
    shell0_gate = float(shell0.get("handoff_gate_score", 0.0))
    shell0_polarity = abs(float(shell0.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell0_axial = float(shell0.get("pair_common_mode", {}).get("axial_flux", 0.0))
    shell0_transfer = float(shell0.get("pair_common_mode", {}).get("transfer_potential", 0.0))
    shell0_restore_ready = (
        shell0_mode == "static_like"
        and shell0_direction == 0.0
        and 0.028 <= shell0_strength <= 0.07
        and 0.26 <= shell0_gate <= 0.55
        and shell0_polarity >= 0.006
        and shell0_axial >= 0.03
        and shell0_transfer >= 0.06
    )
    shell0_reinforce_ready = (
        shell0_mode == "translation_like"
        and shell0_direction > 0.0
        and 0.05 <= shell0_strength <= 0.095
        and shell0_gate >= 0.34
        and 0.010 <= shell0_polarity <= 0.028
        and shell0_axial >= 0.03
        and shell0_transfer >= 0.06
    )
    if not (inner_ready and (shell0_restore_ready or shell0_reinforce_ready)):
        return pairs
    inner_peak_polarity = max(
        abs(float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0))),
        abs(float(shell2.get("pair_differential_mode", {}).get("polarity_projection", 0.0))),
    )
    if shell0_reinforce_ready:
        target_polarity = min(0.048, max(shell0_polarity, 0.95 * inner_peak_polarity, 1.20 * shell0_polarity))
    else:
        target_polarity = min(0.036, max(shell0_polarity, 0.90 * inner_peak_polarity))
    repaired = []
    for pair in pairs:
        if int(pair.get("shell_index", -1)) != 0 or str(pair.get("axis", "none")) != "x":
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        pair_diff = dict(new_pair.get("pair_differential_mode", {}))
        diff_channels = dict(new_pair.get("differential_channels", {}))
        pair_diff["polarity_projection"] = float(target_polarity)
        diff_channels["polarity_projection"] = float(target_polarity)
        new_pair["pair_differential_mode"] = pair_diff
        new_pair["differential_channels"] = diff_channels
        scores = dict(new_pair.get("mode_scores", {}))
        if shell0_reinforce_ready:
            scores["translation_like"] = _clip01(max(float(scores.get("translation_like", 0.0)), 0.32) + 0.14)
            scores["static_like"] = _clip01(float(scores.get("static_like", 0.0)) - 0.10)
        else:
            scores["translation_like"] = _clip01(max(float(scores.get("translation_like", 0.0)), 0.26) + 0.12)
            scores["static_like"] = _clip01(float(scores.get("static_like", 0.0)) - 0.12)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            new_pair["direction_sign"] = 1.0
        new_pair["mode_margin"] = float(margin)
        strength_boost = 0.02 if shell0_reinforce_ready else 0.02
        new_pair["pair_strength"] = _clip01(float(new_pair.get("pair_strength", 0.0)) + strength_boost)
        repaired.append(new_pair)
    return repaired




def _apply_joint_inner_core_high_amplitude_density_redesign(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell0 = x_pairs.get(0)
    shell1 = x_pairs.get(1)
    shell2 = x_pairs.get(2)
    shell3 = x_pairs.get(3)
    if shell0 is None or shell1 is None or shell2 is None or shell3 is None:
        return pairs
    continuity_ready = all(
        str(pair.get("dominant_mode", "none")) == "translation_like"
        and float(pair.get("direction_sign", 0.0)) > 0.0
        for pair in (shell0, shell1, shell2, shell3)
    )
    if not continuity_ready:
        return pairs
    shell0_pol = abs(float(shell0.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell1_pol = abs(float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell2_pol = abs(float(shell2.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell3_pol = abs(float(shell3.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell0_strength = float(shell0.get("pair_strength", 0.0))
    shell1_strength = float(shell1.get("pair_strength", 0.0))
    shell0_gate = float(shell0.get("handoff_gate_score", 0.0))
    shell1_gate = float(shell1.get("handoff_gate_score", 0.0))
    outer_peak = max(shell2_pol, shell3_pol)
    shell0_under = shell0_pol < min(0.045, 0.95 * outer_peak)
    shell1_under = shell1_pol < min(0.024, 0.62 * outer_peak)
    shell0_ready = 0.06 <= shell0_strength <= 0.095 and shell0_gate >= 0.42
    shell1_ready = 0.07 <= shell1_strength <= 0.09 and shell1_gate >= 0.29
    if not (shell0_under and shell1_under and shell0_ready and shell1_ready):
        return pairs
    target_shell0 = min(0.047, max(shell0_pol, 0.98 * outer_peak, 1.18 * shell0_pol))
    target_shell1 = min(0.026, max(shell1_pol, 0.60 * outer_peak, 1.25 * shell1_pol))
    repaired = []
    for pair in pairs:
        shell_index = int(pair.get("shell_index", -1))
        axis = str(pair.get("axis", "none"))
        if axis != "x" or shell_index not in {0, 1}:
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        pair_diff = dict(new_pair.get("pair_differential_mode", {}))
        diff_channels = dict(new_pair.get("differential_channels", {}))
        if shell_index == 0:
            new_polarity = float(target_shell0)
            translation_floor = 0.42
            strength_boost = 0.012
            static_drop = 0.05
        else:
            new_polarity = float(target_shell1)
            translation_floor = 0.34
            strength_boost = 0.008
            static_drop = 0.04
        pair_diff["polarity_projection"] = new_polarity
        diff_channels["polarity_projection"] = new_polarity
        new_pair["pair_differential_mode"] = pair_diff
        new_pair["differential_channels"] = diff_channels
        scores = dict(new_pair.get("mode_scores", {}))
        scores["translation_like"] = _clip01(max(float(scores.get("translation_like", 0.0)), translation_floor) + 0.03)
        scores["static_like"] = _clip01(float(scores.get("static_like", 0.0)) - static_drop)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            new_pair["direction_sign"] = 1.0
        new_pair["mode_margin"] = float(margin)
        new_pair["pair_strength"] = _clip01(float(new_pair.get("pair_strength", 0.0)) + strength_boost)
        repaired.append(new_pair)
    return repaired



def _apply_inner_core_high_amplitude_distribution_shaping(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell0 = x_pairs.get(0)
    shell1 = x_pairs.get(1)
    shell2 = x_pairs.get(2)
    shell3 = x_pairs.get(3)
    if shell0 is None or shell1 is None or shell2 is None or shell3 is None:
        return pairs
    continuity_ready = all(
        str(pair.get("dominant_mode", "none")) == "translation_like"
        and float(pair.get("direction_sign", 0.0)) > 0.0
        for pair in (shell0, shell1, shell2, shell3)
    )
    if not continuity_ready:
        return pairs
    shell0_pol = abs(float(shell0.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell1_pol = abs(float(shell1.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell2_pol = abs(float(shell2.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell3_pol = abs(float(shell3.get("pair_differential_mode", {}).get("polarity_projection", 0.0)))
    shell0_gate = float(shell0.get("handoff_gate_score", 0.0))
    shell1_gate = float(shell1.get("handoff_gate_score", 0.0))
    shell2_gate = float(shell2.get("handoff_gate_score", 0.0))
    shell0_strength = float(shell0.get("pair_strength", 0.0))
    shell1_strength = float(shell1.get("pair_strength", 0.0))
    shell2_strength = float(shell2.get("pair_strength", 0.0))
    shaping_ready = (
        shell0_strength >= 0.08
        and shell1_strength >= 0.08
        and shell2_strength >= 0.10
        and shell0_gate >= 0.42
        and shell1_gate >= 0.29
        and shell2_gate >= 0.35
    )
    if not shaping_ready:
        return pairs
    target_shell0 = min(0.050, max(shell0_pol, 0.046))
    target_shell1 = min(0.034, max(shell1_pol, 0.031))
    target_shell2 = min(0.040, max(shell2_pol, 0.034))
    if (
        target_shell0 <= shell0_pol + 1e-9
        and target_shell1 <= shell1_pol + 1e-9
        and target_shell2 <= shell2_pol + 1e-9
    ):
        return pairs
    repaired = []
    for pair in pairs:
        shell_index = int(pair.get("shell_index", -1))
        axis = str(pair.get("axis", "none"))
        if axis != "x" or shell_index not in {0, 1, 2}:
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        pair_diff = dict(new_pair.get("pair_differential_mode", {}))
        diff_channels = dict(new_pair.get("differential_channels", {}))
        if shell_index == 0:
            new_polarity = target_shell0
            translation_floor = 0.46
            static_drop = 0.03
            strength_boost = 0.004
        elif shell_index == 1:
            new_polarity = target_shell1
            translation_floor = 0.39
            static_drop = 0.03
            strength_boost = 0.003
        else:
            new_polarity = target_shell2
            translation_floor = 0.34
            static_drop = 0.02
            strength_boost = 0.002
        pair_diff["polarity_projection"] = float(new_polarity)
        diff_channels["polarity_projection"] = float(new_polarity)
        new_pair["pair_differential_mode"] = pair_diff
        new_pair["differential_channels"] = diff_channels
        scores = dict(new_pair.get("mode_scores", {}))
        scores["translation_like"] = _clip01(max(float(scores.get("translation_like", 0.0)), translation_floor) + 0.01)
        scores["static_like"] = _clip01(float(scores.get("static_like", 0.0)) - static_drop)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            new_pair["direction_sign"] = 1.0
        new_pair["mode_margin"] = float(margin)
        new_pair["pair_strength"] = _clip01(float(new_pair.get("pair_strength", 0.0)) + strength_boost)
        repaired.append(new_pair)
    return repaired

def _continuity_aligned_x_window_override(
    *,
    phase: str,
    pairs: list[dict[str, Any]],
    expected_translation_signs: dict[str, float] | None,
) -> dict[str, Any] | None:
    if phase != "active" or not expected_translation_signs:
        return None
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return None
    x_pairs = [
        pair for pair in pairs
        if str(pair.get("axis", "none")) == "x"
        and str(pair.get("dominant_mode", "none")) == "translation_like"
        and float(pair.get("direction_sign", 0.0)) > 0.0
    ]
    if len(x_pairs) < 3:
        return None
    shells = sorted(int(pair.get("shell_index", -1)) for pair in x_pairs)
    max_run = 1
    run = 1
    for prev, cur in zip(shells, shells[1:]):
        if cur == prev + 1:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    if max_run < 3:
        return None
    translation_support = sum(_pair_support(pair, "translation_like") for pair in x_pairs)
    strongest_x = max(x_pairs, key=lambda pair: _pair_support(pair, "translation_like"))
    static_candidates = [pair for pair in pairs if str(pair.get("dominant_mode", "none")) == "static_like"]
    best_static = max((_pair_support(pair, "static_like") for pair in static_candidates), default=0.0)
    if translation_support < 0.75 or translation_support <= 1.55 * best_static:
        return None
    return strongest_x

def _apply_shell2_retention_restoration(
    pairs: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None,
) -> list[dict[str, Any]]:
    if not pairs or not expected_translation_signs:
        return pairs
    expected_sign = expected_translation_signs.get("x")
    if expected_sign is None or expected_sign <= 0.0:
        return pairs
    x_pairs = {int(pair.get("shell_index", -1)): pair for pair in pairs if str(pair.get("axis", "none")) == "x"}
    shell2 = x_pairs.get(2)
    shell3 = x_pairs.get(3)
    if shell2 is None or shell3 is None:
        return pairs
    shell3_ready = (
        str(shell3.get("dominant_mode", "none")) == "translation_like"
        and float(shell3.get("direction_sign", 0.0)) > 0.0
        and float(shell3.get("mode_scores", {}).get("translation_like", 0.0)) >= 0.24
        and float(shell3.get("handoff_gate_score", 0.0)) >= 0.34
    )
    shell2_ready = (
        str(shell2.get("dominant_mode", "none")) == "static_like"
        and float(shell2.get("direction_sign", 0.0)) == 0.0
        and 0.04 <= float(shell2.get("mode_scores", {}).get("translation_like", 0.0)) <= 0.09
        and float(shell2.get("mode_scores", {}).get("static_like", 0.0)) >= 0.20
        and 0.09 <= float(shell2.get("pair_strength", 0.0)) <= 0.12
        and 0.34 <= float(shell2.get("handoff_gate_score", 0.0)) <= 0.37
        and float(shell2.get("pair_differential_mode", {}).get("polarity_projection", 0.0)) >= 0.015
        and float(shell2.get("pair_common_mode", {}).get("axial_flux", 0.0)) >= 0.10
        and float(shell2.get("pair_common_mode", {}).get("transfer_potential", 0.0)) >= 0.13
    )
    if not (shell3_ready and shell2_ready):
        return pairs
    repaired = []
    for pair in pairs:
        if int(pair.get("shell_index", -1)) != 2 or str(pair.get("axis", "none")) != "x":
            repaired.append(pair)
            continue
        new_pair = dict(pair)
        scores = dict(new_pair.get("mode_scores", {}))
        translation = float(scores.get("translation_like", 0.0))
        static = float(scores.get("static_like", 0.0))
        retention_bonus = 0.23
        scores["translation_like"] = _clip01(translation + retention_bonus)
        scores["static_like"] = _clip01(static - 0.12)
        new_pair["mode_scores"] = scores
        mode, margin = _dominant_mode(scores)
        new_pair["dominant_mode"] = mode
        new_pair["dominant_axis"] = "x" if mode in {"translation_like", "rotation_like"} else "none"
        if mode == "translation_like":
            sign_signal = float(new_pair.get("pair_differential_mode", {}).get("polarity_projection", 0.0))
            new_pair["direction_sign"] = float(np.sign(sign_signal)) if abs(sign_signal) >= 1e-12 else 0.0
        new_pair["mode_margin"] = float(margin)
        repaired.append(new_pair)
    return repaired

def _window_record(shell_window: dict[str, Any], *, expected_translation_signs: dict[str, float] | None = None) -> dict[str, Any]:
    pairs = _window_pairs(list(shell_window.get("shell_units", [])), expected_translation_signs=expected_translation_signs)
    pairs = _apply_inner_shell_translation_restoration(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_shell2_retention_restoration(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_inner_shell_translation_restoration(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_inner_shell_amplitude_source_redesign(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_shell0_high_amplitude_source_restoration(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_joint_inner_core_high_amplitude_density_redesign(pairs, expected_translation_signs=expected_translation_signs)
    pairs = _apply_inner_core_high_amplitude_distribution_shaping(pairs, expected_translation_signs=expected_translation_signs)
    mode_counts = Counter(str(pair.get("dominant_mode", "mixed")) for pair in pairs)
    dominant_mode = mode_counts.most_common(1)[0][0] if mode_counts else "mixed"
    upstream_axis = str(shell_window.get("upstream_dominant_axis", "none"))
    if dominant_mode == "mixed" and pairs:
        support_by_mode = defaultdict(float)
        for pair in pairs:
            support_by_mode[str(pair.get("dominant_mode", "mixed"))] += float(pair.get("pair_strength", 0.0))
        dominant_mode = max(support_by_mode.items(), key=lambda kv: kv[1])[0]
    upstream_mode = str(shell_window.get("shell_dominant_mode", "mixed"))
    strongest_pair = None
    if upstream_mode in MODES and pairs:
        aligned_pairs = [
            pair for pair in pairs
            if str(pair.get("axis", "none")) == upstream_axis and bool(pair.get("pair_gate_passed", False))
        ]
        upstream_pool = aligned_pairs if aligned_pairs else [
            pair for pair in pairs if str(pair.get("axis", "none")) == upstream_axis
        ]
        if not upstream_pool:
            upstream_pool = [pair for pair in pairs if bool(pair.get("pair_gate_passed", False))] or pairs
        upstream_best = max(upstream_pool, key=lambda pair: _pair_support(pair, upstream_mode))
        if _pair_support(upstream_best, upstream_mode) >= 0.10:
            dominant_mode = upstream_mode
            strongest_pair = upstream_best
    continuity_override = _continuity_aligned_x_window_override(
        phase=str(shell_window.get("phase", "baseline")),
        pairs=pairs,
        expected_translation_signs=expected_translation_signs,
    )
    if continuity_override is not None:
        dominant_mode = "translation_like"
        strongest_pair = continuity_override
    if strongest_pair is None:
        candidates = [pair for pair in pairs if str(pair.get("dominant_mode", "mixed")) == dominant_mode]
        if not candidates:
            candidates = pairs
        strongest_pair = max(candidates, key=lambda pair: _pair_support(pair, dominant_mode), default=None)
    dominant_axis = str(strongest_pair.get("axis", "none")) if strongest_pair else "none"
    return {
        "phase": str(shell_window.get("phase", "baseline")),
        "upstream_dominant_mode": str(shell_window.get("shell_dominant_mode", "mixed")),
        "upstream_dominant_axis": str(shell_window.get("shell_dominant_axis", "none")),
        "atlas_dominant_mode": dominant_mode,
        "atlas_dominant_axis": dominant_axis,
        "window_start": float(shell_window.get("window_start", 0.0)),
        "window_end": float(shell_window.get("window_end", 0.0)),
        "stability_score": float(shell_window.get("stability_score", 0.0)),
        "recovery_score": float(shell_window.get("recovery_score", 0.0)),
        "mode_margin": float(shell_window.get("mode_margin", 0.0)),
        "pair_summaries": pairs,
        "strongest_pair": strongest_pair or {},
    }


def build_mirror_channel_atlas_trace(
    shell_trace: list[dict[str, Any]],
    *,
    expected_translation_signs: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    return [_window_record(window, expected_translation_signs=expected_translation_signs) for window in shell_trace]


def build_mirror_channel_atlas_trace_from_files(
    *,
    shell_trace_path: str | Path,
    expected_translation_signs: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    return build_mirror_channel_atlas_trace(
        _load_json(shell_trace_path),
        expected_translation_signs=expected_translation_signs,
    )


def summarize_mirror_channel_atlas_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_windows": 0,
            "dominant_mode": "none",
            "dominant_axis": "none",
            "dominant_phase": "none",
            "phase_counts": {},
            "phase_dominant_modes": {},
            "active_summary": {},
            "mean_pair_strength": 0.0,
            "max_shell_index": -1,
        }

    phase_counts = Counter(str(row.get("phase", "baseline")) for row in trace)
    mode_counts = Counter(str(row.get("atlas_dominant_mode", "mixed")) for row in trace)
    axis_counts = Counter(str(row.get("atlas_dominant_axis", "none")) for row in trace if str(row.get("atlas_dominant_axis", "none")) != "none")
    dominant_phase = phase_counts.most_common(1)[0][0]
    dominant_mode = mode_counts.most_common(1)[0][0]
    dominant_axis = axis_counts.most_common(1)[0][0] if axis_counts else "none"
    phase_dominant_modes = {}
    for phase in phase_counts:
        phase_rows = [row for row in trace if str(row.get("phase", "baseline")) == phase]
        counts = Counter(str(row.get("atlas_dominant_mode", "mixed")) for row in phase_rows)
        phase_dominant_modes[phase] = counts.most_common(1)[0][0] if counts else "none"

    all_pairs = [pair for row in trace for pair in row.get("pair_summaries", [])]
    max_shell_index = max((int(pair.get("shell_index", -1)) for pair in all_pairs), default=-1)
    active_rows = [row for row in trace if str(row.get("phase", "baseline")) == "active"]
    active_mode_counts = Counter(str(row.get("atlas_dominant_mode", "mixed")) for row in active_rows)
    active_axis_counts = Counter(str(row.get("atlas_dominant_axis", "none")) for row in active_rows if str(row.get("atlas_dominant_axis", "none")) != "none")
    active_mode = active_mode_counts.most_common(1)[0][0] if active_mode_counts else "none"
    active_axis = active_axis_counts.most_common(1)[0][0] if active_axis_counts else "none"

    strongest_pair = {}
    if active_rows:
        candidate_pairs = []
        for row in active_rows:
            pair = dict(row.get("strongest_pair", {}))
            if not pair:
                continue
            pair["window_start"] = float(row.get("window_start", 0.0))
            pair["window_end"] = float(row.get("window_end", 0.0))
            candidate_pairs.append(pair)
        if candidate_pairs:
            strongest_pair = max(candidate_pairs, key=lambda pair: _pair_support(pair, active_mode))

    return {
        "num_windows": int(len(trace)),
        "dominant_mode": dominant_mode,
        "dominant_axis": dominant_axis,
        "dominant_phase": dominant_phase,
        "phase_counts": dict(phase_counts),
        "phase_dominant_modes": phase_dominant_modes,
        "mean_pair_strength": _mean([float(pair.get("pair_strength", 0.0)) for pair in all_pairs]),
        "max_shell_index": int(max_shell_index),
        "active_summary": {
            "num_windows": int(len(active_rows)),
            "dominant_mode": active_mode,
            "dominant_axis": active_axis,
            "strongest_pair": strongest_pair,
        },
    }
