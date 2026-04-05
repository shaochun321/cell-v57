from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_residual_polarity_sign_restoration_repair_audit import (
    build_translation_x_pos_residual_polarity_sign_restoration_repair_audit,
)


def test_translation_x_pos_residual_polarity_sign_restoration_repair_audit_local_outputs() -> None:
    audit = build_translation_x_pos_residual_polarity_sign_restoration_repair_audit(
        repeatability_audit_path='outputs/round35_repair/process_summary_repeatability_audit.json',
        seed7_summary_analysis_path='outputs/round35_repair/seed_7/analysis/process_summary_atlas_analysis.json',
        seed8_summary_analysis_path='outputs/round35_repair/seed_8/analysis/process_summary_atlas_analysis.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['inferred_outcome'] == 'translation_x_family_residual_polarity_sign_restoration_repair_success'

    ev = audit['evidence']
    assert ev['seed7_translation_x_pos_positive_sign_preserved'] is True
    assert ev['seed7_translation_x_neg_negative_sign_preserved'] is True
    assert ev['seed8_translation_x_pos_positive_sign_restored'] is True
    assert ev['seed8_translation_x_neg_negative_sign_restored'] is True
    assert ev['seed8_translation_family_sign_flip_restored'] is True
    assert ev['seed8_translation_x_pos_active_mode_axis_preserved'] is True
    assert ev['seed8_translation_x_neg_active_mode_axis_preserved'] is True
    assert ev['seed8_rotation_z_pos_guardrail_preserved'] is True
    assert ev['seed8_translation_x_pos_strongest_pair_still_static_like'] is True
    assert ev['seed8_translation_x_neg_strongest_pair_still_static_like'] is True
