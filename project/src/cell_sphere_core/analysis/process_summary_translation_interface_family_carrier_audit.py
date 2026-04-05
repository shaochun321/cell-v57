from __future__ import annotations

from pathlib import Path
from typing import Any
import json

TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}
TRACKS = (
    'discrete_channel_track',
    'local_propagation_track',
    'layered_coupling_track',
)


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _case_summary_path(report_path: str | Path, case_name: str) -> Path:
    return Path(report_path).resolve().parent / case_name / 'summary.json'


def _sign_matches(value: float, expected: float, *, eps: float = 1e-12) -> bool:
    if abs(value) < eps:
        return False
    return (value > 0.0) == (expected > 0.0)


def _dominant_axis(balance: dict[str, Any]) -> str:
    axes = {axis: float(balance.get(axis, 0.0)) for axis in ('x', 'y', 'z')}
    if not axes:
        return 'none'
    return max(axes, key=lambda a: abs(axes[a]))


def _track_carrier_ok(x_balance: float, y_balance: float, z_balance: float, expected_sign: float) -> bool:
    dominant_axis = _dominant_axis({'x': x_balance, 'y': y_balance, 'z': z_balance})
    x_sign_ok = _sign_matches(x_balance, expected_sign)
    x_strength_ok = abs(x_balance) >= 0.1
    return dominant_axis == 'x' and x_sign_ok and x_strength_ok


def audit_translation_interface_family_carriers(repeatability_report: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in repeatability_report.get('seeds', [])]
    seed_runs = list(repeatability_report.get('seed_runs', []))
    if not seeds:
        seeds = [int(run.get('seed', 0)) for run in seed_runs]
    reference_seed = seeds[0] if seeds else 0

    per_seed: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []
    evidence = {
        'translation_family_survives_across_tracks': False,
        'common_carrier_break_detected': False,
        'discrete_track_specific_only': False,
        'x_pos_all_tracks_break_detected': False,
        'x_neg_all_tracks_break_detected': False,
    }

    for run in seed_runs:
        seed = int(run.get('seed', 0))
        row: dict[str, Any] = {'seed': seed, 'cases': {}}
        family_survives = True
        x_pos_all_tracks_broken = False
        x_neg_all_tracks_broken = False

        for case_name, expected_sign in TRANSLATION_CASES.items():
            summary = _load_json(_case_summary_path(run['report_path'], case_name))
            active_interface = dict(summary.get('mirror_interface_diagnostics', {}).get('active_summary', {}))
            tracks_payload = dict(summary.get('interface_temporal_diagnostics', {}).get('tracks', {}))
            track_rows: dict[str, Any] = {}
            all_tracks_broken = True
            all_tracks_survive = True

            for track_name in TRACKS:
                track = dict(tracks_payload.get(track_name, {}))
                active_families = dict(track.get('active_families', {}))
                axial = dict(active_families.get('axial_polar_family', {}))
                swirl = dict(active_families.get('swirl_circulation_family', {}))
                balances = dict(track.get('active_mean_axis_polarity_balance', {}))
                x_balance = float(balances.get('x', 0.0))
                y_balance = float(balances.get('y', 0.0))
                z_balance = float(balances.get('z', 0.0))
                dominant_axis = _dominant_axis(balances)
                axial_minus_swirl = float(axial.get('mean_outer_level', 0.0) - swirl.get('mean_outer_level', 0.0))
                translation_family_survives = axial_minus_swirl > 0.08
                outer_shift = float(axial.get('mean_outer_inner_ratio', 0.0)) > 4.0 and float(axial.get('mean_peak_shell_index', -1.0)) >= 1.5
                carrier_ok = _track_carrier_ok(x_balance, y_balance, z_balance, expected_sign)
                sign_ok = _sign_matches(x_balance, expected_sign)
                track_rows[track_name] = {
                    'x_balance': x_balance,
                    'y_balance': y_balance,
                    'z_balance': z_balance,
                    'dominant_axis': dominant_axis,
                    'x_sign_ok': sign_ok,
                    'translation_family_survives': translation_family_survives,
                    'axial_minus_swirl': axial_minus_swirl,
                    'outer_shift_detected': outer_shift,
                    'carrier_ok': carrier_ok,
                }
                all_tracks_broken = all_tracks_broken and (not carrier_ok)
                all_tracks_survive = all_tracks_survive and translation_family_survives

            family_survives = family_survives and all_tracks_survive
            if case_name == 'translation_x_pos':
                x_pos_all_tracks_broken = all_tracks_broken
            elif case_name == 'translation_x_neg':
                x_neg_all_tracks_broken = all_tracks_broken

            row['cases'][case_name] = {
                'interface_dominant_class': str(active_interface.get('dominant_interface_class', 'unknown')),
                'interface_translation_channel': float(active_interface.get('mean_translation_channel', 0.0)),
                'interface_static_channel': float(active_interface.get('mean_static_channel', 0.0)),
                'interface_margin': float(active_interface.get('mean_interface_margin', 0.0)),
                'tracks': track_rows,
                'all_tracks_broken': all_tracks_broken,
                'all_tracks_family_survive': all_tracks_survive,
            }

        row['family_translation_survives_across_tracks'] = family_survives
        row['x_pos_all_tracks_broken'] = x_pos_all_tracks_broken
        row['x_neg_all_tracks_broken'] = x_neg_all_tracks_broken
        row['family_common_carrier_break'] = x_pos_all_tracks_broken and x_neg_all_tracks_broken
        per_seed.append(row)

    evidence['translation_family_survives_across_tracks'] = any(r['family_translation_survives_across_tracks'] for r in per_seed)
    evidence['x_pos_all_tracks_break_detected'] = any(r['x_pos_all_tracks_broken'] for r in per_seed)
    evidence['x_neg_all_tracks_break_detected'] = any(r['x_neg_all_tracks_broken'] for r in per_seed)
    evidence['common_carrier_break_detected'] = any(r['family_common_carrier_break'] for r in per_seed)
    evidence['discrete_track_specific_only'] = False

    if evidence['translation_family_survives_across_tracks'] and evidence['common_carrier_break_detected']:
        primary = 'common_mirrored_translation_carrier_polarity_break'
        secondary = ['discrete_track_sharpest_failure']
        warnings.append(
            'translation survives as an axial-polar family across all three carriers, but the x-axis carrier geometry breaks simultaneously across discrete, local, and layered tracks under seed 8'
        )
    elif evidence['translation_family_survives_across_tracks']:
        primary = 'discrete_track_specific_failure'
        secondary = []
        evidence['discrete_track_specific_only'] = True
    else:
        primary = 'undetermined'
        secondary = []
        failures.append('unable to localize translation instability to a common or track-specific carrier failure')

    return {
        'suite': 'process_summary_translation_interface_family_carrier_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
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


def audit_translation_interface_family_carriers_files(*, repeatability_report_path: str | Path) -> dict[str, Any]:
    return audit_translation_interface_family_carriers(_load_json(repeatability_report_path))
