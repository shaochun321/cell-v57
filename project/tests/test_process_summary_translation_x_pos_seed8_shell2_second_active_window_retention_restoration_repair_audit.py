from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit import (
    build_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit,
)


def test_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit(
        repeatability_audit_path='outputs/round49_repair/process_summary_repeatability_audit.json',
        seed8_baseline_summary_path='outputs/round48_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        seed8_baseline_atlas_trace_path='outputs/round48_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_repaired_summary_path='outputs/round49_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        seed8_repaired_atlas_trace_path='outputs/round49_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_xneg_summary_path='outputs/round49_repair/seed_8/translation_x_neg/process_summary_atlas.json',
        seed8_rotation_summary_path='outputs/round49_repair/seed_8/rotation_z_pos/process_summary_atlas.json',
    )
    assert audit['contracts']['passed'] is True
    assert audit['evidence']['baseline_seed8_second_active_shell2_static_like'] is True
    assert audit['evidence']['repaired_seed8_second_active_shell2_translation_like'] is True
    assert audit['evidence']['repaired_seed8_second_active_shell2_positive_sign'] is True
    assert audit['evidence']['repaired_seed8_active_translation_carrier_total_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_shell2_translation_carrier_count_exceeds_baseline'] is True
    assert audit['evidence']['repaired_seed8_translation_x_pos_active_mode_axis_preserved'] is True
    assert audit['evidence']['repaired_seed8_translation_x_neg_sign_preserved'] is True
    assert audit['evidence']['repaired_seed8_rotation_z_guardrail_preserved'] is True
    assert audit['inferred_outcome'] == 'translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_success'
