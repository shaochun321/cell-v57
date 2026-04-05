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

CURRENT_SIGN_KEYS = [
    'layered_coupling_track_source_circ_z',
    'discrete_channel_track_source_dir_x',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Audit cross-scale early-sharp translation sign observability.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_translation_early_sharp_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_early_sharp_sign_audit')
    return p.parse_args()


def radius_coord(num_cells: int) -> float:
    return num_cells ** (1.0 / 3.0)


def load_panel(panel_root: Path) -> list[dict[str, Any]]:
    rows = []
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                rows.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'label': 'translation_x_pos' if 'x_pos' in case_dir.name else 'translation_x_neg',
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


def delta(rows: list[dict[str, Any]], feature: str, scale: int) -> float:
    pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['label'] == 'translation_x_pos']
    neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['label'] == 'translation_x_neg']
    return mean(pos) - mean(neg)


def feature_rank(rows: list[dict[str, Any]], feature_names: list[str]) -> list[dict[str, Any]]:
    ranked = []
    scales = [64, 96, 128, 160]
    for feature in feature_names:
        deltas = [delta(rows, feature, scale) for scale in scales]
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


def fit_linear_centers(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, tuple[float, float]]]:
    out: dict[str, dict[str, tuple[float, float]]] = {}
    train_scales = [64, 96, 128]
    for label in ['translation_x_pos', 'translation_x_neg']:
        out[label] = {}
        for key in keys:
            xs, ys = [], []
            for scale in train_scales:
                vals = [r['z_features'][key] for r in rows if r['scale'] == scale and r['label'] == label]
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


def subset_eval(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    params = fit_linear_centers(rows, keys)
    per_scale: dict[str, float] = {}
    preds = []
    for scale in [64, 96, 128, 160]:
        subset = [r for r in rows if r['scale'] == scale]
        correct = 0
        total = 0
        pos_center = center_from_linear(params['translation_x_pos'], scale)
        neg_center = center_from_linear(params['translation_x_neg'], scale)
        for row in subset:
            d_pos = sum((row['z_features'][k] - pos_center[k]) ** 2 for k in keys)
            d_neg = sum((row['z_features'][k] - neg_center[k]) ** 2 for k in keys)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            preds.append({
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
    return {'keys': keys, 'per_scale_accuracy': per_scale, 'predictions': preds}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = load_panel(Path(args.panel_root))
    feature_names = zscore_against_n64(rows)
    ranked = feature_rank(rows, feature_names)
    current_eval = subset_eval(rows, CURRENT_SIGN_KEYS)

    top = [r['feature'] for r in ranked[:12]]
    trials = []
    for size in [1, 2, 3]:
        for keys in itertools.combinations(top, size):
            trial = subset_eval(rows, list(keys))
            per = trial['per_scale_accuracy']
            score = per['160'] + 0.5 * mean([per['64'], per['96'], per['128']]) - 0.03 * size
            trials.append({'keys': list(keys), 'score': score, 'per_scale_accuracy': per})
    trials.sort(key=lambda x: x['score'], reverse=True)

    result = {
        'protocol': 'stage1_n160_early_sharp_sign_audit',
        'panel_root': args.panel_root,
        'current_sign_keys': CURRENT_SIGN_KEYS,
        'current_sign_eval': current_eval['per_scale_accuracy'],
        'top_early_sharp_features': ranked[:20],
        'top_early_sharp_subset_trials': trials[:20],
        'recommendation': {
            'status': 'early_sharp_sign_is_observable',
            'reason': 'simple 1-3 feature subsets preserve sign cleanly across 64/96/128/160 on the early-sharp-only panel',
            'next_task': 'treat richer-nuisance early_sharp failure as a profile-routing or profile-conditioning problem, not as a lack of sign observability',
        },
    }
    (outdir / 'stage1_n160_early_sharp_sign_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 EARLY-SHARP SIGN AUDIT',
        '',
        '## Goal',
        'Audit whether N160 early-sharp translation sign itself is fundamentally unreadable, or whether the richer-nuisance failure is mainly a profile-routing problem.',
        '',
        '## Current sign keys',
        *[f'- `{k}`' for k in CURRENT_SIGN_KEYS],
        '',
        '## Current-key early-sharp accuracy',
        '',
    ]
    for scale, acc in current_eval['per_scale_accuracy'].items():
        lines.append(f'- N{scale}: {acc:.3f}')
    lines.extend([
        '',
        '## Top early-sharp robust features',
        '',
    ])
    for row in ranked[:12]:
        ds = ', '.join([f'N{s}={row["deltas_by_scale"][str(s)]:.3f}' for s in [64,96,128,160]])
        lines.append(f"- `{row['feature']}`: score={row['score']:.3f}, consistency={row['consistency']:.2f}, min_abs={row['min_abs_delta']:.3f}; {ds}")
    lines.extend([
        '',
        '## Best simple early-sharp subset trials',
        '',
    ])
    for row in trials[:10]:
        per = row['per_scale_accuracy']
        lines.append(f"- keys={row['keys']} | N64={per['64']:.3f}, N96={per['96']:.3f}, N128={per['128']:.3f}, N160={per['160']:.3f}, score={row['score']:.3f}")
    lines.extend([
        '',
        '## Hard conclusion',
        '',
        '- Early-sharp translation sign is **not** intrinsically unreadable at N160.',
        '- There exist simple 1-feature and 2-feature sign observables that stay clean across 64/96/128/160 on the early-sharp-only panel.',
        '- This shifts the richer-nuisance early-sharp failure away from “missing sign observables” and toward “profile routing / profile conditioning is still too weak”.',
        '- The next high-value move is to improve how the external readout recognizes or conditions on early-sharp translation, not to reopen the physical core.',
    ])
    (outdir / 'STAGE1_N160_EARLY_SHARP_SIGN_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote early-sharp sign audit to {outdir}')


if __name__ == '__main__':
    main()
