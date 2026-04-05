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


def audit_translation_polarity_basis_vs_pair_orientation_sensitivity(*, decomposition_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    seeds = [int(s) for s in decomposition_payload.get('seeds', [])]
    reference_seed = int(decomposition_payload.get('reference_seed', seeds[0] if seeds else 0))
    rows = {int(r['seed']): r for r in decomposition_payload.get('per_seed', [])}
    seed8 = rows.get(8)
    seed7 = rows.get(reference_seed)

    if seed7 is None:
        failures.append('missing reference seed row')
    if seed8 is None:
        failures.append('missing seed 8 row')

    per_case: dict[str, Any] = {}
    per_track: dict[str, Any] = {}
    evidence = {
        'x_pos_orientation_failure_is_cross_carrier': False,
        'x_neg_polarity_failure_is_cross_carrier': False,
        'orientation_sharpest_track_is_discrete': False,
        'polarity_sharpest_track_is_discrete': False,
        'common_most_sensitive_track_detected': False,
    }

    if not failures:
        cases8 = seed8['cases']
        x_pos_tracks = cases8['translation_x_pos']['tracks']
        x_neg_tracks = cases8['translation_x_neg']['tracks']

        orientation_scores: dict[str, float] = {}
        polarity_scores: dict[str, float] = {}

        for track_name in TRACKS:
            pos = x_pos_tracks[track_name]
            neg = x_neg_tracks[track_name]
            x_mag_pos = abs(_float(pos['x_balance']))
            y_mag_pos = abs(_float(pos['y_balance']))
            orientation_scores[track_name] = max(0.0, y_mag_pos - x_mag_pos)
            polarity_scores[track_name] = abs(_float(neg['x_balance'])) if not bool(neg['x_sign_ok']) else 0.0
            per_track[track_name] = {
                'x_pos_orientation_override_score': orientation_scores[track_name],
                'x_neg_polarity_inversion_score': polarity_scores[track_name],
                'x_pos_dominant_axis_seed8': pos['dominant_axis'],
                'x_neg_dominant_axis_seed8': neg['dominant_axis'],
                'x_pos_failure_classification_seed8': pos['failure_classification'],
                'x_neg_failure_classification_seed8': neg['failure_classification'],
            }

        pos_all_orientation = all(
            x_pos_tracks[t]['failure_classification'] == 'x_axis_competition_override' and x_pos_tracks[t]['dominant_axis'] == 'y'
            for t in TRACKS
        )
        neg_all_polarity = all(
            x_neg_tracks[t]['failure_classification'] == 'polarity_projection_inversion' and x_neg_tracks[t]['dominant_axis'] == 'x'
            for t in TRACKS
        )
        evidence['x_pos_orientation_failure_is_cross_carrier'] = pos_all_orientation
        evidence['x_neg_polarity_failure_is_cross_carrier'] = neg_all_polarity

        orientation_track = max(orientation_scores, key=orientation_scores.get)
        polarity_track = max(polarity_scores, key=polarity_scores.get)
        evidence['orientation_sharpest_track_is_discrete'] = orientation_track == 'discrete_channel_track'
        evidence['polarity_sharpest_track_is_discrete'] = polarity_track == 'discrete_channel_track'
        evidence['common_most_sensitive_track_detected'] = orientation_track == polarity_track == 'discrete_channel_track'

        per_case['translation_x_pos'] = {
            'seed8_dominant_failure_mode': cases8['translation_x_pos']['dominant_failure_mode'],
            'cross_carrier_orientation_failure': pos_all_orientation,
            'sharpest_orientation_track': orientation_track,
            'sharpest_orientation_score': orientation_scores[orientation_track],
        }
        per_case['translation_x_neg'] = {
            'seed8_dominant_failure_mode': cases8['translation_x_neg']['dominant_failure_mode'],
            'cross_carrier_polarity_failure': neg_all_polarity,
            'sharpest_polarity_track': polarity_track,
            'sharpest_polarity_score': polarity_scores[polarity_track],
        }

        if pos_all_orientation and neg_all_polarity and orientation_track == polarity_track == 'discrete_channel_track':
            primary = 'discrete_channel_track_is_sharpest_for_both_post_shift_failure_modes'
            secondary = ['cross_carrier_failure_persistence', 'local_and_layered_tracks_show_same_failure_classes']
            warnings.append(
                'translation_x_pos loses x dominance across all carriers while translation_x_neg preserves x but flips polarity across all carriers; the discrete channel track is the sharpest manifestation of both post-shift failure modes, though the instability is cross-carrier rather than track-local'
            )
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to identify a common carrier-level sensitivity pattern across orientation and polarity failure modes')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_polarity_basis_vs_pair_orientation_sensitivity_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'evidence': evidence,
        'per_case': per_case,
        'per_track': per_track,
        'inferred_primary_source': primary,
        'secondary_contributors': secondary,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }


def audit_translation_polarity_basis_vs_pair_orientation_sensitivity_files(*, decomposition_path: str | Path) -> dict[str, Any]:
    return audit_translation_polarity_basis_vs_pair_orientation_sensitivity(
        decomposition_payload=_load_json(decomposition_path),
    )
