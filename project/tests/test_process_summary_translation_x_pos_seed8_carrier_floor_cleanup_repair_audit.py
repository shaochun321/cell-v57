from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_carrier_floor_cleanup_repair_audit import (
    build_translation_x_pos_seed8_carrier_floor_cleanup_repair_audit,
)


def test_translation_x_pos_seed8_carrier_floor_cleanup_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_seed8_carrier_floor_cleanup_repair_audit(
        previous_round_audit_path="outputs/round39_xpos_x_family_carrier_margin_strengthening_repair_audit/process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit.json",
        repeatability_audit_path="outputs/round40_repair/process_summary_repeatability_audit.json",
        seed7_summary_analysis_path="outputs/round40_repair/seed_7/analysis/process_summary_atlas_analysis.json",
        seed8_summary_analysis_path="outputs/round40_repair/seed_8/analysis/process_summary_atlas_analysis.json",
    )

    assert audit["contracts"]["passed"] is True
    assert audit["evidence"]["seed8_translation_x_pos_gap_reduced_vs_round39"] is True
    assert audit["evidence"]["seed8_translation_x_pos_active_amplitude_improved_vs_round39"] is True
    assert audit["evidence"]["seed8_translation_x_pos_strongest_pair_preserved"] is True
    assert audit["evidence"]["seed8_rotation_z_pos_guardrail_preserved"] is True
    assert audit["inferred_outcome"] == "translation_x_pos_seed8_carrier_floor_cleanup_repair_success"
