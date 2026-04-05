from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit import (
    build_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit,
)


def test_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit_local_outputs() -> None:
    audit = build_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit(
        repeatability_audit_path='outputs/round36_repair/process_summary_repeatability_audit.json',
        seed7_summary_analysis_path='outputs/round36_repair/seed_7/analysis/process_summary_atlas_analysis.json',
        seed8_summary_analysis_path='outputs/round36_repair/seed_8/analysis/process_summary_atlas_analysis.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['evidence']['seed8_translation_x_pos_pair_mode_restored'] is True
    assert audit['evidence']['seed8_translation_x_neg_pair_mode_restored'] is True
    assert audit['evidence']['seed8_rotation_z_pos_guardrail_preserved'] is True
    assert audit['inferred_outcome'] == 'translation_x_family_strongest_pair_translation_mode_restoration_repair_success'
