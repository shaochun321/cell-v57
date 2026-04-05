from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_carrier_polarity_decomposition import (
    decompose_translation_carrier_polarity_files,
)


def test_translation_carrier_polarity_decomposition_finds_asymmetric_failure_modes() -> None:
    payload = decompose_translation_carrier_polarity_files(
        carrier_audit_path=ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'asymmetric_translation_carrier_failure_modes'
    assert payload['evidence']['x_pos_axis_competition_detected'] is True
    assert payload['evidence']['x_neg_polarity_inversion_detected'] is True
    assert payload['evidence']['asymmetric_failure_modes_detected'] is True

    rows = {int(r['seed']): r for r in payload['per_seed']}
    seed8 = rows[8]
    assert seed8['cases']['translation_x_pos']['dominant_failure_mode'] == 'x_axis_competition_override'
    assert seed8['cases']['translation_x_neg']['dominant_failure_mode'] == 'polarity_projection_inversion'
