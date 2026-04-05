from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit import (
    build_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit,
)


def test_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit(
        repeatability_audit_path='outputs/round54_repair/process_summary_repeatability_audit.json',
        seed7_reference_summary_path='outputs/round52_repair/seed_7/translation_x_pos/process_summary_atlas.json',
        seed8_baseline_summary_path='outputs/round52_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        seed8_baseline_atlas_trace_path='outputs/round52_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_repaired_summary_path='outputs/round54_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        seed8_repaired_atlas_trace_path='outputs/round54_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_xneg_summary_path='outputs/round54_repair/seed_8/translation_x_neg/process_summary_atlas.json',
        seed8_rotation_pos_summary_path='outputs/round54_repair/seed_8/rotation_z_pos/process_summary_atlas.json',
        seed8_rotation_neg_summary_path='outputs/round54_repair/seed_8/rotation_z_neg/process_summary_atlas.json',
    )
    assert audit['contracts']['passed'] is True
    assert audit['evidence']['repaired_seed8_shell1_translation_present_in_both_active_windows'] is True
    assert audit['evidence']['repaired_seed8_active_translation_carrier_total_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_translation_carrier_pair_count_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_raw_mean_polarity_projection_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_shell1_peak_polarity_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_final_mean_within_point001_of_baseline'] is True
    assert audit['evidence']['repaired_seed8_raw_gap_to_seed7_reduced'] is True
    assert audit['evidence']['repaired_seed8_translation_x_pos_active_mode_axis_preserved'] is True
    assert audit['evidence']['repaired_seed8_translation_x_neg_sign_preserved'] is True
    assert audit['evidence']['repaired_seed8_rotation_z_pos_guardrail_preserved'] is True
    assert audit['evidence']['repaired_seed8_rotation_z_neg_guardrail_preserved'] is True
    assert audit['inferred_outcome'] == 'translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_success'
