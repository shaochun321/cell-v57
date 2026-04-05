from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_polarity_basis_vs_pair_orientation_sensitivity_audit import audit_translation_polarity_basis_vs_pair_orientation_sensitivity_files


def test_translation_sensitivity_identifies_discrete_as_sharpest_cross_carrier_manifestation() -> None:
    payload = audit_translation_polarity_basis_vs_pair_orientation_sensitivity_files(
        decomposition_path=ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'discrete_channel_track_is_sharpest_for_both_post_shift_failure_modes'
    assert payload['evidence']['x_pos_orientation_failure_is_cross_carrier'] is True
    assert payload['evidence']['x_neg_polarity_failure_is_cross_carrier'] is True
    assert payload['evidence']['orientation_sharpest_track_is_discrete'] is True
    assert payload['evidence']['polarity_sharpest_track_is_discrete'] is True
    assert payload['evidence']['common_most_sensitive_track_detected'] is True
    assert payload['per_case']['translation_x_pos']['sharpest_orientation_track'] == 'discrete_channel_track'
    assert payload['per_case']['translation_x_neg']['sharpest_polarity_track'] == 'discrete_channel_track'
