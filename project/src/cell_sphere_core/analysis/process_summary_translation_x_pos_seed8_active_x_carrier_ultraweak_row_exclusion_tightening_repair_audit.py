from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _summary_row(summary_analysis: dict[str, Any], case_name: str) -> dict[str, Any]:
    case = dict(summary_analysis["cases"][case_name])
    active_signature = dict(case.get("active_signature", {}))
    strongest_pair = dict(active_signature.get("strongest_pair", {}))
    return {
        "active_dominant_mode": str(case.get("active_dominant_mode", "none")),
        "active_dominant_axis": str(case.get("active_dominant_axis", "none")),
        "active_mean_polarity_projection": float(active_signature.get("mean_polarity_projection", 0.0)),
        "active_raw_mean_polarity_projection": float(active_signature.get("raw_mean_polarity_projection", 0.0)),
        "active_support_weighted_mean_polarity_projection": float(active_signature.get("support_weighted_mean_polarity_projection", 0.0)),
        "active_carrier_mean_polarity_projection": float(active_signature.get("carrier_mean_polarity_projection", 0.0)),
        "active_margin_weighted_carrier_polarity_projection": float(active_signature.get("margin_weighted_carrier_polarity_projection", 0.0)),
        "active_carrier_floor_mean_polarity_projection": float(active_signature.get("carrier_floor_mean_polarity_projection", 0.0)),
        "active_carrier_floor_weighted_polarity_projection": float(active_signature.get("carrier_floor_weighted_polarity_projection", 0.0)),
        "translation_carrier_pair_count": int(active_signature.get("translation_carrier_pair_count", 0)),
        "carrier_floor_pair_count": int(active_signature.get("carrier_floor_pair_count", 0)),
        "active_direction_sign": float(active_signature.get("direction_sign", 0.0)),
        "strongest_pair_mode": str(strongest_pair.get("dominant_mode", "none")),
        "strongest_pair_axis": str(strongest_pair.get("axis", "none")),
    }


def build_translation_x_pos_seed8_active_x_carrier_ultraweak_row_exclusion_tightening_repair_audit(
    *,
    previous_round_audit_path: str | Path,
    repeatability_audit_path: str | Path,
    seed7_summary_analysis_path: str | Path,
    seed8_summary_analysis_path: str | Path,
) -> dict[str, Any]:
    previous_round = _load_json(previous_round_audit_path)
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary_analysis = _load_json(seed7_summary_analysis_path)
    seed8_summary_analysis = _load_json(seed8_summary_analysis_path)

    seed7 = {
        "translation_x_pos": _summary_row(seed7_summary_analysis, "translation_x_pos"),
        "translation_x_neg": _summary_row(seed7_summary_analysis, "translation_x_neg"),
    }
    seed8 = {
        "translation_x_pos": _summary_row(seed8_summary_analysis, "translation_x_pos"),
        "translation_x_neg": _summary_row(seed8_summary_analysis, "translation_x_neg"),
        "rotation_z_pos": _summary_row(seed8_summary_analysis, "rotation_z_pos"),
    }

    txp7 = seed7["translation_x_pos"]
    txn7 = seed7["translation_x_neg"]
    txp8 = seed8["translation_x_pos"]
    txn8 = seed8["translation_x_neg"]
    rzp8 = seed8["rotation_z_pos"]
    previous_gap = float(previous_round.get("seed8_translation_x_pos_gap_to_seed7", 0.0))
    current_gap = float(txp7["active_mean_polarity_projection"] - txp8["active_mean_polarity_projection"])

    evidence = {
        "seed8_translation_x_pos_gap_reduced_vs_round44": current_gap < previous_gap,
        "seed8_translation_x_pos_active_amplitude_improved_vs_round44": txp8["active_mean_polarity_projection"] > float(previous_round.get("seed8", {}).get("translation_x_pos", {}).get("active_mean_polarity_projection", 0.0)),
        "seed8_translation_x_pos_active_mode_axis_preserved": txp8["active_dominant_mode"] == "translation_like" and txp8["active_dominant_axis"] == "x",
        "seed8_translation_x_neg_active_mode_axis_preserved": txn8["active_dominant_mode"] == "translation_like" and txn8["active_dominant_axis"] == "x",
        "seed8_translation_x_pos_sign_preserved": txp8["active_mean_polarity_projection"] > 0.0,
        "seed8_translation_x_neg_sign_preserved": txn8["active_mean_polarity_projection"] < 0.0,
        "seed8_translation_x_pos_strongest_pair_preserved": txp8["strongest_pair_mode"] == "translation_like" and txp8["strongest_pair_axis"] == "x",
        "seed8_translation_x_neg_strongest_pair_preserved": txn8["strongest_pair_mode"] == "translation_like" and txn8["strongest_pair_axis"] == "x",
        "seed8_rotation_z_pos_guardrail_preserved": rzp8["active_dominant_mode"] == "rotation_like" and rzp8["active_dominant_axis"] == "z",
        "seed7_translation_x_pos_reference_preserved": txp7["active_mean_polarity_projection"] > 0.10,
        "seed7_translation_x_neg_reference_preserved": txn7["active_mean_polarity_projection"] < -0.10,
        "seed8_translation_x_pos_weighted_floor_exceeds_current_mean": abs(txp8["active_carrier_floor_weighted_polarity_projection"]) >= abs(txp8["active_mean_polarity_projection"]),
        "seed8_translation_x_pos_carrier_floor_pair_count_narrow": 2 <= txp8["carrier_floor_pair_count"] < txp8["translation_carrier_pair_count"],
        "seed8_translation_x_pos_raw_to_weighted_dilution_still_large": abs(txp8["active_raw_mean_polarity_projection"]) < 0.55 * max(abs(txp8["active_carrier_floor_weighted_polarity_projection"]), 1e-12),
    }
    contracts_passed = all(evidence.values())
    residual_issue = "seed8_translation_x_pos_gap_to_seed7_still_material" if current_gap > 0.12 else "none"

    return {
        "suite": "translation_x_pos_seed8_active_x_carrier_ultraweak_row_exclusion_tightening_repair_audit_r1",
        "contracts": {"passed": contracts_passed},
        "repeatability_failures": repeatability.get("contracts", {}).get("failures", []),
        "previous_round_seed8_translation_x_pos_gap_to_seed7": previous_gap,
        "seed8_translation_x_pos_gap_to_seed7": current_gap,
        "seed7": seed7,
        "seed8": seed8,
        "evidence": evidence,
        "inferred_outcome": "translation_x_pos_seed8_active_x_carrier_ultraweak_row_exclusion_tightening_repair_success" if contracts_passed else "undetermined",
        "residual_issue": residual_issue,
        "interpretation": {
            "primary_effect": "raise the repaired seed8 translation_x_pos mean slightly further by tightening ultraweak active x-row exclusion only when strongest-pair translation mode is already restored, the carrier-floor weighted signal still has the same sign, and the raw mean remains clearly diluted below that floor-cleared carrier signal",
            "guardrail": "preserve x-axis identity, polarity sign, strongest-pair translation mode, and the rotation_z_pos active z guardrail",
            "next_branch": "optional only if future rounds still need more seed8 x_pos lift after tightening ultraweak-row exclusion without broadening beyond active x-family summary corrections",
        },
    }
