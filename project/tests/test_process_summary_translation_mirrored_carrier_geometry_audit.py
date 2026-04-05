from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_mirrored_carrier_geometry_audit import audit_translation_mirrored_carrier_geometry_files


def test_translation_mirrored_carrier_geometry_decomposes_shared_shift() -> None:
    payload = audit_translation_mirrored_carrier_geometry_files(
        seed_profiles_path=ROOT / 'outputs/process_summary_translation_mirrored_readout_audit_r1/process_summary_translation_mirrored_readout_seed_profiles.json',
        decomposition_path=ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'mirrored_geometry_bias_decomposes_into_pair_orientation_and_polarity_basis_asymmetry'
    assert payload['evidence']['x_pos_pair_orientation_bias_detected'] is True
    assert payload['evidence']['x_neg_polarity_basis_asymmetry_detected'] is True
    assert payload['evidence']['mirrored_failure_modes_split_detected'] is True
    assert payload['evidence']['common_single_geometry_mechanism_rejected'] is True
    pos = payload['per_case']['translation_x_pos']
    neg = payload['per_case']['translation_x_neg']
    assert pos['dominant_failure_mode_cmp'] == 'x_axis_competition_override'
    assert neg['dominant_failure_mode_cmp'] == 'polarity_projection_inversion'
    assert pos['comparison_pair_sign_ok'] is False
    assert neg['comparison_pair_sign_ok'] is False
