from __future__ import annotations

import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit import (
    build_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit,
)


def test_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit_round59() -> None:
    base = Path('outputs')
    audit = build_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit(
        round52_seed8_summary_path=base / 'round52_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round58_seed8_summary_path=base / 'round58_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round58_seed8_atlas_trace_path=base / 'round58_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round59_seed8_summary_path=base / 'round59_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        round59_seed8_atlas_trace_path=base / 'round59_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
        round59_seed8_xneg_summary_path=base / 'round59_repair/seed_8/translation_x_neg/process_summary_atlas.json',
        round59_seed8_rotation_pos_summary_path=base / 'round59_repair/seed_8/rotation_z_pos/process_summary_atlas.json',
        round59_seed8_rotation_neg_summary_path=base / 'round59_repair/seed_8/rotation_z_neg/process_summary_atlas.json',
        repeatability_audit_path=base / 'round59_repair/process_summary_repeatability_audit.json',
    )
    assert audit['contracts']['passed']
    assert audit['evidence']['round59_seed8_shell0_shell1_positive_translation_present_in_both_active_windows']
    assert audit['evidence']['round59_seed8_joint_inner_core_density_exceeds_round58']
    assert audit['evidence']['round59_seed8_final_mean_exceeds_round58']
    assert audit['evidence']['round59_seed8_raw_mean_exceeds_round58']
    assert audit['evidence']['round59_seed8_translation_x_pos_active_mode_axis_preserved']
    assert audit['evidence']['round59_seed8_translation_x_neg_sign_preserved']
    assert audit['evidence']['round59_seed8_rotation_z_pos_guardrail_preserved']
    assert audit['evidence']['round59_seed8_rotation_z_neg_guardrail_preserved']
    assert audit['evidence']['round59_seed8_final_mean_still_below_round52_frozen_baseline']
