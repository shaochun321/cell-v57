from __future__ import annotations

from pathlib import Path
from typing import Any
import json

TRACKS = [
    'discrete_channel_track',
    'local_propagation_track',
    'layered_coupling_track',
]


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _metric_row(ref: dict[str, Any], cur: dict[str, Any]) -> dict[str, Any]:
    ref_x = float(ref['x_balance'])
    cur_x = float(cur['x_balance'])
    ref_y = float(ref['y_balance'])
    cur_y = float(cur['y_balance'])
    ref_z = float(ref['z_balance'])
    cur_z = float(cur['z_balance'])
    return {
        'reference_x_balance': ref_x,
        'current_x_balance': cur_x,
        'reference_y_balance': ref_y,
        'current_y_balance': cur_y,
        'reference_z_balance': ref_z,
        'current_z_balance': cur_z,
        'x_sign_flipped': ref_x * cur_x < 0.0,
        'y_sign_flipped': ref_y * cur_y < 0.0,
        'z_sign_flipped': ref_z * cur_z < 0.0,
        'dominant_axis_retained': str(cur['dominant_axis']) == 'x',
        'x_sign_ok': bool(cur['x_sign_ok']),
        'translation_family_survives': bool(cur['translation_family_survives']),
        'axial_minus_swirl_ref': float(ref['axial_minus_swirl']),
        'axial_minus_swirl_cur': float(cur['axial_minus_swirl']),
        'axial_support_preserved': float(cur['axial_minus_swirl']) > 0.08,
        'resolution_floor_crossed': (abs(cur_x) - abs(cur_y)) <= 0.0 and abs(cur_x) / max(abs(ref_x), 1.0e-9) < 0.20,
    }


def audit_translation_x_neg_sign_limited_polarity_basis(*, carrier_payload: dict[str, Any], floor_payload: dict[str, Any], decomposition_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    rows = {int(r['seed']): r for r in carrier_payload.get('per_seed', [])}
    seed7 = rows.get(7)
    seed8 = rows.get(8)
    if seed7 is None or seed8 is None:
        failures.append('missing seed 7 or seed 8 row in carrier audit')

    per_track: dict[str, Any] = {}
    evidence = {
        'all_tracks_preserve_x_axis_for_x_neg': False,
        'all_tracks_flip_x_sign_for_x_neg': False,
        'all_tracks_flip_vector_sign_pattern_for_x_neg': False,
        'all_tracks_preserve_translation_family_for_x_neg': False,
        'x_neg_failure_is_not_resolution_floor_limited': False,
        'decomposition_already_classifies_x_neg_as_polarity_inversion': False,
        'x_neg_failure_is_sign_limited_with_axis_preservation': False,
    }

    if not failures:
        ref_tracks = seed7['cases']['translation_x_neg']['tracks']
        cur_tracks = seed8['cases']['translation_x_neg']['tracks']

        all_x_axis = True
        all_x_flip = True
        all_vector_flip = True
        all_family = True
        all_not_floor = True
        for track in TRACKS:
            row = _metric_row(ref_tracks[track], cur_tracks[track])
            per_track[track] = row
            all_x_axis &= bool(row['dominant_axis_retained'])
            all_x_flip &= bool(row['x_sign_flipped']) and not bool(row['x_sign_ok'])
            all_vector_flip &= bool(row['x_sign_flipped']) and bool(row['y_sign_flipped']) and bool(row['z_sign_flipped'])
            all_family &= bool(row['translation_family_survives']) and bool(row['axial_support_preserved'])
            all_not_floor &= not bool(row['resolution_floor_crossed'])

        floor_evidence = floor_payload.get('evidence', {})
        decomp_rows = {int(r['seed']): r for r in decomposition_payload.get('per_seed', [])}
        decomp_seed8 = decomp_rows.get(8, {})
        decomp_x_neg = decomp_seed8.get('cases', {}).get('translation_x_neg', {})

        evidence['all_tracks_preserve_x_axis_for_x_neg'] = all_x_axis
        evidence['all_tracks_flip_x_sign_for_x_neg'] = all_x_flip
        evidence['all_tracks_flip_vector_sign_pattern_for_x_neg'] = all_vector_flip
        evidence['all_tracks_preserve_translation_family_for_x_neg'] = all_family
        evidence['x_neg_failure_is_not_resolution_floor_limited'] = bool(floor_evidence.get('x_neg_failure_not_explained_by_resolution_floor')) and all_not_floor
        evidence['decomposition_already_classifies_x_neg_as_polarity_inversion'] = str(decomp_x_neg.get('dominant_failure_mode')) == 'polarity_projection_inversion'
        evidence['x_neg_failure_is_sign_limited_with_axis_preservation'] = (
            evidence['all_tracks_preserve_x_axis_for_x_neg']
            and evidence['all_tracks_flip_x_sign_for_x_neg']
            and evidence['all_tracks_preserve_translation_family_for_x_neg']
            and evidence['x_neg_failure_is_not_resolution_floor_limited']
        )

        if all(evidence.values()):
            primary = 'x_neg_sign_limited_polarity_basis_inversion_with_axis_preservation'
            secondary = [
                'cross_carrier_vector_sign_flip_without_axis_loss',
                'translation_family_support_remains_intact_while_sign_inverts',
                'resolution_floor_rejected_for_x_neg_failure',
            ]
            warnings.append(
                'x_neg does not fail by losing x-axis resolution: all tracks keep x dominant and translation family support while flipping sign, which is more consistent with a sign-limited polarity-basis inversion than with axis competition or smoothing loss'
            )
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to verify sign-limited x_neg polarity-basis inversion with axis preservation across translation tracks')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_x_neg_sign_limited_polarity_basis_audit',
        'evidence': evidence,
        'per_track': per_track,
        'inferred_primary_source': primary,
        'secondary_contributors': secondary,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }


def audit_translation_x_neg_sign_limited_polarity_basis_files(*, carrier_path: str | Path, floor_path: str | Path, decomposition_path: str | Path) -> dict[str, Any]:
    return audit_translation_x_neg_sign_limited_polarity_basis(
        carrier_payload=_load_json(carrier_path),
        floor_payload=_load_json(floor_path),
        decomposition_payload=_load_json(decomposition_path),
    )
