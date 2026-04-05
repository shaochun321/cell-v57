from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit import (
    build_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit,
)


def test_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit(
        previous_round_audit_path='outputs/round38_xpos_active_amplitude_gap_reduction_repair_audit/process_summary_translation_x_pos_active_amplitude_gap_reduction_repair_audit.json',
        repeatability_audit_path='outputs/round39_repair/process_summary_repeatability_audit.json',
        seed7_summary_analysis_path='outputs/round39_repair/seed_7/analysis/process_summary_atlas_analysis.json',
        seed8_summary_analysis_path='outputs/round39_repair/seed_8/analysis/process_summary_atlas_analysis.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['evidence']['seed8_translation_x_pos_gap_reduced_vs_round38'] is True
    assert audit['evidence']['seed8_translation_x_pos_active_amplitude_improved_vs_round38'] is True
    assert audit['evidence']['seed8_translation_x_pos_strongest_pair_preserved'] is True
    assert audit['evidence']['seed8_rotation_z_pos_guardrail_preserved'] is True
    assert audit['inferred_outcome'] == 'translation_x_pos_x_family_carrier_margin_strengthening_repair_success'
