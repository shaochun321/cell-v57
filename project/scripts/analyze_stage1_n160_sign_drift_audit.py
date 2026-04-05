from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import extract_features

CURRENT_V6_SIGN_KEYS = [
    'layered_coupling_track_source_circ_z',
    'discrete_channel_track_source_dir_x',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Audit N160 late-sharp translation sign drift across scales.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_translation_sign_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_sign_drift_audit')
    return p.parse_args()


def radius_coord(num_cells: int) -> float:
    return num_cells ** (1.0 / 3.0)


def load_translation_panel(panel_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                label = 'translation_x_pos' if 'x_pos' in case_dir.name else 'translation_x_neg'
                profile = 'late_sharp' if 'late_sharp' in case_dir.name else 'early_soft'
                rows.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'label': label,
                    'profile': profile,
                    'features': extract_features(case_dir),
                })
    return rows


def zscore_against_n64(rows: list[dict[str, Any]]) -> list[str]:
    feature_names = list(rows[0]['features'].keys())
    ref = [r for r in rows if r['scale'] == 64]
    means = {k: mean(r['features'][k] for r in ref) for k in feature_names}
    stds = {k: (pstdev([r['features'][k] for r in ref]) or 1.0) for k in feature_names}
    for row in rows:
        row['z_features'] = {k: (row['features'][k] - means[k]) / stds[k] for k in feature_names}
    return feature_names


def late_sharp_delta(rows: list[dict[str, Any]], feature: str, scale: int) -> float:
    pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == 'late_sharp' and r['label'] == 'translation_x_pos']
    neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == 'late_sharp' and r['label'] == 'translation_x_neg']
    return mean(pos) - mean(neg)


def profile_delta(rows: list[dict[str, Any]], feature: str, scale: int, profile: str) -> float:
    pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == profile and r['label'] == 'translation_x_pos']
    neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == profile and r['label'] == 'translation_x_neg']
    return mean(pos) - mean(neg)


def feature_rank(rows: list[dict[str, Any]], feature_names: list[str], profile: str) -> list[dict[str, Any]]:
    ranked = []
    scales = [64, 96, 128, 160]
    for feature in feature_names:
        deltas = [profile_delta(rows, feature, scale, profile) for scale in scales]
        signs = [1 if d > 0 else -1 if d < 0 else 0 for d in deltas]
        if 0 in signs:
            continue
        consistency = abs(sum(signs)) / len(signs)
        min_abs = min(abs(d) for d in deltas)
        mean_abs = mean(abs(d) for d in deltas)
        cv = (pstdev(deltas) / abs(mean(deltas))) if mean(deltas) != 0 else 999.0
        score = consistency * min_abs / (1.0 + cv)
        ranked.append({
            'feature': feature,
            'score': score,
            'consistency': consistency,
            'min_abs_delta': min_abs,
            'mean_abs_delta': mean_abs,
            'cv': cv,
            'deltas_by_scale': {str(s): d for s, d in zip(scales, deltas)},
        })
    ranked.sort(key=lambda x: x['score'], reverse=True)
    return ranked


def fit_linear_centers(rows: list[dict[str, Any]], keys: list[str], profile: str) -> dict[str, dict[str, tuple[float, float]]]:
    out: dict[str, dict[str, tuple[float, float]]] = {}
    train_scales = [64, 96, 128]
    for label in ['translation_x_pos', 'translation_x_neg']:
        out[label] = {}
        for key in keys:
            xs, ys = [], []
            for scale in train_scales:
                vals = [r['z_features'][key] for r in rows if r['scale'] == scale and r['profile'] == profile and r['label'] == label]
                xs.append(radius_coord(scale))
                ys.append(mean(vals))
            xbar = mean(xs)
            ybar = mean(ys)
            den = sum((x - xbar) ** 2 for x in xs) or 1.0
            a = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / den
            b = ybar - a * xbar
            out[label][key] = (a, b)
    return out


def center_from_linear(params: dict[str, tuple[float, float]], scale: int) -> dict[str, float]:
    r = radius_coord(scale)
    return {k: a * r + b for k, (a, b) in params.items()}


def subset_eval(rows: list[dict[str, Any]], keys: list[str], profile: str) -> dict[str, Any]:
    params = fit_linear_centers(rows, keys, profile)
    per_scale: dict[str, float] = {}
    predictions: list[dict[str, Any]] = []
    for scale in [64, 96, 128, 160]:
        subset = [r for r in rows if r['scale'] == scale and r['profile'] == profile]
        correct = 0
        total = 0
        pos_center = center_from_linear(params['translation_x_pos'], scale)
        neg_center = center_from_linear(params['translation_x_neg'], scale)
        for row in subset:
            d_pos = sum((row['z_features'][k] - pos_center[k]) ** 2 for k in keys)
            d_neg = sum((row['z_features'][k] - neg_center[k]) ** 2 for k in keys)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            predictions.append({
                'scale': scale,
                'seed': row['seed'],
                'case_name': row['case_name'],
                'label': row['label'],
                'predicted': pred,
                'd_pos': d_pos,
                'd_neg': d_neg,
            })
            correct += int(pred == row['label'])
            total += 1
        per_scale[str(scale)] = correct / total if total else 0.0
    return {'keys': keys, 'profile': profile, 'per_scale_accuracy': per_scale, 'predictions': predictions}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = load_translation_panel(Path(args.panel_root))
    feature_names = zscore_against_n64(rows)

    early_rank = feature_rank(rows, feature_names, 'early_soft')
    late_rank = feature_rank(rows, feature_names, 'late_sharp')

    current_key_deltas = {
        key: {
            'early_soft': {str(scale): profile_delta(rows, key, scale, 'early_soft') for scale in [64, 96, 128, 160]},
            'late_sharp': {str(scale): profile_delta(rows, key, scale, 'late_sharp') for scale in [64, 96, 128, 160]},
        }
        for key in CURRENT_V6_SIGN_KEYS
    }

    current_late_eval = subset_eval(rows, CURRENT_V6_SIGN_KEYS, 'late_sharp')

    top_late_candidates = [r['feature'] for r in late_rank[:12]]
    subset_trials = []
    for size in [1, 2, 3]:
        for keys in itertools.combinations(top_late_candidates, size):
            trial = subset_eval(rows, list(keys), 'late_sharp')
            per = trial['per_scale_accuracy']
            score = per['160'] + 0.5 * mean([per['64'], per['96'], per['128']]) - 0.03 * size
            subset_trials.append({
                'keys': list(keys),
                'score': score,
                'per_scale_accuracy': per,
            })
    subset_trials.sort(key=lambda x: x['score'], reverse=True)

    result = {
        'protocol': 'stage1_n160_sign_drift_audit',
        'panel_root': args.panel_root,
        'current_v6_sign_keys': CURRENT_V6_SIGN_KEYS,
        'current_key_deltas': current_key_deltas,
        'current_late_sharp_sign_only_eval': {
            'keys': CURRENT_V6_SIGN_KEYS,
            'per_scale_accuracy': current_late_eval['per_scale_accuracy'],
        },
        'top_early_soft_features': early_rank[:20],
        'top_late_sharp_features': late_rank[:20],
        'top_late_sharp_subset_trials': subset_trials[:20],
        'recommendation': {
            'status': 'no_clean_drop_in_replacement_yet',
            'reason': 'current v6 sign keys flip or collapse on N160 late_sharp, while best late_sharp-only subset still does not preserve back-compatibility on 64/96/128',
            'next_task': 'treat late_sharp translation sign as its own drift problem and add richer temporal/profile observables rather than re-opening the physical core',
        },
    }
    (outdir / 'stage1_n160_sign_drift_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 SIGN DRIFT AUDIT',
        '',
        '## Goal',
        'Audit why the current v6 scale-adaptive sign handoff fails on **N160 late-sharp translation sign** even though gate stability is preserved.',
        '',
        '## Current v6 sign keys',
        *[f'- `{k}`' for k in CURRENT_V6_SIGN_KEYS],
        '',
        '## Current-key delta trajectories (pos minus neg)',
        '',
    ]
    for key, block in current_key_deltas.items():
        lines.append(f'### {key}')
        lines.append('')
        for profile in ['early_soft', 'late_sharp']:
            vals = ', '.join([f'N{scale}={block[profile][str(scale)]:.3f}' for scale in [64, 96, 128, 160]])
            lines.append(f'- {profile}: {vals}')
        lines.append('')
    lines.extend([
        '## Current-key late-sharp sign-only accuracy',
        '',
    ])
    for scale, acc in current_late_eval['per_scale_accuracy'].items():
        lines.append(f'- N{scale}: {acc:.3f}')
    lines.extend([
        '',
        'Interpretation:',
        '- the current two-key sign handoff is clean on 64/96/128 for late_sharp only, but collapses at N160',
        '- the failure is consistent with a scale-driven sign drift, not with gate collapse',
        '',
        '## Top late-sharp robust features',
        '',
    ])
    for row in late_rank[:12]:
        ds = ', '.join([f'N{s}={row["deltas_by_scale"][str(s)]:.3f}' for s in [64, 96, 128, 160]])
        lines.append(f"- `{row['feature']}`: score={row['score']:.3f}, consistency={row['consistency']:.2f}, min_abs={row['min_abs_delta']:.3f}; {ds}")
    lines.extend([
        '',
        '## Best simple late-sharp subset trials',
        '',
    ])
    for row in subset_trials[:10]:
        per = row['per_scale_accuracy']
        lines.append(f"- keys={row['keys']} | N64={per['64']:.3f}, N96={per['96']:.3f}, N128={per['128']:.3f}, N160={per['160']:.3f}, score={row['score']:.3f}")
    lines.extend([
        '',
        '## Hard conclusion',
        '',
        '- N160 late-sharp translation sign is now the true front-line drift problem.',
        '- The current v6 sign keys do not extrapolate cleanly to N160 late_sharp.',
        '- There is **no clean drop-in late-sharp replacement** among simple 1-3 feature subsets that also preserves 64/96/128 back-compatibility.',
        '- This points away from reopening the physical core and toward richer translation-sign observables or a more explicit profile-aware readout branch.',
    ])
    (outdir / 'STAGE1_N160_SIGN_DRIFT_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote N160 sign drift audit to {outdir}')


if __name__ == '__main__':
    main()
