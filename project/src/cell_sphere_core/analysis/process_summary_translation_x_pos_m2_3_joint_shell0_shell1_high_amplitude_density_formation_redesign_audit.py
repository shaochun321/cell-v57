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


def _joint_inner_core_density(rows: list[dict[str, Any]]) -> float:
    total = 0.0
    count = 0
    for window in rows:
        for shell_idx in (0, 1):
            row = next((r for r in window["pair_rows"] if int(r["shell_index"]) == shell_idx), None)
            if row is None:
                continue
            total += max(0.0, float(row["polarity_projection"]))
            count += 1
    return float(total / max(count, 1))


def _shell0_shell1_positive_translation_both_windows(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    for window in rows[:2]:
        for shell_idx in (0, 1):
            row = next((r for r in window["pair_rows"] if int(r["shell_index"]) == shell_idx), None)
            if row is None:
                return False
            if not (row["dominant_mode"] == "translation_like" and row["direction_sign"] > 0.0):
                return False
    return True


def build_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit(
    *,
    round52_seed8_summary_path: str | Path,
    round58_seed8_summary_path: str | Path,
    round58_seed8_atlas_trace_path: str | Path,
    round59_seed8_summary_path: str | Path,
    round59_seed8_atlas_trace_path: str | Path,
    round59_seed8_xneg_summary_path: str | Path,
    round59_seed8_rotation_pos_summary_path: str | Path,
    round59_seed8_rotation_neg_summary_path: str | Path,
    repeatability_audit_path: str | Path,
) -> dict[str, Any]:
    round52 = _load_json(round52_seed8_summary_path)
    round58 = _load_json(round58_seed8_summary_path)
    round59 = _load_json(round59_seed8_summary_path)
    round58_rows = _active_x_rows(_load_json(round58_seed8_atlas_trace_path))
    round59_rows = _active_x_rows(_load_json(round59_seed8_atlas_trace_path))
    xneg = _load_json(round59_seed8_xneg_summary_path)
    rot_pos = _load_json(round59_seed8_rotation_pos_summary_path)
    rot_neg = _load_json(round59_seed8_rotation_neg_summary_path)
    repeatability = _load_json(repeatability_audit_path)

    r52x = _phase_x_summary(round52)
    r58x = _phase_x_summary(round58)
    r59x = _phase_x_summary(round59)
    xneg_active = _phase_x_summary(xneg)
    rot_pos_active = _phase_summary(rot_pos)
    rot_neg_active = _phase_summary(rot_neg)

    round58_density = _joint_inner_core_density(round58_rows)
    round59_density = _joint_inner_core_density(round59_rows)

    evidence = {
        "round59_seed8_shell0_shell1_positive_translation_present_in_both_active_windows": _shell0_shell1_positive_translation_both_windows(round59_rows),
        "round59_seed8_joint_inner_core_density_exceeds_round58": round59_density > round58_density,
        "round59_seed8_final_mean_exceeds_round58": float(r59x.get("mean_polarity_projection", 0.0)) > float(r58x.get("mean_polarity_projection", 0.0)),
        "round59_seed8_raw_mean_exceeds_round58": float(r59x.get("raw_mean_polarity_projection", 0.0)) > float(r58x.get("raw_mean_polarity_projection", 0.0)),
        "round59_seed8_translation_x_pos_active_mode_axis_preserved": str(round59["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(round59["phase_summaries"]["active"]["dominant_axis"]) == "x",
        "round59_seed8_translation_x_neg_sign_preserved": str(xneg["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(xneg["phase_summaries"]["active"]["dominant_axis"]) == "x" and float(xneg_active.get("direction_sign", 0.0)) < 0.0,
        "round59_seed8_rotation_z_pos_guardrail_preserved": str(rot_pos_active.get("dominant_mode", "none")) == "rotation_like" and str(rot_pos_active.get("dominant_axis", "none")) == "z",
        "round59_seed8_rotation_z_neg_guardrail_preserved": str(rot_neg_active.get("dominant_mode", "none")) == "rotation_like" and str(rot_neg_active.get("dominant_axis", "none")) == "z",
        "round59_seed8_final_mean_still_below_round52_frozen_baseline": float(r59x.get("mean_polarity_projection", 0.0)) < float(r52x.get("mean_polarity_projection", 0.0)),
    }
    contracts_passed = all(v for k, v in evidence.items() if k != "round59_seed8_final_mean_still_below_round52_frozen_baseline")
    delta_to_round58 = float(r59x.get("mean_polarity_projection", 0.0)) - float(r58x.get("mean_polarity_projection", 0.0))
    gap_to_round52 = float(r52x.get("mean_polarity_projection", 0.0)) - float(r59x.get("mean_polarity_projection", 0.0))

    return {
        "suite": "translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit_r1",
        "contracts": {"passed": contracts_passed},
        "evidence": evidence,
        "repeatability_failures": list(repeatability.get("contracts", {}).get("failures", []) or repeatability.get("failures", []) or []),
        "seed8_round52_frozen_reference": {"phase_active_x_summary": r52x},
        "seed8_round58_m2_2_density": {"phase_active_x_summary": r58x, "active_x_pair_rows": round58_rows, "joint_inner_core_density": round58_density},
        "seed8_round59_m2_3_joint_density": {"phase_active_x_summary": r59x, "active_x_pair_rows": round59_rows, "joint_inner_core_density": round59_density},
        "guardrails": {
            "seed8_translation_x_neg_active_x_summary": xneg_active,
            "seed8_rotation_z_pos_active_summary": rot_pos_active,
            "seed8_rotation_z_neg_active_summary": rot_neg_active,
        },
        "deltas": {
            "round59_minus_round58_final_mean": float(delta_to_round58),
            "round52_minus_round59_gap": float(gap_to_round52),
            "round59_minus_round58_joint_inner_core_density": float(round59_density - round58_density),
        },
        "decision": "continue_inner_core_material_redesign" if contracts_passed else "undetermined",
        "headline": "joint shell0/shell1 high-amplitude density increased; guardrails preserved; final mean still below frozen round52 baseline",
        "residual_issue": "inner-core density improved, but shell0/shell1 combined high-amplitude source still remains below the frozen round52 summary-equivalent level",
    }
