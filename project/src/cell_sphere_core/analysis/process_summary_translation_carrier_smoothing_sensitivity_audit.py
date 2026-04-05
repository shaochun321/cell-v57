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


def audit_translation_carrier_smoothing_sensitivity(*, anatomy_payload: dict[str, Any], carrier_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    anatomy_evidence = anatomy_payload.get('evidence', {})
    carrier_rows = {int(r['seed']): r for r in carrier_payload.get('per_seed', [])}
    seed8 = carrier_rows.get(8)
    if seed8 is None:
        failures.append('missing seed 8 row in translation interface family carrier audit')

    per_track: dict[str, Any] = {}
    evidence = {
        'cross_carrier_failures_persist_under_smoothing': False,
        'smoothing_attenuates_but_does_not_change_failure_classes': False,
        'smoothed_tracks_do_not_restore_x_pos_x_dominance': False,
        'smoothed_tracks_do_not_restore_x_neg_polarity': False,
        'discrete_not_false_positive_due_to_over_sharpness': False,
    }

    if not failures:
        cases = seed8['cases']
        x_pos = cases['translation_x_pos']['tracks']
        x_neg = cases['translation_x_neg']['tracks']

        cross_carrier = anatomy_evidence.get('shared_failure_classes_detected') is True
        attenuated_versions = anatomy_evidence.get('local_and_layered_are_attenuated_versions') is True

        pos_local_layered_y = (
            x_pos['local_propagation_track']['dominant_axis'] == 'y'
            and x_pos['layered_coupling_track']['dominant_axis'] == 'y'
        )
        neg_local_layered_sign_bad = (
            not bool(x_neg['local_propagation_track']['x_sign_ok'])
            and not bool(x_neg['layered_coupling_track']['x_sign_ok'])
        )

        all_tracks_failed = (
            bool(cases['translation_x_pos'].get('all_tracks_broken'))
            and bool(cases['translation_x_neg'].get('all_tracks_broken'))
        )

        evidence['cross_carrier_failures_persist_under_smoothing'] = cross_carrier and all_tracks_failed
        evidence['smoothing_attenuates_but_does_not_change_failure_classes'] = attenuated_versions
        evidence['smoothed_tracks_do_not_restore_x_pos_x_dominance'] = pos_local_layered_y
        evidence['smoothed_tracks_do_not_restore_x_neg_polarity'] = neg_local_layered_sign_bad
        evidence['discrete_not_false_positive_due_to_over_sharpness'] = (
            cross_carrier and attenuated_versions and pos_local_layered_y and neg_local_layered_sign_bad
        )

        for track_name in TRACKS:
            x_pos_class = 'x_axis_competition_override' if x_pos[track_name]['dominant_axis'] == 'y' else 'carrier_ok'
            x_neg_class = 'polarity_projection_inversion' if not bool(x_neg[track_name]['x_sign_ok']) else 'carrier_ok'
            per_track[track_name] = {
                'x_pos_failure_classification': x_pos_class,
                'x_pos_dominant_axis': x_pos[track_name]['dominant_axis'],
                'x_neg_failure_classification': x_neg_class,
                'x_neg_x_sign_ok': bool(x_neg[track_name]['x_sign_ok']),
                'x_pos_axial_minus_swirl': float(x_pos[track_name]['axial_minus_swirl']),
                'x_neg_axial_minus_swirl': float(x_neg[track_name]['axial_minus_swirl']),
            }

        if all(evidence.values()):
            primary = 'passive_smoothing_attenuates_translation_failures_but_cannot_replace_discrete_polarity_resolution'
            secondary = [
                'local_and_layered_tracks_are_low_pass_versions_of_the_same_failure_geometry',
                'discrete_track_is_not_a_false_positive_but_the_highest_contrast_readout',
            ]
            warnings.append(
                'local and layered tracks attenuate the same post-shift translation failure geometry, but they do not restore x-dominance for translation_x_pos or polarity correctness for translation_x_neg; the problem is not that discrete alone fabricates a sharp artifact, but that smoothing cannot recover lost polarity resolution'
            )
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to verify that smoothing only attenuates translation failure rather than resolving it')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_carrier_smoothing_sensitivity_audit',
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


def audit_translation_carrier_smoothing_sensitivity_files(*, anatomy_path: str | Path, carrier_path: str | Path) -> dict[str, Any]:
    return audit_translation_carrier_smoothing_sensitivity(
        anatomy_payload=_load_json(anatomy_path),
        carrier_payload=_load_json(carrier_path),
    )
