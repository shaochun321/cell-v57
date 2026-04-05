from __future__ import annotations

from typing import Any
import json
from pathlib import Path

import numpy as np

from cell_sphere_core.analysis.process_summary_family_repeatability import FAMILIES


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _mean(values: list[float]) -> float:
    return float(np.mean(np.asarray(values, dtype=np.float64))) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(np.asarray(values, dtype=np.float64), ddof=0)) if len(values) > 1 else 0.0


def _sign_fraction(values: list[float], expected_sign: float) -> float:
    if not values:
        return 0.0
    target = float(np.sign(expected_sign))
    return float(sum(1 for v in values if np.sign(v) == target) / max(1, len(values)))


def _case_rows_from_report(report: dict[str, Any], case_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in report.get('seed_runs', []):
        analysis = dict(run.get('analysis', {}))
        case = dict(analysis.get('cases', {}).get(case_name, {}))
        case['seed'] = int(run.get('seed', 0))
        rows.append(case)
    return rows


def summarize_family_guided_case_consensus(
    repeatability_report: dict[str, Any],
    family_audit: dict[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'suite': 'process_summary_family_guided_case_consensus',
        'metadata': dict(repeatability_report.get('metadata', {})),
        'num_seed_runs': len(repeatability_report.get('seed_runs', [])),
        'seeds': [int(run.get('seed', 0)) for run in repeatability_report.get('seed_runs', [])],
        'families': {},
        'cases': {},
    }
    failures: list[str] = []
    warnings: list[str] = []
    for family_name, spec in FAMILIES.items():
        fam = dict(family_audit.get('families', {}).get(family_name, {}))
        expected_mode = str(spec['expected_mode'])
        expected_axis = str(spec['expected_axis'])
        family_mode_stable = (
            fam.get('expected_axis_fraction', 0.0) == 1.0
            and fam.get('expected_mode_fraction', 0.0) == 1.0
            and fam.get('flip_fraction', 0.0) == 1.0
            and float(fam.get('min_separation', 0.0)) > 0.02
        )
        payload['families'][family_name] = {
            'expected_mode': expected_mode,
            'expected_axis': expected_axis,
            'family_mode_stable': bool(family_mode_stable),
            'axis_majority': fam.get('axis_majority', 'none'),
            'mode_majority': fam.get('mode_majority', 'mixed'),
            'expected_axis_fraction': float(fam.get('expected_axis_fraction', 0.0)),
            'expected_mode_fraction': float(fam.get('expected_mode_fraction', 0.0)),
            'flip_fraction': float(fam.get('flip_fraction', 0.0)),
            'min_separation': float(fam.get('min_separation', 0.0)),
        }
        for case_name, expected_sign in [
            (spec['positive_case'], spec['expected_positive_sign']),
            (spec['negative_case'], -float(spec['expected_positive_sign'])),
        ]:
            rows = _case_rows_from_report(repeatability_report, case_name)
            axis_rows = [
                dict(case.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get(expected_axis, {}))
                for case in rows
            ]
            field = str(spec['signal_field'])
            active_signals = [float(axis_row.get(field, 0.0)) for axis_row in axis_rows]
            expected_sign_fraction = _sign_fraction(active_signals, expected_sign)
            phase_mode_support = [float(axis_row.get('support_scores', {}).get(expected_mode, 0.0)) for axis_row in axis_rows]
            phase_static_support = [float(axis_row.get('support_scores', {}).get('static_like', 0.0)) for axis_row in axis_rows]
            active_mode_fractions = [
                1.0 if str(case.get('active_dominant_mode', 'none')) == expected_mode else 0.0
                for case in rows
            ]
            consensus = {
                'case_name': case_name,
                'family': family_name,
                'consensus_mode': expected_mode if family_mode_stable else 'mixed',
                'consensus_axis': expected_axis if family_mode_stable else 'none',
                'family_mode_stable': bool(family_mode_stable),
                'active_signal_field': field,
                'active_signals_expected_axis': active_signals,
                'active_signal_mean': _mean(active_signals),
                'active_signal_std': _std(active_signals),
                'active_signal_expected_sign_fraction': float(expected_sign_fraction),
                'mean_expected_mode_support_at_expected_axis': _mean(phase_mode_support),
                'mean_static_support_at_expected_axis': _mean(phase_static_support),
                'active_mode_expected_fraction_raw': _mean(active_mode_fractions),
                'sign_calibration_stable': bool(expected_sign_fraction == 1.0),
                'seeds': [int(case.get('seed', 0)) for case in rows],
            }
            payload['cases'][case_name] = consensus
            if not family_mode_stable:
                failures.append(f'{case_name} family-level mode/axis not stable enough for consensus')
            if expected_sign_fraction < 1.0:
                warnings.append(f'{case_name} absolute sign calibration unstable across seeds')
    payload['contracts'] = {
        'passed': not failures,
        'failures': failures,
        'warnings': warnings,
    }
    return payload


def summarize_family_guided_case_consensus_files(
    *,
    repeatability_report_path: str | Path,
    family_audit_path: str | Path,
) -> dict[str, Any]:
    return summarize_family_guided_case_consensus(
        _load_json(repeatability_report_path),
        _load_json(family_audit_path),
    )
