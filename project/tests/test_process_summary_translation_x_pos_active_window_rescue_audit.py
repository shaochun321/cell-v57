from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_active_window_rescue_audit import build_translation_x_pos_active_window_rescue_audit


def test_translation_x_pos_active_window_rescue_audit_local_outputs() -> None:
    audit = build_translation_x_pos_active_window_rescue_audit(
        repeatability_audit_path='outputs/round31_repeatability_base/process_summary_repeatability_audit.json',
        seed7_analysis_path='outputs/round31_repeatability_base/seed_7/analysis/process_summary_atlas_analysis.json',
        seed8_analysis_path='outputs/round31_repeatability_base/seed_8/analysis/process_summary_atlas_analysis.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['inferred_primary_source'] == 'translation_x_pos_active_window_upstream_static_collapse_before_handoff_gate'

    ev = audit['evidence']
    assert ev['seed7_translation_like_x_reference_is_clean'] is True
    assert ev['seed8_active_mode_still_translation_like'] is True
    assert ev['seed8_active_axis_is_y_not_x'] is True
    assert ev['seed8_gate_still_passes_pairs'] is True
    assert ev['seed8_upstream_axis_match_collapses_to_zero'] is True
    assert ev['seed8_strongest_pair_arrives_as_static_like_none'] is True
    assert ev['seed8_failure_occurs_before_handoff_gate_can_rescue'] is True

    assert audit['seed7']['upstream_axis_match_fraction'] == 1.0
    assert audit['seed8']['upstream_axis_match_fraction'] == 0.0
    assert audit['seed8']['strongest_pair_mode'] == 'static_like'
    assert audit['seed8']['strongest_pair_axis'] == 'y'
