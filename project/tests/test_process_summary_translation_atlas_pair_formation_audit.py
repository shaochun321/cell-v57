from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_atlas_pair_formation_audit import audit_translation_atlas_pair_formation_files


def test_translation_atlas_pair_formation_audit_localizes_pair_collapse() -> None:
    payload = audit_translation_atlas_pair_formation_files(
        repeatability_report_path=ROOT / 'outputs/process_summary_repeatability_r1/process_summary_repeatability_protocol_report.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'atlas_pair_formation_collapse'
    assert payload['evidence']['family_wide_raw_sign_inversion']
    assert payload['evidence']['shell_interface_redistribution_detected']
    assert payload['evidence']['atlas_pair_formation_collapse_detected']
    per_seed = {int(r['seed']): r for r in payload['per_seed']}
    seed7 = per_seed[7]
    seed8 = per_seed[8]
    assert not seed7['family_atlas_pair_formation_collapse']
    assert seed8['family_atlas_pair_formation_collapse']
    assert seed8['cases']['translation_x_pos']['strongest_pair_mode'] == 'static_like'
    assert seed8['cases']['translation_x_pos']['strongest_pair_translation_margin'] < 0.0
    assert seed8['cases']['translation_x_neg']['strongest_pair_sign_ok'] is False
