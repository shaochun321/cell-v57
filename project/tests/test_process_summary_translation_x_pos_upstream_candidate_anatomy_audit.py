from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_upstream_candidate_anatomy_audit import build_translation_x_pos_upstream_candidate_anatomy_audit


def test_translation_x_pos_upstream_candidate_anatomy_audit_local_outputs() -> None:
    audit = build_translation_x_pos_upstream_candidate_anatomy_audit(
        repeatability_audit_path='outputs/round31_repeatability_base/process_summary_repeatability_audit.json',
        seed7_process_trace_path='outputs/round31_repeatability_base/seed_7/translation_x_pos/process_calculator_trace.json',
        seed7_shell_trace_path='outputs/round31_repeatability_base/seed_7/translation_x_pos/mirror_shell_interface_trace.json',
        seed7_atlas_trace_path='outputs/round31_repeatability_base/seed_7/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_process_trace_path='outputs/round31_repeatability_base/seed_8/translation_x_pos/process_calculator_trace.json',
        seed8_shell_trace_path='outputs/round31_repeatability_base/seed_8/translation_x_pos/mirror_shell_interface_trace.json',
        seed8_atlas_trace_path='outputs/round31_repeatability_base/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['inferred_primary_source'] == 'translation_x_pos_upstream_candidate_selection_collapse'

    ev = audit['evidence']
    assert ev['seed7_reference_chain_is_clean'] is True
    assert ev['seed8_process_to_shell_break_occurs_before_handoff'] is True
    assert ev['seed8_shell2_x_survives_but_does_not_mature'] is True
    assert ev['seed8_shell2_can_still_lean_x_locally'] is True
    assert ev['seed8_shell3_y_preempts_after_collapse'] is True

    seed8_windows = audit['seed8']['active_windows']
    assert seed8_windows[0]['process'] == 'rotation_like/z'
    assert seed8_windows[0]['shell'] == 'static_like/none'
    assert seed8_windows[0]['atlas'] == 'static_like/z'
    assert seed8_windows[0]['strongest_pair'] == 'static_like/none'
