from __future__ import annotations

from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit import (
    build_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit,
)


def test_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit_round60() -> None:
    base = Path('outputs')
    audit = build_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit(
        round52_seed8_summary_path=base / 'round52_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round59_seed8_summary_path=base / 'round59_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round59_seed8_atlas_trace_path=base / 'round59_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round60_seed8_summary_path=base / 'round60_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round60_seed8_atlas_trace_path=base / 'round60_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round60_seed8_xneg_summary_path=base / 'round60_repair/seed_8/translation_x_neg/process_summary_atlas.json',
        round60_seed8_rotation_pos_summary_path=base / 'round60_repair/seed_8/rotation_z_pos/process_summary_atlas.json',
        round60_seed8_rotation_neg_summary_path=base / 'round60_repair/seed_8/rotation_z_neg/process_summary_atlas.json',
        repeatability_audit_path=base / 'round59_repair/process_summary_repeatability_audit.json',
    )
    assert audit['contracts']['passed']
    assert audit['evidence']['round60_seed8_shell012_positive_translation_present_in_both_active_windows']
    assert audit['evidence']['round60_seed8_inner_core_density_exceeds_round59']
    assert audit['evidence']['round60_seed8_final_mean_exceeds_round59']
    assert audit['evidence']['round60_seed8_raw_mean_exceeds_round59']
    assert audit['evidence']['round60_seed8_translation_x_pos_active_mode_axis_preserved']
    assert audit['evidence']['round60_seed8_translation_x_neg_sign_preserved']
    assert audit['evidence']['round60_seed8_rotation_z_pos_guardrail_preserved']
    assert audit['evidence']['round60_seed8_rotation_z_neg_guardrail_preserved']
    assert audit['evidence']['round60_seed8_final_mean_within_frozen_round52_tolerance']
