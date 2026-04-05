from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_polarity_resolution_floor_audit import audit_translation_polarity_resolution_floor_files


def test_translation_polarity_resolution_floor_is_one_sided() -> None:
    payload = audit_translation_polarity_resolution_floor_files(
        carrier_path=ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json',
        smoothing_path=ROOT / 'outputs/process_summary_translation_carrier_smoothing_sensitivity_audit_r1/process_summary_translation_carrier_smoothing_sensitivity_audit.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'x_pos_crosses_translation_polarity_resolution_floor_while_x_neg_failure_remains_above_floor_and_is_sign_limited'
    assert payload['evidence']['x_pos_resolution_floor_crossed_across_tracks'] is True
    assert payload['evidence']['x_neg_failure_not_explained_by_resolution_floor'] is True
    assert payload['evidence']['local_and_layered_below_floor_for_x_pos'] is True
    assert payload['evidence']['smoothing_cannot_restore_polarity_once_x_pos_floor_is_crossed'] is True
    assert payload['evidence']['polarity_resolution_floor_is_one_sided_not_full_translation_explanation'] is True
    assert payload['per_track']['local_propagation_track']['x_pos']['floor_crossed'] is True
    assert payload['per_track']['layered_coupling_track']['x_pos']['floor_crossed'] is True
    assert payload['per_track']['discrete_channel_track']['x_neg']['floor_crossed'] is False
    assert payload['per_track']['local_propagation_track']['x_neg']['floor_crossed'] is False
    assert payload['per_track']['layered_coupling_track']['x_neg']['floor_crossed'] is False
