from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_inner_outer_shell_audit import audit_translation_inner_outer_shell_files


def test_translation_inner_outer_shell_audit_localizes_readout_redistribution() -> None:
    payload = audit_translation_inner_outer_shell_files(
        repeatability_report_path=ROOT / 'outputs/process_summary_repeatability_r1/process_summary_repeatability_audit.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'mirrored_translation_readout_redistribution'
    assert payload['evidence']['outer_shell_shift_detected']
    assert payload['evidence']['strongest_pair_sign_failure_detected']
    per_seed = {int(r['seed']): r for r in payload['per_seed']}
    seed8 = per_seed[8]
    assert seed8['family_raw_inversion']
    assert seed8['family_outer_shift']
    assert seed8['family_pair_sign_failure']
    assert seed8['cases']['translation_x_pos']['strongest_shell'] == 3
    assert seed8['cases']['translation_x_neg']['strongest_shell'] == 3
    assert seed8['cases']['translation_x_pos']['strongest_pair_polarity_projection'] < 0.0
    assert seed8['cases']['translation_x_neg']['strongest_pair_polarity_projection'] > 0.0
