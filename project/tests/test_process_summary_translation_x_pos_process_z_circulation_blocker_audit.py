from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_process_z_circulation_blocker_audit import (
    build_translation_x_pos_process_z_circulation_blocker_audit,
)


def test_translation_x_pos_process_z_circulation_blocker_audit_local_outputs() -> None:
    audit = build_translation_x_pos_process_z_circulation_blocker_audit(
        repeatability_audit_path='outputs/round31_repeatability_base/process_summary_repeatability_audit.json',
        seed7_process_trace_path='outputs/round31_repeatability_base/seed_7/translation_x_pos/process_calculator_trace.json',
        seed7_shell_trace_path='outputs/round31_repeatability_base/seed_7/translation_x_pos/mirror_shell_interface_trace.json',
        seed8_process_trace_path='outputs/round31_repeatability_base/seed_8/translation_x_pos/process_calculator_trace.json',
        seed8_shell_trace_path='outputs/round31_repeatability_base/seed_8/translation_x_pos/mirror_shell_interface_trace.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['inferred_primary_source'] == 'translation_x_pos_process_z_circulation_blocker'

    ev = audit['evidence']
    assert ev['seed7_process_translation_reference_is_clean'] is True
    assert ev['seed8_process_is_rotation_z_before_shell'] is True
    assert ev['seed7_shell_override_promotes_translation_x'] is True
    assert ev['seed8_shell_override_never_forms_after_process_z_rotation'] is True
    assert ev['seed7_and_seed8_shell_summaries_are_both_locally_static'] is True

    seed8_window0 = audit['seed8']['active_process_windows'][0]
    assert seed8_window0['process'] == 'rotation_like/z'
    assert seed8_window0['mean_z_circulation'] > seed8_window0['mean_x_direction']
    assert seed8_window0['rotation_like'] > seed8_window0['translation_like']
