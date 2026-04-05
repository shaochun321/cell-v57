from __future__ import annotations

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_x_carrier_source_restoration_audit import (
    build_translation_x_pos_seed8_x_carrier_source_restoration_audit,
)


def test_translation_x_pos_seed8_x_carrier_source_restoration_audit_local_outputs() -> None:
    audit = build_translation_x_pos_seed8_x_carrier_source_restoration_audit(
        repeatability_audit_path='outputs/round46_repair/process_summary_repeatability_audit.json',
        seed7_summary_path='outputs/round46_repair/seed_7/translation_x_pos/process_summary_atlas.json',
        seed7_atlas_trace_path='outputs/round46_repair/seed_7/translation_x_pos/mirror_channel_atlas_trace.json',
        seed8_summary_path='outputs/round46_repair/seed_8/translation_x_pos/process_summary_atlas.json',
        seed8_atlas_trace_path='outputs/round46_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json',
    )

    assert audit['contracts']['passed'] is True
    assert audit['evidence']['seed7_inner_shell_translation_carriers_present'] is True
    assert audit['evidence']['seed8_inner_shell_translation_carriers_missing'] is True
    assert audit['evidence']['seed8_outer_shell_translation_carriers_survive'] is True
    assert audit['evidence']['seed8_shell2_retention_loss_between_active_windows'] is True
    assert audit['evidence']['seed8_inner_shells_are_ultraweak_static_rows'] is True
    assert audit['inferred_primary_source'] == 'translation_x_pos_seed8_x_carrier_generation_loss'
