from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_mirrored_asymmetry_audit import audit_translation_mirrored_asymmetry_files


def test_translation_mirrored_asymmetry_prefers_geometry_bias_after_shared_shift() -> None:
    payload = audit_translation_mirrored_asymmetry_files(
        seed_profiles_path=ROOT / 'outputs/process_summary_translation_mirrored_readout_audit_r1/process_summary_translation_mirrored_readout_seed_profiles.json',
        decomposition_path=ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'mirrored_carrier_geometry_bias_after_shared_outer_shift'
    assert payload['evidence']['shared_outer_shift_detected'] is True
    assert payload['evidence']['symmetric_outer_shift_detected'] is True
    assert payload['evidence']['post_shift_failure_asymmetry_detected'] is True
    assert payload['evidence']['early_shell_to_carrier_diversion_detected'] is False
    pos = payload['per_case']['translation_x_pos']
    neg = payload['per_case']['translation_x_neg']
    assert pos['pair_strength_shell_shift'] == 3
    assert neg['pair_strength_shell_shift'] == 3
    assert pos['dominant_failure_mode_cmp'] == 'x_axis_competition_override'
    assert neg['dominant_failure_mode_cmp'] == 'polarity_projection_inversion'
