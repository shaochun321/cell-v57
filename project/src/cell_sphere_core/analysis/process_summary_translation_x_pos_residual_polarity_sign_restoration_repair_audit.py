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
        "active_direction_sign": float(active_signature.get("direction_sign", 0.0)),
        "strongest_pair_mode": str(strongest_pair.get("dominant_mode", "none")),
        "strongest_pair_axis": str(strongest_pair.get("axis", "none")),
        "strongest_pair_polarity_projection": float(strongest_pair.get("differential_channels", {}).get("polarity_projection", 0.0)),
    }


def build_translation_x_pos_residual_polarity_sign_restoration_repair_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_summary_analysis_path: str | Path,
    seed8_summary_analysis_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary_analysis = _load_json(seed7_summary_analysis_path)
    seed8_summary_analysis = _load_json(seed8_summary_analysis_path)

    seed7 = {
        "translation_x_pos": _summary_row(seed7_summary_analysis, "translation_x_pos"),
        "translation_x_neg": _summary_row(seed7_summary_analysis, "translation_x_neg"),
        "rotation_z_pos": _summary_row(seed7_summary_analysis, "rotation_z_pos"),
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

    evidence = {
        "seed7_translation_x_pos_positive_sign_preserved": txp7["active_mean_polarity_projection"] > 0.0,
        "seed7_translation_x_neg_negative_sign_preserved": txn7["active_mean_polarity_projection"] < 0.0,
        "seed8_translation_x_pos_positive_sign_restored": txp8["active_mean_polarity_projection"] > 0.0,
        "seed8_translation_x_neg_negative_sign_restored": txn8["active_mean_polarity_projection"] < 0.0,
        "seed8_translation_family_sign_flip_restored": txp8["active_mean_polarity_projection"] * txn8["active_mean_polarity_projection"] < 0.0,
        "seed8_translation_x_pos_active_mode_axis_preserved": txp8["active_dominant_mode"] == "translation_like" and txp8["active_dominant_axis"] == "x",
        "seed8_translation_x_neg_active_mode_axis_preserved": txn8["active_dominant_mode"] == "translation_like" and txn8["active_dominant_axis"] == "x",
        "seed8_rotation_z_pos_guardrail_preserved": rzp8["active_dominant_mode"] == "rotation_like" and rzp8["active_dominant_axis"] == "z",
        "seed8_translation_x_pos_strongest_pair_still_static_like": txp8["strongest_pair_mode"] == "static_like",
        "seed8_translation_x_neg_strongest_pair_still_static_like": txn8["strongest_pair_mode"] == "static_like",
    }

    contracts_passed = all(
        evidence[key]
        for key in (
            "seed7_translation_x_pos_positive_sign_preserved",
            "seed7_translation_x_neg_negative_sign_preserved",
            "seed8_translation_x_pos_positive_sign_restored",
            "seed8_translation_x_neg_negative_sign_restored",
            "seed8_translation_family_sign_flip_restored",
            "seed8_translation_x_pos_active_mode_axis_preserved",
            "seed8_translation_x_neg_active_mode_axis_preserved",
            "seed8_rotation_z_pos_guardrail_preserved",
        )
    )

    residual = "translation_x_family_strongest_pair_mode_not_yet_restored" if (
        evidence["seed8_translation_x_pos_strongest_pair_still_static_like"]
        or evidence["seed8_translation_x_neg_strongest_pair_still_static_like"]
    ) else "none"

    return {
        "suite": "translation_x_pos_residual_polarity_sign_restoration_repair_audit_r1",
        "contracts": {"passed": contracts_passed},
        "repeatability_failures": repeatability.get("contracts", {}).get("failures", []),
        "seed7": seed7,
        "seed8": seed8,
        "evidence": evidence,
        "inferred_outcome": "translation_x_family_residual_polarity_sign_restoration_repair_success" if contracts_passed else "undetermined",
        "residual_issue": residual,
        "interpretation": {
            "primary_effect": "restore translation x-family polarity sign without losing recovered active x axis",
            "guardrail": "preserve rotation_z_pos active z classification",
            "next_branch": "restore strongest-pair translation mode under the already restored sign and axis",
        },
    }
