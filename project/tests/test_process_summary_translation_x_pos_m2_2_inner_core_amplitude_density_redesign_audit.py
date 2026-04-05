from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit import (
    build_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit,
)


def test_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit_local_outputs() -> None:
    audit = build_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit(
        round52_seed8_summary_path='outputs/round52_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round57_seed8_summary_path='outputs/round57_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round57_seed8_atlas_trace_path='outputs/round57_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round58_seed8_summary_path='outputs/round58_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round58_seed8_atlas_trace_path='outputs/round58_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round58_seed8_xneg_summary_path='outputs/round58_repair/seed_8/translation_x_neg/process_summary_atlas.json',
        round58_seed8_rotation_pos_summary_path='outputs/round58_repair/seed_8/rotation_z_pos/process_summary_atlas.json',
        round58_seed8_rotation_neg_summary_path='outputs/round58_repair/seed_8/rotation_z_neg/process_summary_atlas.json',
        repeatability_audit_path='outputs/round58_repair/process_summary_repeatability_audit.json',
    )
    assert audit['contracts']['passed'] is True
    assert audit['evidence']['round58_seed8_shell0_translation_present_in_both_active_windows'] is True
    assert audit['evidence']['round58_seed8_final_mean_exceeds_round57'] is True
    assert audit['evidence']['round58_seed8_raw_mean_exceeds_round57'] is True
    assert audit['evidence']['round58_seed8_translation_x_pos_active_mode_axis_preserved'] is True
    assert audit['evidence']['round58_seed8_translation_x_neg_sign_preserved'] is True
    assert audit['evidence']['round58_seed8_rotation_z_pos_guardrail_preserved'] is True
    assert audit['evidence']['round58_seed8_rotation_z_neg_guardrail_preserved'] is True
    assert audit['evidence']['round58_seed8_final_mean_still_below_round52_frozen_baseline'] is True
