# M2.4 baseline recheck commands

## Run audit
```bash
PYTHONPATH=src python scripts/run_process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit_protocol.py
```

## Run analysis export
```bash
PYTHONPATH=src python scripts/analyze_process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.py
```

## Run test
```bash
PYTHONPATH=src pytest -q tests/test_process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.py
```

## Generated files
- `outputs/m2_4_material_baseline_recheck_audit/process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.json`
- `outputs/m2_4_material_baseline_recheck_audit/process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit_analysis.json`
- `outputs/m2_4_material_baseline_recheck_audit/process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.png`
