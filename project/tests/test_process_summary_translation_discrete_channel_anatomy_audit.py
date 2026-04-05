from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_discrete_channel_anatomy_audit import audit_translation_discrete_channel_anatomy_files


def test_translation_discrete_channel_anatomy_identifies_highest_contrast_lowest_smoothing_track() -> None:
    payload = audit_translation_discrete_channel_anatomy_files(
        carrier_path=ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json',
        decomposition_path=ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'discrete_channel_track_preserves_highest_contrast_and_lowest_smoothing_across_translation_failures'
    assert payload['evidence']['shared_failure_classes_detected'] is True
    assert payload['evidence']['discrete_has_highest_failure_magnitudes'] is True
    assert payload['evidence']['discrete_has_highest_axis_energy'] is True
    assert payload['evidence']['discrete_has_highest_family_support'] is True
    assert payload['evidence']['local_and_layered_are_attenuated_versions'] is True
    assert payload['per_track']['discrete_channel_track']['x_pos_orientation_override_score'] > payload['per_track']['local_propagation_track']['x_pos_orientation_override_score'] > payload['per_track']['layered_coupling_track']['x_pos_orientation_override_score']
    assert payload['per_track']['discrete_channel_track']['x_neg_polarity_inversion_score'] > payload['per_track']['local_propagation_track']['x_neg_polarity_inversion_score'] > payload['per_track']['layered_coupling_track']['x_neg_polarity_inversion_score']
