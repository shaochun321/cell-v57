from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

CASES = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)
EXPECTED = {
    'floating_static': ('static_like', 'static_like', 'none'),
    'translation_x_pos': ('translation_like', 'translation_like', 'x'),
    'translation_x_neg': ('translation_like', 'translation_like', 'x'),
    'rotation_z_pos': ('rotation_like', 'rotation_like', 'z'),
    'rotation_z_neg': ('rotation_like', 'rotation_like', 'z'),
}
SIGNAL_FIELDS = {
    'translation_x_pos': 'mean_polarity_projection',
    'translation_x_neg': 'mean_polarity_projection',
    'rotation_z_pos': 'mean_circulation_projection',
    'rotation_z_neg': 'mean_circulation_projection',
}
EXPECTED_SIGNAL_SIGN = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
    'rotation_z_pos': 1.0,
    'rotation_z_neg': -1.0,
}

def _mean(values: list[float]) -> float:
    return float(np.mean(np.asarray(values, dtype=np.float64))) if values else 0.0

def _std(values: list[float]) -> float:
    return float(np.std(np.asarray(values, dtype=np.float64), ddof=0)) if len(values) > 1 else 0.0

def _consistency(values: list[str]) -> tuple[str, float]:
    if not values:
        return 'none', 0.0
    winner, count = Counter(values).most_common(1)[0]
    return str(winner), float(count / max(1, len(values)))

def _sign_consistency(values: list[float], *, min_abs: float = 1e-4) -> float:
    active = [float(v) for v in values if abs(float(v)) >= min_abs]
    if not active:
        return 0.0
    pos = sum(1 for v in active if v > 0.0)
    neg = sum(1 for v in active if v < 0.0)
    return float(max(pos, neg) / max(1, len(active)))

def summarize_process_summary_repeatability(report: dict[str, Any]) -> dict[str, Any]:
    seed_runs = list(report.get('seed_runs', []))
    audit: dict[str, Any] = {
        'suite': 'process_summary_repeatability',
        'metadata': dict(report.get('metadata', {})),
        'num_seed_runs': len(seed_runs),
        'seeds': [int(run.get('seed', 0)) for run in seed_runs],
        'seed_runs': [
            {
                'seed': int(run.get('seed', 0)),
                'report_path': str(run.get('report_path', '')),
                'analysis_path': str(run.get('analysis_path', '')),
            }
            for run in seed_runs
        ],
        'cases': {},
        'paired_gates': {},
    }
    case_lookup = {case: [dict(run.get('analysis', {}).get('cases', {}).get(case, {})) for run in seed_runs] for case in CASES}
    for case_name in CASES:
        rows = case_lookup[case_name]
        expected_overall, expected_active, expected_axis = EXPECTED[case_name]
        dominant_modes = [str(r.get('dominant_mode', 'none')) for r in rows]
        active_modes = [str(r.get('active_dominant_mode', 'none')) for r in rows]
        active_axes = [str(r.get('active_dominant_axis', 'none')) for r in rows]
        mode_majority, mode_consistency = _consistency(dominant_modes)
        active_majority, active_consistency = _consistency(active_modes)
        axis_majority, axis_consistency = _consistency(active_axes)
        overall_supports = [float(max(dict(r.get('overall_scores', {})).values(), default=0.0)) for r in rows]
        signal_field = SIGNAL_FIELDS.get(case_name, '')
        signals = [float(dict(r.get('active_signature', {})).get(signal_field, 0.0)) for r in rows] if signal_field else []
        expected_sign = EXPECTED_SIGNAL_SIGN.get(case_name, 0.0)
        sign_fraction = 0.0
        if signals and expected_sign != 0.0:
            sign_fraction = float(sum(1 for v in signals if np.sign(v) == np.sign(expected_sign)) / max(1, len(signals)))
        audit['cases'][case_name] = {
            'dominant_modes': dominant_modes,
            'active_modes': active_modes,
            'active_axes': active_axes,
            'mode_majority': mode_majority,
            'active_majority': active_majority,
            'axis_majority': axis_majority,
            'mode_consistency': float(mode_consistency),
            'active_consistency': float(active_consistency),
            'axis_consistency': float(axis_consistency),
            'overall_support_mean': _mean(overall_supports),
            'overall_support_std': _std(overall_supports),
            'expected_overall': expected_overall,
            'expected_active': expected_active,
            'expected_axis': expected_axis,
            'overall_expected_fraction': float(sum(1 for v in dominant_modes if v == expected_overall) / max(1, len(dominant_modes))),
            'active_expected_fraction': float(sum(1 for v in active_modes if v == expected_active) / max(1, len(active_modes))),
            'axis_expected_fraction': float(sum(1 for v in active_axes if v == expected_axis) / max(1, len(active_axes))) if expected_axis != 'none' else 1.0,
            'active_signal_field': signal_field,
            'active_signals': signals,
            'active_signal_mean': _mean(signals),
            'active_signal_std': _std(signals),
            'active_signal_sign_consistency': _sign_consistency(signals),
            'active_signal_expected_sign_fraction': sign_fraction,
        }
    for pos_case, neg_case, field, label in [
        ('translation_x_pos', 'translation_x_neg', 'mean_polarity_projection', 'translation_polarity'),
        ('rotation_z_pos', 'rotation_z_neg', 'mean_circulation_projection', 'rotation_circulation'),
    ]:
        per_seed = []
        for run in seed_runs:
            cases = dict(run.get('analysis', {}).get('cases', {}))
            pos = float(dict(cases.get(pos_case, {}).get('active_signature', {})).get(field, 0.0))
            neg = float(dict(cases.get(neg_case, {}).get('active_signature', {})).get(field, 0.0))
            per_seed.append({
                'seed': int(run.get('seed', 0)),
                'positive_signal': pos,
                'negative_signal': neg,
                'sign_flip': bool(pos * neg < 0.0),
                'separation': float(abs(pos - neg)),
            })
        audit['paired_gates'][label] = {
            'per_seed': per_seed,
            'flip_fraction': float(sum(1 for row in per_seed if row['sign_flip']) / max(1, len(per_seed))),
            'min_separation': float(min((row['separation'] for row in per_seed), default=0.0)),
            'mean_separation': _mean([float(row['separation']) for row in per_seed]),
        }
    failures: list[str] = []
    for case_name, summary in audit['cases'].items():
        if summary['overall_expected_fraction'] < 1.0:
            failures.append(f'{case_name} overall mode unstable across seeds')
        if case_name != 'floating_static' and summary['active_expected_fraction'] < 1.0:
            failures.append(f'{case_name} active mode unstable across seeds')
        if summary['expected_axis'] != 'none' and summary['axis_expected_fraction'] < 1.0:
            failures.append(f'{case_name} active axis unstable across seeds')
        if summary['active_signal_field']:
            if summary['active_signal_expected_sign_fraction'] < 1.0:
                failures.append(f'{case_name} active signal sign unstable across seeds')
            if summary['active_signal_sign_consistency'] < 1.0:
                failures.append(f'{case_name} active signal consistency below 1.0')
    for label, pair_summary in audit['paired_gates'].items():
        if pair_summary['flip_fraction'] < 1.0:
            failures.append(f'{label} sign flip unstable across seeds')
        if pair_summary['min_separation'] <= 0.01:
            failures.append(f'{label} separation too small across seeds')
    audit['contracts'] = {'passed': not failures, 'failures': failures}
    return audit
