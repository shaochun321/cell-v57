# M2.4 commands

```bash
cd /mnt/data/round60work
PYTHONPATH=src pytest -q   tests/test_mirror_channel_atlas.py   tests/test_process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit.py

PYTHONPATH=src python scripts/run_process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit_protocol.py   --round52-seed8-summary outputs/round52_repair/seed_8/translation_x_pos/process_summary_atlas.json   --round59-seed8-summary outputs/round59_repair/seed_8/translation_x_pos/process_summary_atlas.json   --round59-seed8-atlas-trace outputs/round59_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json   --round60-seed8-summary outputs/round60_repair/seed_8/translation_x_pos/process_summary_atlas.json   --round60-seed8-atlas-trace outputs/round60_repair/seed_8/translation_x_pos/mirror_channel_atlas_trace.json   --round60-seed8-xneg-summary outputs/round60_repair/seed_8/translation_x_neg/process_summary_atlas.json   --round60-seed8-rotation-pos-summary outputs/round60_repair/seed_8/rotation_z_pos/process_summary_atlas.json   --round60-seed8-rotation-neg-summary outputs/round60_repair/seed_8/rotation_z_neg/process_summary_atlas.json   --repeatability-audit outputs/round59_repair/process_summary_repeatability_audit.json   --outdir outputs/m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit

PYTHONPATH=src python scripts/analyze_process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit.py   --audit outputs/m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit/process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit.json   --outdir outputs/m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit
```
