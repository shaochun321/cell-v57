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


def _float(v: Any) -> float:
    return float(v)


def audit_translation_discrete_channel_anatomy(*, carrier_payload: dict[str, Any], decomposition_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    rows = {int(r['seed']): r for r in carrier_payload.get('per_seed', [])}
    seed8 = rows.get(8)
    decomp_rows = {int(r['seed']): r for r in decomposition_payload.get('per_seed', [])}
    decomp8 = decomp_rows.get(8)

    if seed8 is None:
        failures.append('missing seed 8 row in translation interface family carrier audit')
    if decomp8 is None:
        failures.append('missing seed 8 row in translation carrier polarity decomposition')

    per_track: dict[str, Any] = {}
    evidence = {
        'shared_failure_classes_detected': False,
        'discrete_has_highest_failure_magnitudes': False,
        'discrete_has_highest_axis_energy': False,
        'discrete_has_highest_family_support': False,
        'local_and_layered_are_attenuated_versions': False,
    }

    if not failures:
        cases_c = seed8['cases']
        cases_d = decomp8['cases']

        orientation_scores: dict[str, float] = {}
        polarity_scores: dict[str, float] = {}
        axis_energy: dict[str, float] = {}
        family_support: dict[str, float] = {}
        shared_classes = {
            'x_pos': set(),
            'x_neg': set(),
        }

        for track_name in TRACKS:
            pos_c = cases_c['translation_x_pos']['tracks'][track_name]
            neg_c = cases_c['translation_x_neg']['tracks'][track_name]
            pos_d = cases_d['translation_x_pos']['tracks'][track_name]
            neg_d = cases_d['translation_x_neg']['tracks'][track_name]

            x_mag_pos = abs(_float(pos_c['x_balance']))
            y_mag_pos = abs(_float(pos_c['y_balance']))
            z_mag_pos = abs(_float(pos_c['z_balance']))
            x_mag_neg = abs(_float(neg_c['x_balance']))
            y_mag_neg = abs(_float(neg_c['y_balance']))
            z_mag_neg = abs(_float(neg_c['z_balance']))

            orientation_scores[track_name] = max(0.0, y_mag_pos - x_mag_pos)
            polarity_scores[track_name] = x_mag_neg if not bool(neg_c['x_sign_ok']) else 0.0
            axis_energy[track_name] = (x_mag_pos + y_mag_pos + z_mag_pos + x_mag_neg + y_mag_neg + z_mag_neg) / 2.0
            family_support[track_name] = (_float(pos_c['axial_minus_swirl']) + _float(neg_c['axial_minus_swirl'])) / 2.0
            shared_classes['x_pos'].add(pos_d['failure_classification'])
            shared_classes['x_neg'].add(neg_d['failure_classification'])

            per_track[track_name] = {
                'x_pos_failure_classification': pos_d['failure_classification'],
                'x_neg_failure_classification': neg_d['failure_classification'],
                'x_pos_orientation_override_score': orientation_scores[track_name],
                'x_neg_polarity_inversion_score': polarity_scores[track_name],
                'mean_axis_energy': axis_energy[track_name],
                'mean_family_support': family_support[track_name],
            }

        discrete = 'discrete_channel_track'
        local = 'local_propagation_track'
        layered = 'layered_coupling_track'

        shared_failure_classes = shared_classes['x_pos'] == {'x_axis_competition_override'} and shared_classes['x_neg'] == {'polarity_projection_inversion'}
        discrete_highest_failure_magnitudes = (
            orientation_scores[discrete] > orientation_scores[local] > orientation_scores[layered]
            and polarity_scores[discrete] > polarity_scores[local] > polarity_scores[layered]
        )
        discrete_highest_axis_energy = axis_energy[discrete] > axis_energy[local] > axis_energy[layered]
        discrete_highest_family_support = family_support[discrete] > family_support[local] > family_support[layered]
        local_and_layered_are_attenuated_versions = (
            shared_failure_classes and discrete_highest_failure_magnitudes and discrete_highest_axis_energy
        )

        evidence['shared_failure_classes_detected'] = shared_failure_classes
        evidence['discrete_has_highest_failure_magnitudes'] = discrete_highest_failure_magnitudes
        evidence['discrete_has_highest_axis_energy'] = discrete_highest_axis_energy
        evidence['discrete_has_highest_family_support'] = discrete_highest_family_support
        evidence['local_and_layered_are_attenuated_versions'] = local_and_layered_are_attenuated_versions

        if all(evidence.values()):
            primary = 'discrete_channel_track_preserves_highest_contrast_and_lowest_smoothing_across_translation_failures'
            secondary = ['local_and_layered_tracks_are_attenuated_versions_of_the_same_failure_classes', 'failure_is_cross_carrier_not_discrete_unique']
            warnings.append(
                'the discrete channel track is the sharpest translation-failure carrier because it preserves the highest axis-energy and family-support contrast under the shared post-shift failure geometry, while local and layered tracks show the same failure classes with attenuated magnitude'
            )
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to verify that discrete-channel sharpness is explained by higher retained contrast and lower smoothing')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_discrete_channel_anatomy_audit',
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


def audit_translation_discrete_channel_anatomy_files(*, carrier_path: str | Path, decomposition_path: str | Path) -> dict[str, Any]:
    return audit_translation_discrete_channel_anatomy(
        carrier_payload=_load_json(carrier_path),
        decomposition_payload=_load_json(decomposition_path),
    )
