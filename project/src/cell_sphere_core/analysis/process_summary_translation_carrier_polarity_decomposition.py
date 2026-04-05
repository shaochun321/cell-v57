from __future__ import annotations

from pathlib import Path
from typing import Any
import json

TRACKS = (
    'discrete_channel_track',
    'local_propagation_track',
    'layered_coupling_track',
)
TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _dominant_axis(x: float, y: float, z: float) -> str:
    vals = {'x': x, 'y': y, 'z': z}
    return max(vals, key=lambda k: abs(vals[k]))


def _sign_matches(value: float, expected: float, *, eps: float = 1e-12) -> bool:
    if abs(value) < eps:
        return False
    return (value > 0.0) == (expected > 0.0)


def _classify_track_failure(x_balance: float, y_balance: float, z_balance: float, expected_sign: float) -> str:
    dominant_axis = _dominant_axis(x_balance, y_balance, z_balance)
    x_sign_ok = _sign_matches(x_balance, expected_sign)
    x_abs = abs(x_balance)
    yz_competition = max(abs(y_balance), abs(z_balance))
    x_strength_weak = x_abs < 0.1
    axis_not_x = dominant_axis != 'x'
    if axis_not_x and x_strength_weak:
        return 'x_axis_competition_override'
    if axis_not_x:
        return 'axis_competition_override'
    if (not x_sign_ok) and x_abs >= 0.1:
        return 'polarity_projection_inversion'
    if (not x_sign_ok) and x_abs < 0.1:
        return 'weak_polarity_projection'
    if x_strength_weak and yz_competition >= x_abs:
        return 'weak_x_projection'
    return 'carrier_ok'


def decompose_translation_carrier_polarity(audit_payload: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in audit_payload.get('seeds', [])]
    reference_seed = int(audit_payload.get('reference_seed', seeds[0] if seeds else 0))
    per_seed: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    classification_counts: dict[str, int] = {}

    for row in audit_payload.get('per_seed', []):
        seed = int(row['seed'])
        out_row: dict[str, Any] = {'seed': seed, 'cases': {}}
        for case_name, expected_sign in TRANSLATION_CASES.items():
            case = dict(row['cases'][case_name])
            track_rows: dict[str, Any] = {}
            dominant_failure = 'carrier_ok'
            dominant_priority = -1
            priorities = {
                'x_axis_competition_override': 4,
                'axis_competition_override': 3,
                'polarity_projection_inversion': 2,
                'weak_polarity_projection': 1,
                'weak_x_projection': 0,
                'carrier_ok': -1,
            }
            carrier_ok_count = 0
            for track_name in TRACKS:
                track = dict(case['tracks'][track_name])
                x_balance = float(track['x_balance'])
                y_balance = float(track['y_balance'])
                z_balance = float(track['z_balance'])
                classification = _classify_track_failure(x_balance, y_balance, z_balance, expected_sign)
                classification_counts[classification] = classification_counts.get(classification, 0) + 1
                if classification == 'carrier_ok':
                    carrier_ok_count += 1
                pr = priorities.get(classification, -1)
                if pr > dominant_priority:
                    dominant_priority = pr
                    dominant_failure = classification
                track_rows[track_name] = {
                    **track,
                    'failure_classification': classification,
                }
            out_row['cases'][case_name] = {
                'interface_dominant_class': case.get('interface_dominant_class', 'unknown'),
                'dominant_failure_mode': dominant_failure,
                'carrier_ok_count': carrier_ok_count,
                'tracks': track_rows,
            }
        per_seed.append(out_row)

    seed_map = {int(r['seed']): r for r in per_seed}
    seed8 = seed_map.get(8)
    primary = 'undetermined'
    secondary: list[str] = []
    evidence = {
        'x_pos_axis_competition_detected': False,
        'x_neg_polarity_inversion_detected': False,
        'asymmetric_failure_modes_detected': False,
    }
    if seed8:
        pos_mode = seed8['cases']['translation_x_pos']['dominant_failure_mode']
        neg_mode = seed8['cases']['translation_x_neg']['dominant_failure_mode']
        evidence['x_pos_axis_competition_detected'] = pos_mode in {'x_axis_competition_override', 'axis_competition_override'}
        evidence['x_neg_polarity_inversion_detected'] = neg_mode in {'polarity_projection_inversion', 'weak_polarity_projection'}
        evidence['asymmetric_failure_modes_detected'] = pos_mode != neg_mode
        if evidence['x_pos_axis_competition_detected'] and evidence['x_neg_polarity_inversion_detected']:
            primary = 'asymmetric_translation_carrier_failure_modes'
            secondary = ['x_vs_y_axis_competition', 'polarity_projection_inversion']
            warnings.append(
                'translation_x_pos fails mainly by losing x-axis dominance under seed 8, while translation_x_neg keeps x dominance but flips polarity; translation carrier instability decomposes into asymmetric failure modes rather than one uniform break'
            )
        elif evidence['x_pos_axis_competition_detected']:
            primary = 'x_vs_y_axis_competition'
        elif evidence['x_neg_polarity_inversion_detected']:
            primary = 'polarity_projection_inversion'
        else:
            failures.append('unable to decompose translation carrier instability into axis-competition or polarity-inversion modes')
    else:
        failures.append('missing seed 8 row required for decomposition audit')

    return {
        'suite': 'process_summary_translation_carrier_polarity_decomposition',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'classification_counts': classification_counts,
        'evidence': evidence,
        'inferred_primary_source': primary,
        'secondary_contributors': secondary,
        'per_seed': per_seed,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }


def decompose_translation_carrier_polarity_files(*, carrier_audit_path: str | Path) -> dict[str, Any]:
    return decompose_translation_carrier_polarity(_load_json(carrier_audit_path))
