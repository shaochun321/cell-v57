from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

FAMILIES = {
    'translation': {
        'positive_case': 'translation_x_pos',
        'negative_case': 'translation_x_neg',
        'signal_field': 'mean_polarity_projection',
        'expected_mode': 'translation_like',
        'expected_axis': 'x',
        'expected_positive_sign': 1.0,
    },
    'rotation': {
        'positive_case': 'rotation_z_pos',
        'negative_case': 'rotation_z_neg',
        'signal_field': 'mean_circulation_projection',
        'expected_mode': 'rotation_like',
        'expected_axis': 'z',
        'expected_positive_sign': 1.0,
    },
}
AXES = ('x', 'y', 'z')


def _mean(values: list[float]) -> float:
    return float(np.mean(np.asarray(values, dtype=np.float64))) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(np.asarray(values, dtype=np.float64), ddof=0)) if len(values) > 1 else 0.0


def _consistency(values: list[str]) -> tuple[str, float]:
    if not values:
        return 'none', 0.0
    winner, count = Counter(values).most_common(1)[0]
    return str(winner), float(count / max(1, len(values)))


def _active_axis_rows(case_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(case_payload.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}))


def _axis_pair_summary(*, family: str, positive_case: dict[str, Any], negative_case: dict[str, Any], axis: str, signal_field: str) -> dict[str, Any]:
    pos_axis = _active_axis_rows(positive_case).get(axis, {})
    neg_axis = _active_axis_rows(negative_case).get(axis, {})
    pos_signal = float(pos_axis.get(signal_field, 0.0))
    neg_signal = float(neg_axis.get(signal_field, 0.0))
    signal_flip = bool(pos_signal * neg_signal < 0.0)
    separation = float(abs(pos_signal - neg_signal))
    mean_translation_support = _mean([
        float(pos_axis.get('support_scores', {}).get('translation_like', 0.0)),
        float(neg_axis.get('support_scores', {}).get('translation_like', 0.0)),
    ])
    mean_rotation_support = _mean([
        float(pos_axis.get('support_scores', {}).get('rotation_like', 0.0)),
        float(neg_axis.get('support_scores', {}).get('rotation_like', 0.0)),
    ])
    mean_static_support = _mean([
        float(pos_axis.get('support_scores', {}).get('static_like', 0.0)),
        float(neg_axis.get('support_scores', {}).get('static_like', 0.0)),
    ])
    if family == 'translation':
        mode_support = mean_translation_support + 0.60 * separation
        competing_support = max(mean_rotation_support, mean_static_support)
        inferred_mode = 'translation_like' if mode_support > competing_support else 'mixed'
    else:
        mode_support = mean_rotation_support + 0.60 * separation
        competing_support = max(mean_translation_support, mean_static_support)
        inferred_mode = 'rotation_like' if mode_support > competing_support else 'mixed'
    return {
        'axis': axis,
        'positive_signal': pos_signal,
        'negative_signal': neg_signal,
        'signal_flip': signal_flip,
        'separation': separation,
        'mean_translation_support': mean_translation_support,
        'mean_rotation_support': mean_rotation_support,
        'mean_static_support': mean_static_support,
        'mode_support': float(mode_support),
        'competing_support': float(competing_support),
        'inferred_mode': inferred_mode,
    }


def summarize_process_summary_family_repeatability(report: dict[str, Any]) -> dict[str, Any]:
    seed_runs = list(report.get('seed_runs', []))
    audit: dict[str, Any] = {
        'suite': 'process_summary_family_repeatability',
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
        'families': {},
    }
    failures: list[str] = []
    for family, spec in FAMILIES.items():
        per_seed: list[dict[str, Any]] = []
        chosen_axes: list[str] = []
        chosen_modes: list[str] = []
        positive_signs: list[float] = []
        separations: list[float] = []
        for run in seed_runs:
            cases = dict(run.get('analysis', {}).get('cases', {}))
            pos_case = dict(cases.get(spec['positive_case'], {}))
            neg_case = dict(cases.get(spec['negative_case'], {}))
            axis_candidates = [
                _axis_pair_summary(
                    family=family,
                    positive_case=pos_case,
                    negative_case=neg_case,
                    axis=axis,
                    signal_field=spec['signal_field'],
                )
                for axis in AXES
            ]
            best = max(
                axis_candidates,
                key=lambda row: (
                    1 if row['signal_flip'] else 0,
                    float(row['separation']),
                    float(row['mode_support']),
                ),
            )
            chosen_axes.append(str(best['axis']))
            chosen_modes.append(str(best['inferred_mode']))
            separations.append(float(best['separation']))
            positive_signs.append(float(np.sign(best['positive_signal'])) if abs(best['positive_signal']) >= 1e-12 else 0.0)
            per_seed.append({
                'seed': int(run.get('seed', 0)),
                'best_axis': str(best['axis']),
                'best_mode': str(best['inferred_mode']),
                'best_separation': float(best['separation']),
                'positive_signal': float(best['positive_signal']),
                'negative_signal': float(best['negative_signal']),
                'signal_flip': bool(best['signal_flip']),
                'axis_candidates': axis_candidates,
            })
        axis_majority, axis_consistency = _consistency(chosen_axes)
        mode_majority, mode_consistency = _consistency(chosen_modes)
        expected_axis = str(spec['expected_axis'])
        expected_mode = str(spec['expected_mode'])
        positive_expected_fraction = float(sum(1 for s in positive_signs if s == np.sign(spec['expected_positive_sign'])) / max(1, len(positive_signs)))
        flip_fraction = float(sum(1 for row in per_seed if row['signal_flip']) / max(1, len(per_seed)))
        family_payload = {
            'expected_mode': expected_mode,
            'expected_axis': expected_axis,
            'per_seed': per_seed,
            'axis_majority': axis_majority,
            'axis_consistency': float(axis_consistency),
            'mode_majority': mode_majority,
            'mode_consistency': float(mode_consistency),
            'expected_axis_fraction': float(sum(1 for axis in chosen_axes if axis == expected_axis) / max(1, len(chosen_axes))),
            'expected_mode_fraction': float(sum(1 for mode in chosen_modes if mode == expected_mode) / max(1, len(chosen_modes))),
            'positive_signal_expected_sign_fraction': positive_expected_fraction,
            'flip_fraction': flip_fraction,
            'mean_separation': _mean(separations),
            'min_separation': float(min(separations)) if separations else 0.0,
            'separation_std': _std(separations),
        }
        audit['families'][family] = family_payload
        if family_payload['expected_axis_fraction'] < 1.0:
            failures.append(f'{family} best axis unstable across seeds')
        if family_payload['expected_mode_fraction'] < 1.0:
            failures.append(f'{family} inferred mode unstable across seeds')
        if family_payload['flip_fraction'] < 1.0:
            failures.append(f'{family} signal flip unstable across seeds')
        if family_payload['min_separation'] <= 0.02:
            failures.append(f'{family} separation too small across seeds')
    audit['contracts'] = {'passed': not failures, 'failures': failures}
    return audit
