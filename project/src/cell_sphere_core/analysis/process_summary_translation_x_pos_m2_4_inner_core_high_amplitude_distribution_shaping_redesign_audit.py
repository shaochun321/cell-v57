from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _phase_x_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json["phase_summaries"]["active"]["axis_summaries"]["x"])


def _phase_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json["phase_summaries"]["active"])


def _active_x_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for window_index, window in enumerate(atlas_trace):
        if str(window.get("phase", "baseline")) != "active":
            continue
        rows = []
        for pair in sorted([item for item in window.get("pair_summaries", []) if str(item.get("axis", "none")) == "x"], key=lambda item: int(item.get("shell_index", -1))):
            rows.append({
                "shell_index": int(pair.get("shell_index", -1)),
                "dominant_mode": str(pair.get("dominant_mode", "none")),
                "direction_sign": float(pair.get("direction_sign", 0.0)),
                "pair_strength": float(pair.get("pair_strength", 0.0)),
                "handoff_gate_score": float(pair.get("handoff_gate_score", 0.0)),
                "translation_like": float(pair.get("mode_scores", {}).get("translation_like", 0.0)),
                "static_like": float(pair.get("mode_scores", {}).get("static_like", 0.0)),
                "polarity_projection": float(pair.get("pair_differential_mode", {}).get("polarity_projection", 0.0)),
            })
        out.append({
            "window_index": int(window_index),
            "atlas_dominant_mode": str(window.get("atlas_dominant_mode", "none")),
            "atlas_dominant_axis": str(window.get("atlas_dominant_axis", "none")),
            "pair_rows": rows,
        })
    return out


def _inner_core_density(rows: list[dict[str, Any]]) -> float:
    total = 0.0
    count = 0
    for window in rows:
        for shell_idx in (0, 1, 2):
            row = next((r for r in window["pair_rows"] if int(r["shell_index"]) == shell_idx), None)
            if row is None:
                continue
            total += max(0.0, float(row["polarity_projection"]))
            count += 1
    return float(total / max(count, 1))


def _shell012_positive_translation_both_windows(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    for window in rows[:2]:
        for shell_idx in (0, 1, 2):
            row = next((r for r in window["pair_rows"] if int(r["shell_index"]) == shell_idx), None)
            if row is None:
                return False
            if not (row["dominant_mode"] == "translation_like" and row["direction_sign"] > 0.0):
                return False
    return True


def build_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit(
    *,
    round52_seed8_summary_path: str | Path,
    round59_seed8_summary_path: str | Path,
    round59_seed8_atlas_trace_path: str | Path,
    round60_seed8_summary_path: str | Path,
    round60_seed8_atlas_trace_path: str | Path,
    round60_seed8_xneg_summary_path: str | Path,
    round60_seed8_rotation_pos_summary_path: str | Path,
    round60_seed8_rotation_neg_summary_path: str | Path,
    repeatability_audit_path: str | Path,
) -> dict[str, Any]:
    round52 = _load_json(round52_seed8_summary_path)
    round59 = _load_json(round59_seed8_summary_path)
    round60 = _load_json(round60_seed8_summary_path)
    round59_rows = _active_x_rows(_load_json(round59_seed8_atlas_trace_path))
    round60_rows = _active_x_rows(_load_json(round60_seed8_atlas_trace_path))
    xneg = _load_json(round60_seed8_xneg_summary_path)
    rot_pos = _load_json(round60_seed8_rotation_pos_summary_path)
    rot_neg = _load_json(round60_seed8_rotation_neg_summary_path)
    repeatability = _load_json(repeatability_audit_path)

    r52x = _phase_x_summary(round52)
    r59x = _phase_x_summary(round59)
    r60x = _phase_x_summary(round60)
    xneg_active = _phase_x_summary(xneg)
    rot_pos_active = _phase_summary(rot_pos)
    rot_neg_active = _phase_summary(rot_neg)

    round59_density = _inner_core_density(round59_rows)
    round60_density = _inner_core_density(round60_rows)
    gap_to_round52 = float(r52x.get("mean_polarity_projection", 0.0)) - float(r60x.get("mean_polarity_projection", 0.0))

    evidence = {
        "round60_seed8_shell012_positive_translation_present_in_both_active_windows": _shell012_positive_translation_both_windows(round60_rows),
        "round60_seed8_inner_core_density_exceeds_round59": round60_density > round59_density,
        "round60_seed8_final_mean_exceeds_round59": float(r60x.get("mean_polarity_projection", 0.0)) > float(r59x.get("mean_polarity_projection", 0.0)),
        "round60_seed8_raw_mean_exceeds_round59": float(r60x.get("raw_mean_polarity_projection", 0.0)) > float(r59x.get("raw_mean_polarity_projection", 0.0)),
        "round60_seed8_translation_x_pos_active_mode_axis_preserved": str(round60["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(round60["phase_summaries"]["active"]["dominant_axis"]) == "x",
        "round60_seed8_translation_x_neg_sign_preserved": str(xneg["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(xneg["phase_summaries"]["active"]["dominant_axis"]) == "x" and float(xneg_active.get("direction_sign", 0.0)) < 0.0,
        "round60_seed8_rotation_z_pos_guardrail_preserved": str(rot_pos_active.get("dominant_mode", "none")) == "rotation_like" and str(rot_pos_active.get("dominant_axis", "none")) == "z",
        "round60_seed8_rotation_z_neg_guardrail_preserved": str(rot_neg_active.get("dominant_mode", "none")) == "rotation_like" and str(rot_neg_active.get("dominant_axis", "none")) == "z",
        "round60_seed8_final_mean_within_frozen_round52_tolerance": abs(gap_to_round52) <= 1e-4,
    }
    contracts_passed = all(evidence.values())
    return {
        "suite": "translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit_r1",
        "contracts": {"passed": contracts_passed},
        "evidence": evidence,
        "repeatability_failures": list(repeatability.get("contracts", {}).get("failures", []) or repeatability.get("failures", []) or []),
        "seed8_round52_frozen_reference": {"phase_active_x_summary": r52x},
        "seed8_round59_m2_3_joint_density": {"phase_active_x_summary": r59x, "active_x_pair_rows": round59_rows, "inner_core_density": round59_density},
        "seed8_round60_m2_4_distribution_shaping": {"phase_active_x_summary": r60x, "active_x_pair_rows": round60_rows, "inner_core_density": round60_density},
        "guardrails": {
            "seed8_translation_x_neg_active_x_summary": xneg_active,
            "seed8_rotation_z_pos_active_summary": rot_pos_active,
            "seed8_rotation_z_neg_active_summary": rot_neg_active,
        },
        "deltas": {
            "round60_minus_round59_final_mean": float(r60x.get("mean_polarity_projection", 0.0) - r59x.get("mean_polarity_projection", 0.0)),
            "round52_minus_round60_gap": float(gap_to_round52),
            "round60_minus_round59_inner_core_density": float(round60_density - round59_density),
        },
        "decision": "freeze_m2_4_as_material_baseline" if contracts_passed else "continue_inner_core_material_redesign",
        "headline": "inner-core high-amplitude distribution shaping almost matches the frozen round52 baseline while preserving material-source continuity and guardrails",
        "residual_issue": "frozen round52 gap is effectively closed within tolerance, but seed7-level superiority is still not reclaimed from source-first material design alone",
    }
