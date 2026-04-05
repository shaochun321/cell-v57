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


def _track_metrics(ref: dict[str, Any], cur: dict[str, Any]) -> dict[str, float | bool | str]:
    ref_x = float(ref['x_balance'])
    ref_y = float(ref['y_balance'])
    cur_x = float(cur['x_balance'])
    cur_y = float(cur['y_balance'])
    ref_axis_margin = abs(ref_x) - abs(ref_y)
    cur_axis_margin = abs(cur_x) - abs(cur_y)
    retention_ratio = abs(cur_x) / max(abs(ref_x), 1.0e-9)
    floor_crossed = cur_axis_margin <= 0.0 and retention_ratio < 0.20
    return {
        'reference_x_balance': ref_x,
        'current_x_balance': cur_x,
        'reference_y_balance': ref_y,
        'current_y_balance': cur_y,
        'reference_axis_margin': ref_axis_margin,
        'current_axis_margin': cur_axis_margin,
        'x_retention_ratio': retention_ratio,
        'floor_crossed': floor_crossed,
        'dominant_axis': str(cur['dominant_axis']),
        'x_sign_ok': bool(cur['x_sign_ok']),
    }


def audit_translation_polarity_resolution_floor(*, carrier_payload: dict[str, Any], smoothing_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    rows = {int(r['seed']): r for r in carrier_payload.get('per_seed', [])}
    seed7 = rows.get(7)
    seed8 = rows.get(8)
    if seed7 is None or seed8 is None:
        failures.append('missing seed 7 or seed 8 row in translation interface family carrier audit')

    per_track: dict[str, Any] = {}
    evidence = {
        'x_pos_resolution_floor_crossed_across_tracks': False,
        'x_neg_failure_not_explained_by_resolution_floor': False,
        'local_and_layered_below_floor_for_x_pos': False,
        'smoothing_cannot_restore_polarity_once_x_pos_floor_is_crossed': False,
        'polarity_resolution_floor_is_one_sided_not_full_translation_explanation': False,
    }

    if not failures:
        seed7_cases = seed7['cases']
        seed8_cases = seed8['cases']
        x_pos_seed7 = seed7_cases['translation_x_pos']['tracks']
        x_pos_seed8 = seed8_cases['translation_x_pos']['tracks']
        x_neg_seed7 = seed7_cases['translation_x_neg']['tracks']
        x_neg_seed8 = seed8_cases['translation_x_neg']['tracks']

        x_pos_floor_count = 0
        x_neg_above_floor_count = 0
        local_layered_below = True
        x_neg_sign_bad_all = True

        for track in TRACKS:
            pos_metrics = _track_metrics(x_pos_seed7[track], x_pos_seed8[track])
            neg_metrics = _track_metrics(x_neg_seed7[track], x_neg_seed8[track])
            per_track[track] = {
                'x_pos': pos_metrics,
                'x_neg': neg_metrics,
            }
            if bool(pos_metrics['floor_crossed']):
                x_pos_floor_count += 1
            if not bool(neg_metrics['floor_crossed']):
                x_neg_above_floor_count += 1
            if track in {'local_propagation_track', 'layered_coupling_track'}:
                local_layered_below &= bool(pos_metrics['floor_crossed'])
            x_neg_sign_bad_all &= not bool(neg_metrics['x_sign_ok'])

        smoothing_evidence = smoothing_payload.get('evidence', {})
        evidence['x_pos_resolution_floor_crossed_across_tracks'] = x_pos_floor_count == len(TRACKS)
        evidence['x_neg_failure_not_explained_by_resolution_floor'] = x_neg_above_floor_count == len(TRACKS) and x_neg_sign_bad_all
        evidence['local_and_layered_below_floor_for_x_pos'] = local_layered_below
        evidence['smoothing_cannot_restore_polarity_once_x_pos_floor_is_crossed'] = (
            bool(smoothing_evidence.get('smoothed_tracks_do_not_restore_x_pos_x_dominance'))
            and bool(smoothing_evidence.get('smoothed_tracks_do_not_restore_x_neg_polarity'))
        )
        evidence['polarity_resolution_floor_is_one_sided_not_full_translation_explanation'] = (
            evidence['x_pos_resolution_floor_crossed_across_tracks']
            and evidence['x_neg_failure_not_explained_by_resolution_floor']
        )

        if all(evidence.values()):
            primary = 'x_pos_crosses_translation_polarity_resolution_floor_while_x_neg_failure_remains_above_floor_and_is_sign_limited'
            secondary = [
                'local_and_layered_tracks_fall_below_floor_for_x_pos_after_shared_shift',
                'smoothing_cannot_recover_x_polarity_once_floor_is_crossed',
                'x_neg_failure_requires_polarity_basis_explanation_not_resolution_floor',
            ]
            warnings.append(
                'translation polarity-resolution floor is real, but it only explains the x_pos side of the post-shift failure: all three tracks lose enough x-vs-y separation to cross the floor there, whereas x_neg stays above the floor and still fails due to sign inversion'
            )
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to verify one-sided polarity-resolution floor behavior across translation tracks')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_polarity_resolution_floor_audit',
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


def audit_translation_polarity_resolution_floor_files(*, carrier_path: str | Path, smoothing_path: str | Path) -> dict[str, Any]:
    return audit_translation_polarity_resolution_floor(
        carrier_payload=_load_json(carrier_path),
        smoothing_payload=_load_json(smoothing_path),
    )
