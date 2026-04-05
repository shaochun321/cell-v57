from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_process_x_direction_recovery_repair_audit import (
    build_translation_x_pos_process_x_direction_recovery_repair_audit,
)


def test_translation_x_pos_process_x_direction_recovery_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_process_x_direction_recovery_repair_audit(
        repeatability_audit_path='outputs/round34_repair/process_summary_repeatability_audit.json',
        seed7_translation_process_trace_path='outputs/round34_repair/seed_7/translation_x_pos/process_calculator_trace.json',
        seed7_translation_shell_trace_path='outputs/round34_repair/seed_7/translation_x_pos/mirror_shell_interface_trace.json',
        seed7_summary_analysis_path='outputs/round34_repair/seed_7/analysis/process_summary_atlas_analysis.json',
        seed8_translation_process_trace_path='outputs/round34_repair/seed_8/translation_x_pos/process_calculator_trace.json',
        seed8_translation_shell_trace_path='outputs/round34_repair/seed_8/translation_x_pos/mirror_shell_interface_trace.json',
        seed8_summary_analysis_path='outputs/round34_repair/seed_8/analysis/process_summary_atlas_analysis.json',
        seed8_rotation_process_trace_path='outputs/round34_repair/seed_8/rotation_z_pos/process_calculator_trace.json',
        seed8_rotation_shell_trace_path='outputs/round34_repair/seed_8/rotation_z_pos/mirror_shell_interface_trace.json',
        seed8_rotation_summary_analysis_path='outputs/round34_repair/seed_8/analysis/process_summary_atlas_analysis.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['inferred_outcome'] == 'translation_x_pos_process_x_direction_recovery_repair_success'

    ev = audit['evidence']
    assert ev['seed7_translation_x_pos_preserved_at_process_level'] is True
    assert ev['seed7_translation_x_pos_preserved_at_shell_level'] is True
    assert ev['seed7_translation_x_pos_preserved_at_summary_level'] is True
    assert ev['seed8_translation_x_pos_active_summary_recovered_to_translation_x'] is True
    assert ev['seed8_translation_x_pos_has_recovered_process_window'] is True
    assert ev['seed8_translation_x_pos_has_recovered_shell_window'] is True
    assert ev['seed8_rotation_z_pos_guardrail_preserved'] is True
    assert ev['seed8_translation_x_pos_residual_sign_instability_remains'] is True
