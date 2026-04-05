from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_carrier_smoothing_sensitivity_audit import audit_translation_carrier_smoothing_sensitivity_files


def test_translation_carrier_smoothing_sensitivity_identifies_passive_low_pass_limit() -> None:
    payload = audit_translation_carrier_smoothing_sensitivity_files(
        anatomy_path=ROOT / 'outputs/process_summary_translation_discrete_channel_anatomy_audit_r1/process_summary_translation_discrete_channel_anatomy_audit.json',
        carrier_path=ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'passive_smoothing_attenuates_translation_failures_but_cannot_replace_discrete_polarity_resolution'
    assert payload['evidence']['cross_carrier_failures_persist_under_smoothing'] is True
    assert payload['evidence']['smoothing_attenuates_but_does_not_change_failure_classes'] is True
    assert payload['evidence']['smoothed_tracks_do_not_restore_x_pos_x_dominance'] is True
    assert payload['evidence']['smoothed_tracks_do_not_restore_x_neg_polarity'] is True
    assert payload['evidence']['discrete_not_false_positive_due_to_over_sharpness'] is True
    assert payload['per_track']['local_propagation_track']['x_pos_dominant_axis'] == 'y'
    assert payload['per_track']['layered_coupling_track']['x_pos_dominant_axis'] == 'y'
    assert payload['per_track']['local_propagation_track']['x_neg_x_sign_ok'] is False
    assert payload['per_track']['layered_coupling_track']['x_neg_x_sign_ok'] is False
