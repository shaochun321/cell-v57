from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import numpy as np

from cell_sphere_core.analysis.process_summary_family_repeatability import FAMILIES


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _case_rows_from_report(report: dict[str, Any], case_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in report.get('seed_runs', []):
        analysis = dict(run.get('analysis', {}))
        case = dict(analysis.get('cases', {}).get(case_name, {}))
        case['seed'] = int(run.get('seed', 0))
        rows.append(case)
    return rows


def _axis_signal(case_row: dict[str, Any], axis: str, field: str) -> float:
    return float(
        dict(case_row.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get(axis, {})).get(field, 0.0)
    )


def summarize_family_polarity_calibration(
    repeatability_report: dict[str, Any],
    family_consensus: dict[str, Any],
) -> dict[str, Any]:
    seed_runs = list(repeatability_report.get('seed_runs', []))
    seeds = [int(run.get('seed', 0)) for run in seed_runs]
    payload: dict[str, Any] = {
        'suite': 'process_summary_family_polarity_calibration',
        'metadata': dict(repeatability_report.get('metadata', {})),
        'num_seed_runs': len(seed_runs),
        'seeds': seeds,
        'families': {},
        'cases': {},
    }
    failures: list[str] = []
    warnings: list[str] = []

    for family_name, spec in FAMILIES.items():
        expected_axis = str(spec['expected_axis'])
        field = str(spec['signal_field'])
        pos_case = str(spec['positive_case'])
        neg_case = str(spec['negative_case'])
        pos_rows = _case_rows_from_report(repeatability_report, pos_case)
        neg_rows = _case_rows_from_report(repeatability_report, neg_case)
        by_seed_pos = {int(r.get('seed', 0)): r for r in pos_rows}
        by_seed_neg = {int(r.get('seed', 0)): r for r in neg_rows}

        family_rows: list[dict[str, Any]] = []
        raw_ok = 0
        calibrated_ok = 0
        sign_factors: list[int] = []
        for seed in seeds:
            pos_signal = _axis_signal(by_seed_pos[seed], expected_axis, field)
            neg_signal = _axis_signal(by_seed_neg[seed], expected_axis, field)
            pair_gap = float(pos_signal - neg_signal)
            orientation_sign = float(np.sign(pair_gap)) if abs(pair_gap) >= 1e-8 else 0.0
            expected_orientation = float(np.sign(2.0 * spec['expected_positive_sign']))
            sign_factor = -1 if orientation_sign != 0.0 and orientation_sign != expected_orientation else 1
            sign_factors.append(sign_factor)
            pos_cal = float(sign_factor * pos_signal)
            neg_cal = float(sign_factor * neg_signal)
            pos_raw_ok = int(np.sign(pos_signal) == np.sign(spec['expected_positive_sign']))
            neg_raw_ok = int(np.sign(neg_signal) == np.sign(-float(spec['expected_positive_sign'])))
            pos_cal_ok = int(np.sign(pos_cal) == np.sign(spec['expected_positive_sign']))
            neg_cal_ok = int(np.sign(neg_cal) == np.sign(-float(spec['expected_positive_sign'])))
            raw_ok += pos_raw_ok + neg_raw_ok
            calibrated_ok += pos_cal_ok + neg_cal_ok
            family_rows.append({
                'seed': seed,
                'expected_axis': expected_axis,
                'field': field,
                'positive_raw_signal': pos_signal,
                'negative_raw_signal': neg_signal,
                'pair_gap_raw': pair_gap,
                'orientation_sign_raw': orientation_sign,
                'sign_factor': sign_factor,
                'positive_calibrated_signal': pos_cal,
                'negative_calibrated_signal': neg_cal,
                'pair_gap_calibrated': float(pos_cal - neg_cal),
                'raw_signs_ok': bool(pos_raw_ok and neg_raw_ok),
                'calibrated_signs_ok': bool(pos_cal_ok and neg_cal_ok),
            })
        raw_sign_fraction = float(raw_ok / max(1, 2 * len(seeds)))
        calibrated_sign_fraction = float(calibrated_ok / max(1, 2 * len(seeds)))
        family_mode_stable = bool(family_consensus.get('families', {}).get(family_name, {}).get('family_mode_stable', False))
        payload['families'][family_name] = {
            'expected_axis': expected_axis,
            'signal_field': field,
            'family_mode_stable': family_mode_stable,
            'sign_factors': sign_factors,
            'orientation_flip_detected_fraction': float(sum(1 for f in sign_factors if f == -1) / max(1, len(sign_factors))),
            'raw_sign_fraction': raw_sign_fraction,
            'calibrated_sign_fraction': calibrated_sign_fraction,
            'seed_rows': family_rows,
        }
        if not family_mode_stable:
            failures.append(f'{family_name} family mode not stable enough for calibration')
        if calibrated_sign_fraction < 1.0:
            failures.append(f'{family_name} calibrated sign fraction below 1.0')
        elif raw_sign_fraction < 1.0:
            warnings.append(f'{family_name} raw absolute sign unstable but family-calibrated sign stable')

        for row in family_rows:
            for case_name, raw_key, cal_key, expected_sign in [
                (pos_case, 'positive_raw_signal', 'positive_calibrated_signal', spec['expected_positive_sign']),
                (neg_case, 'negative_raw_signal', 'negative_calibrated_signal', -float(spec['expected_positive_sign'])),
            ]:
                case = payload['cases'].setdefault(case_name, {
                    'case_name': case_name,
                    'family': family_name,
                    'expected_axis': expected_axis,
                    'signal_field': field,
                    'raw_signals': [],
                    'calibrated_signals': [],
                    'sign_factors': [],
                    '_expected_sign': float(expected_sign),
                    'consensus_mode': family_consensus.get('cases', {}).get(case_name, {}).get('consensus_mode', 'mixed'),
                    'consensus_axis': family_consensus.get('cases', {}).get(case_name, {}).get('consensus_axis', 'none'),
                })
                case['raw_signals'].append(float(row[raw_key]))
                case['calibrated_signals'].append(float(row[cal_key]))
                case['sign_factors'].append(int(row['sign_factor']))

    for case in payload['cases'].values():
        expected_sign = float(case.pop('_expected_sign'))
        raw_vals = list(case['raw_signals'])
        cal_vals = list(case['calibrated_signals'])
        case['raw_signal_mean'] = float(np.mean(np.asarray(raw_vals, dtype=np.float64))) if raw_vals else 0.0
        case['calibrated_signal_mean'] = float(np.mean(np.asarray(cal_vals, dtype=np.float64))) if cal_vals else 0.0
        case['raw_expected_sign_fraction'] = float(sum(1 for v in raw_vals if np.sign(v) == np.sign(expected_sign)) / max(1, len(raw_vals)))
        case['calibrated_expected_sign_fraction'] = float(sum(1 for v in cal_vals if np.sign(v) == np.sign(expected_sign)) / max(1, len(cal_vals)))
        case['sign_calibration_fixed'] = bool(case['raw_expected_sign_fraction'] < 1.0 and case['calibrated_expected_sign_fraction'] == 1.0)

    payload['contracts'] = {
        'passed': not failures,
        'failures': failures,
        'warnings': warnings,
    }
    return payload


def summarize_family_polarity_calibration_files(*, repeatability_report_path: str | Path, family_consensus_path: str | Path) -> dict[str, Any]:
    return summarize_family_polarity_calibration(
        _load_json(repeatability_report_path),
        _load_json(family_consensus_path),
    )
