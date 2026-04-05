from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_x_neg_sign_limited_polarity_basis_audit import audit_translation_x_neg_sign_limited_polarity_basis_files


def test_translation_x_neg_sign_limited_polarity_basis_is_axis_preserving() -> None:
    payload = audit_translation_x_neg_sign_limited_polarity_basis_files(
        carrier_path=ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json',
        floor_path=ROOT / 'outputs/process_summary_translation_polarity_resolution_floor_audit_r1/process_summary_translation_polarity_resolution_floor_audit.json',
        decomposition_path=ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json',
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'x_neg_sign_limited_polarity_basis_inversion_with_axis_preservation'
    assert payload['evidence']['all_tracks_preserve_x_axis_for_x_neg'] is True
    assert payload['evidence']['all_tracks_flip_x_sign_for_x_neg'] is True
    assert payload['evidence']['all_tracks_flip_vector_sign_pattern_for_x_neg'] is True
    assert payload['evidence']['all_tracks_preserve_translation_family_for_x_neg'] is True
    assert payload['evidence']['x_neg_failure_is_not_resolution_floor_limited'] is True
    assert payload['evidence']['decomposition_already_classifies_x_neg_as_polarity_inversion'] is True
    assert payload['evidence']['x_neg_failure_is_sign_limited_with_axis_preservation'] is True
    assert payload['per_track']['discrete_channel_track']['dominant_axis_retained'] is True
    assert payload['per_track']['local_propagation_track']['dominant_axis_retained'] is True
    assert payload['per_track']['layered_coupling_track']['dominant_axis_retained'] is True
