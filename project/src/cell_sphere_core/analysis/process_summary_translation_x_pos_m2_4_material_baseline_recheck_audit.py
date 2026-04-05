
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def build_m2_4_material_baseline_recheck(base_dir: str | Path) -> dict[str, Any]:
    base = Path(base_dir)

    round52 = _load_json(base / "outputs/round52_repair/seed_8/translation_x_pos/process_summary_atlas.json")
    round59 = _load_json(base / "outputs/round59_repair/seed_8/translation_x_pos/process_summary_atlas.json")
    round60 = _load_json(base / "outputs/round60_repair/seed_8/translation_x_pos/process_summary_atlas.json")
    xneg60 = _load_json(base / "outputs/round60_repair/seed_8/translation_x_neg/process_summary_atlas.json")
    rzpos60 = _load_json(base / "outputs/round60_repair/seed_8/rotation_z_pos/process_summary_atlas.json")
    rzneg60 = _load_json(base / "outputs/round60_repair/seed_8/rotation_z_neg/process_summary_atlas.json")

    sig52 = round52["active_signature"]
    sig59 = round59["active_signature"]
    sig60 = round60["active_signature"]
    xneg60_sig = xneg60["active_signature"]
    rzpos60_sig = rzpos60["active_signature"]
    rzneg60_sig = rzneg60["active_signature"]

    gap_to_round52 = sig52["mean_polarity_projection"] - sig60["mean_polarity_projection"]
    final_gain_vs_round59 = sig60["mean_polarity_projection"] - sig59["mean_polarity_projection"]
    raw_gain_vs_round52 = sig60["raw_mean_polarity_projection"] - sig52["raw_mean_polarity_projection"]

    guardrails = {
        "translation_x_pos_mode_axis_preserved": (
            round60["active_dominant_mode"] == "translation_like" and round60["active_dominant_axis"] == "x"
        ),
        "translation_x_neg_negative_sign_preserved": xneg60_sig["direction_sign"] < 0.0,
        "rotation_z_pos_guardrail_preserved": (
            rzpos60["active_dominant_mode"] == "rotation_like" and rzpos60["active_dominant_axis"] == "z"
        ),
        "rotation_z_neg_guardrail_preserved": (
            rzneg60["active_dominant_mode"] == "rotation_like" and rzneg60["active_dominant_axis"] == "z"
        ),
    }

    decision = "freeze_m2_4_as_project_baseline"
    if not all(guardrails.values()) or gap_to_round52 > 1e-3:
        decision = "do_not_freeze_m2_4"

    return {
        "suite": "m2_4_material_baseline_recheck",
        "decision": decision,
        "headline": (
            "m2.4 reaches the frozen round52 x_pos baseline within tolerance while preserving source-first continuity and guardrails"
            if decision == "freeze_m2_4_as_project_baseline"
            else "m2.4 baseline recheck failed; do not freeze as project baseline"
        ),
        "recommended_next_step": (
            "freeze M2.4 as the new project baseline and only open M2.5 if it can outperform this baseline without reopening summary/gate patches"
            if decision == "freeze_m2_4_as_project_baseline"
            else "hold redesign branch and re-audit source continuity before any further work"
        ),
        "thresholds": {
            "max_gap_to_frozen_round52": 1e-3,
            "all_guardrails_required": True,
        },
        "round52_frozen_reference": {
            "final_active_mean": sig52["mean_polarity_projection"],
            "raw_active_mean": sig52["raw_mean_polarity_projection"],
            "translation_support": sig52["support_scores"]["translation_like"],
            "carrier_floor_pair_count": sig52["carrier_floor_pair_count"],
            "translation_carrier_pair_count": sig52["translation_carrier_pair_count"],
            "strongest_shell": sig52["strongest_shell"],
        },
        "round59_m2_3_reference": {
            "final_active_mean": sig59["mean_polarity_projection"],
            "raw_active_mean": sig59["raw_mean_polarity_projection"],
            "translation_support": sig59["support_scores"]["translation_like"],
            "carrier_floor_pair_count": sig59["carrier_floor_pair_count"],
            "translation_carrier_pair_count": sig59["translation_carrier_pair_count"],
            "strongest_shell": sig59["strongest_shell"],
        },
        "round60_m2_4_candidate": {
            "final_active_mean": sig60["mean_polarity_projection"],
            "raw_active_mean": sig60["raw_mean_polarity_projection"],
            "translation_support": sig60["support_scores"]["translation_like"],
            "carrier_floor_pair_count": sig60["carrier_floor_pair_count"],
            "translation_carrier_pair_count": sig60["translation_carrier_pair_count"],
            "strongest_shell": sig60["strongest_shell"],
        },
        "guardrails": guardrails,
        "evidence": {
            "gap_to_frozen_round52": gap_to_round52,
            "final_gain_vs_round59": final_gain_vs_round59,
            "raw_gain_vs_round52": raw_gain_vs_round52,
            "translation_support_gain_vs_round52": sig60["support_scores"]["translation_like"] - sig52["support_scores"]["translation_like"],
            "carrier_floor_gain_vs_round52": sig60["carrier_floor_pair_count"] - sig52["carrier_floor_pair_count"],
            "translation_carrier_gain_vs_round52": sig60["translation_carrier_pair_count"] - sig52["translation_carrier_pair_count"],
        },
        "residual_issue": (
            "m2.4 essentially closes the frozen round52 gap, but seed7-level superiority is still not reclaimed; future work must beat this baseline from the source side rather than re-opening summary patches"
        ),
    }
