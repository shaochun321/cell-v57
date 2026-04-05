from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import numpy as np

TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _case_row_by_seed(repeatability_report: dict[str, Any], case_name: str) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for run in repeatability_report.get('seed_runs', []):
        seed = int(run.get('seed', 0))
        case = dict(run.get('analysis', {}).get('cases', {}).get(case_name, {}))
        rows[seed] = case
    return rows


def _active_x_summary(case_row: dict[str, Any]) -> dict[str, Any]:
    return dict(case_row.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get('x', {}))


def _coerce_shell_strengths(summary: dict[str, Any]) -> dict[int, float]:
    raw = dict(summary.get('mean_shell_strengths', {}))
    return {int(k): float(v) for k, v in raw.items()}


def audit_translation_sign_source(
    repeatability_report: dict[str, Any],
    polarity_calibration: dict[str, Any],
) -> dict[str, Any]:
    seeds = [int(s) for s in repeatability_report.get('seeds', [])]
    if not seeds:
        seeds = [int(run.get('seed', 0)) for run in repeatability_report.get('seed_runs', [])]
    by_case = {case: _case_row_by_seed(repeatability_report, case) for case in TRANSLATION_CASES}
    calibration_factors = list(
        polarity_calibration.get('families', {}).get('translation', {}).get('sign_factors', [])
    )
    factor_by_seed = {seed: int(calibration_factors[i]) for i, seed in enumerate(seeds) if i < len(calibration_factors)}

    per_seed: list[dict[str, Any]] = []
    reference_seed = seeds[0] if seeds else 0
    ref_shells: dict[str, int] = {}
    for case in TRANSLATION_CASES:
        ref_x = _active_x_summary(by_case[case].get(reference_seed, {}))
        ref_shells[case] = int(ref_x.get('strongest_shell', -1))

    failures: list[str] = []
    warnings: list[str] = []
    inferred_source = 'undetermined'
    evidence = {
        'family_wide_inversion_detected': False,
        'outer_shell_shift_detected': False,
        'axis_drift_detected': False,
        'active_mode_drift_detected': False,
    }

    for seed in seeds:
        seed_row: dict[str, Any] = {
            'seed': seed,
            'family_sign_factor': int(factor_by_seed.get(seed, 1)),
            'cases': {},
        }
        raw_signs_wrong = []
        shell_shift_cases = []
        axis_drift_cases = []
        active_mode_drift_cases = []
        for case_name, expected_sign in TRANSLATION_CASES.items():
            case_row = by_case[case_name].get(seed, {})
            active_x = _active_x_summary(case_row)
            raw_signal = float(active_x.get('mean_polarity_projection', 0.0))
            strongest_shell = int(active_x.get('strongest_shell', -1))
            shell_strengths = _coerce_shell_strengths(active_x)
            max_shell = max(shell_strengths) if shell_strengths else -1
            is_outer = max_shell >= 0 and strongest_shell >= max(1, max_shell // 2 + max_shell % 2)
            active_axis = str(case_row.get('active_dominant_axis', 'none'))
            active_mode = str(case_row.get('active_dominant_mode', 'mixed'))
            sign_ok = float(np.sign(raw_signal)) == float(np.sign(expected_sign)) if abs(raw_signal) >= 1e-12 else False
            if not sign_ok:
                raw_signs_wrong.append(case_name)
            if strongest_shell != ref_shells.get(case_name, strongest_shell):
                shell_shift_cases.append(case_name)
            if active_axis != 'x':
                axis_drift_cases.append(case_name)
            if active_mode != 'translation_like':
                active_mode_drift_cases.append(case_name)
            seed_row['cases'][case_name] = {
                'raw_signal': raw_signal,
                'expected_sign': expected_sign,
                'sign_ok': bool(sign_ok),
                'strongest_shell': strongest_shell,
                'reference_shell': ref_shells.get(case_name, strongest_shell),
                'max_shell': max_shell,
                'outer_shell_dominant': bool(is_outer),
                'mean_shell_strengths': shell_strengths,
                'active_dominant_axis': active_axis,
                'active_dominant_mode': active_mode,
            }
        seed_row['family_raw_inversion'] = len(raw_signs_wrong) == len(TRANSLATION_CASES)
        seed_row['shell_shift_cases'] = shell_shift_cases
        seed_row['axis_drift_cases'] = axis_drift_cases
        seed_row['active_mode_drift_cases'] = active_mode_drift_cases
        seed_row['outer_shell_shift_cases'] = [
            c for c in shell_shift_cases if seed_row['cases'][c]['outer_shell_dominant']
        ]
        per_seed.append(seed_row)

    family_inversion = any(row['family_raw_inversion'] for row in per_seed)
    outer_shell_shift = any(len(row['outer_shell_shift_cases']) == len(TRANSLATION_CASES) for row in per_seed)
    axis_drift = any(bool(row['axis_drift_cases']) for row in per_seed)
    active_mode_drift = any(bool(row['active_mode_drift_cases']) for row in per_seed)
    evidence['family_wide_inversion_detected'] = family_inversion
    evidence['outer_shell_shift_detected'] = outer_shell_shift
    evidence['axis_drift_detected'] = axis_drift
    evidence['active_mode_drift_detected'] = active_mode_drift

    if family_inversion and outer_shell_shift:
        inferred_source = 'outer_shell_dominance_change'
        if axis_drift:
            warnings.append('axis drift appears downstream of the shell shift and likely amplifies summary instability')
    elif family_inversion and axis_drift:
        inferred_source = 'axis_summary_weighting'
    elif family_inversion and active_mode_drift:
        inferred_source = 'phase_aggregation'
    else:
        inferred_source = 'undetermined'
        failures.append('unable to isolate a dominant translation sign inversion source from existing summaries')

    payload = {
        'suite': 'process_summary_translation_sign_source_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'translation_family_sign_factors': factor_by_seed,
        'evidence': evidence,
        'inferred_primary_source': inferred_source,
        'secondary_contributors': [
            name for name, present in [
                ('axis_summary_weighting', axis_drift),
                ('phase_aggregation', active_mode_drift),
            ] if present and name != inferred_source
        ],
        'per_seed': per_seed,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }
    return payload


def audit_translation_sign_source_files(*, repeatability_report_path: str | Path, polarity_calibration_path: str | Path) -> dict[str, Any]:
    return audit_translation_sign_source(
        _load_json(repeatability_report_path),
        _load_json(polarity_calibration_path),
    )
