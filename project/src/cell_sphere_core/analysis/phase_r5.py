from __future__ import annotations

from typing import Any
import numpy as np

from .phase_r2 import _rotation_metrics, _translation_guard_metrics


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _rating(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "moderate"
    return "weak"


def summarize_phase_r5_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(protocol_report.get('metadata', {}))
    rows_in = list(protocol_report.get('rotation_scan', []))
    translation_guard = dict(protocol_report.get('translation_guard', {}))
    agg_rows: list[dict[str, Any]] = []
    for case in rows_in:
        repeat_metrics = []
        for rep in case.get('repeats', []):
            metrics = _rotation_metrics(rep.get('rotation_pos', {}), rep.get('rotation_neg', {}))
            repeat_metrics.append({
                'repeat_id': rep.get('repeat_id', 'r?'),
                'rng_seed': int(rep.get('rng_seed', 0)),
                **metrics,
            })
        scores = [float(r['rotation_score']) for r in repeat_metrics]
        mean_score = float(np.mean(scores)) if scores else 0.0
        std_score = float(np.std(scores)) if scores else 0.0
        floor_score = float(min(scores)) if scores else 0.0
        ceil_score = float(max(scores)) if scores else 0.0
        sign_consistency = float(np.mean([float(r['sign_separation']) for r in repeat_metrics])) if repeat_metrics else 0.0
        swirl_dom = float(np.mean([float(r['swirl_dominance']) for r in repeat_metrics])) if repeat_metrics else 0.0
        repeatability_score = _clip01(
            0.45 * mean_score +
            0.25 * floor_score +
            0.15 * (1.0 - min(std_score / 0.03, 1.0)) +
            0.15 * sign_consistency
        )
        agg_rows.append({
            'case_id': case.get('case_id', 'unknown'),
            'rotation_alpha': float(case.get('rotation_alpha', 0.0)),
            'swirl_gain': float(case.get('swirl_gain', 1.0)),
            'circulation_gain': float(case.get('circulation_gain', 0.0)),
            'axial_base': float(case.get('axial_base', 0.0)),
            'transfer_base': float(case.get('transfer_base', 0.0)),
            'circulation_feed': float(case.get('circulation_feed', 0.0)),
            'repeat_count': len(repeat_metrics),
            'rotation_score_mean': mean_score,
            'rotation_score_std': std_score,
            'rotation_score_floor': floor_score,
            'rotation_score_ceil': ceil_score,
            'sign_consistency': sign_consistency,
            'swirl_dominance_mean': swirl_dom,
            'repeatability_score': repeatability_score,
            'repeats': repeat_metrics,
        })
    agg_rows = sorted(agg_rows, key=lambda r: (r['repeatability_score'], r['rotation_score_mean']), reverse=True)
    best = agg_rows[0] if agg_rows else {'case_id': 'none', 'repeatability_score': 0.0, 'rotation_score_mean': 0.0}
    worst = agg_rows[-1] if agg_rows else {'case_id': 'none', 'repeatability_score': 0.0, 'rotation_score_mean': 0.0}

    alphas = sorted({float(r['rotation_alpha']) for r in agg_rows})
    gains = sorted({float(r['swirl_gain']) for r in agg_rows})
    alpha_step = float(np.median(np.diff(alphas))) if len(alphas) >= 2 else 20.0
    gain_step = float(np.median(np.diff(gains))) if len(gains) >= 2 else 0.05
    a_best = float(best.get('rotation_alpha', 0.0))
    g_best = float(best.get('swirl_gain', 0.0))
    neighbors = [
        r for r in agg_rows
        if abs(float(r['rotation_alpha']) - a_best) <= alpha_step + 1e-9
        and abs(float(r['swirl_gain']) - g_best) <= gain_step + 1e-9
    ]
    nb_scores = [float(r['repeatability_score']) for r in neighbors]
    plateau = {
        'neighbor_count': int(len(neighbors)),
        'mean_repeatability': float(np.mean(nb_scores)) if nb_scores else 0.0,
        'floor_repeatability': float(min(nb_scores)) if nb_scores else 0.0,
        'std_repeatability': float(np.std(nb_scores)) if nb_scores else 0.0,
        'plateau_fraction': float(np.mean([1.0 if s >= float(best.get('repeatability_score', 0.0)) - 0.02 else 0.0 for s in nb_scores])) if nb_scores else 0.0,
    }
    plateau['plateau_score'] = _clip01(
        0.45 * plateau['mean_repeatability'] +
        0.25 * plateau['floor_repeatability'] +
        0.15 * (1.0 - min(plateau['std_repeatability'] / 0.03, 1.0)) +
        0.15 * plateau['plateau_fraction']
    )

    guard = _translation_guard_metrics(translation_guard) if translation_guard else {
        'axial_margin': 0.0,
        'x_balance': 0.0,
        'translation_guard_score': 0.0,
    }

    overall = {
        'num_scan_points': int(len(agg_rows)),
        'repeat_count': int(len(agg_rows[0]['repeats'])) if agg_rows else 0,
        'repeatability_mean': float(np.mean([float(r['repeatability_score']) for r in agg_rows])) if agg_rows else 0.0,
        'repeatability_std': float(np.std([float(r['repeatability_score']) for r in agg_rows])) if agg_rows else 0.0,
        'strong_region_fraction': float(np.mean([1.0 if float(r['repeatability_score']) >= 0.8 else 0.0 for r in agg_rows])) if agg_rows else 0.0,
    }

    recommendations: list[str] = []
    if float(best.get('repeatability_score', 0.0)) < 0.85:
        recommendations.append('Best narrow-band config is still not strongly repeatable; keep tuning rotation forcing before widening the study.')
    if plateau['plateau_score'] < 0.82:
        recommendations.append('Best point does not yet sit on a broad repeatable plateau; treat it as fragile.')
    if float(guard.get('translation_guard_score', 0.0)) < 0.90:
        recommendations.append('Translation guard degraded while optimizing rotation repeatability; do not accept this region yet.')
    if not recommendations:
        recommendations.append('A compact repeatable rotation patch is emerging; confirm it with one more nearby repeat set before freezing.')

    return {
        'phase': 'Phase R.5',
        'principle': 'Phase R.5 performs a denser narrow scan with repeated runs to determine whether the candidate rotation patch is actually repeatable, not just locally good once.',
        'metadata': metadata,
        'translation_guard': guard,
        'scan_rows': agg_rows,
        'best_config': best,
        'worst_config': worst,
        'local_repeatability_plateau': plateau,
        'overall': overall,
        'ratings': {
            'best_repeatability': _rating(float(best.get('repeatability_score', 0.0))),
            'translation_guard': _rating(float(guard.get('translation_guard_score', 0.0))),
            'plateau': _rating(float(plateau.get('plateau_score', 0.0))),
        },
        'recommendations': recommendations,
    }
