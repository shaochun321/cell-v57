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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Audit translation-only richer profile routing/sign across scales.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_translation_richer_profile_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_translation_richer_profile_scale_audit')
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
                name = case_dir.name
                if 'early_sharp' in name:
                    profile = 'early_sharp'
                elif 'mid_balanced' in name:
                    profile = 'mid_balanced'
                else:
                    profile = 'late_soft'
                rows.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': name,
                    'label': 'translation_x_pos' if 'x_pos' in name else 'translation_x_neg',
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


def class_delta(rows: list[dict[str, Any]], feature: str, scale: int, klass: str) -> float:
    if klass == 'early_vs_non':
        pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == 'early_sharp']
        neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] != 'early_sharp']
    elif klass == 'nonearly_sign':
        pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] != 'early_sharp' and r['label'] == 'translation_x_pos']
        neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] != 'early_sharp' and r['label'] == 'translation_x_neg']
    elif klass == 'early_sign':
        pos = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == 'early_sharp' and r['label'] == 'translation_x_pos']
        neg = [r['z_features'][feature] for r in rows if r['scale'] == scale and r['profile'] == 'early_sharp' and r['label'] == 'translation_x_neg']
    else:
        raise ValueError(klass)
    return mean(pos) - mean(neg)


def feature_rank(rows: list[dict[str, Any]], feature_names: list[str], klass: str) -> list[dict[str, Any]]:
    ranked = []
    scales = [64, 96, 128, 160]
    for feature in feature_names:
        try:
            deltas = [class_delta(rows, feature, scale, klass) for scale in scales]
        except StatisticsError:
            continue
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


def fit_linear_centers(rows: list[dict[str, Any]], keys: list[str], label_selector) -> dict[str, tuple[float, float]]:
    out = {}
    train_scales = [64, 96, 128]
    for key in keys:
        xs, ys = [], []
        for scale in train_scales:
            vals = [r['z_features'][key] for r in rows if r['scale'] == scale and label_selector(r)]
            xs.append(radius_coord(scale))
            ys.append(mean(vals))
        xbar = mean(xs)
        ybar = mean(ys)
        den = sum((x - xbar) ** 2 for x in xs) or 1.0
        a = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / den
        b = ybar - a * xbar
        out[key] = (a, b)
    return out


def center_from_linear(params: dict[str, tuple[float, float]], scale: int) -> dict[str, float]:
    r = radius_coord(scale)
    return {k: a * r + b for k, (a, b) in params.items()}


def subset_eval_binary(rows: list[dict[str, Any]], keys: list[str], label_selector, positive_name: str) -> dict[str, Any]:
    pos_params = fit_linear_centers(rows, keys, label_selector)
    neg_params = fit_linear_centers(rows, keys, lambda r: not label_selector(r))
    per_scale = {}
    preds = []
    for scale in [64, 96, 128, 160]:
        subset = [r for r in rows if r['scale'] == scale]
        correct = total = 0
        pos_center = center_from_linear(pos_params, scale)
        neg_center = center_from_linear(neg_params, scale)
        for row in subset:
            d_pos = sum((row['z_features'][k] - pos_center[k]) ** 2 for k in keys)
            d_neg = sum((row['z_features'][k] - neg_center[k]) ** 2 for k in keys)
            pred = positive_name if d_pos < d_neg else f'not_{positive_name}'
            truth = positive_name if label_selector(row) else f'not_{positive_name}'
            preds.append({'scale': scale, 'seed': row['seed'], 'case_name': row['case_name'], 'truth': truth, 'predicted': pred, 'd_pos': d_pos, 'd_neg': d_neg})
            correct += int(pred == truth)
            total += 1
        per_scale[str(scale)] = correct / total if total else 0.0
    return {'keys': keys, 'per_scale_accuracy': per_scale, 'predictions': preds}


def subset_eval_sign(rows: list[dict[str, Any]], keys: list[str], profile_filter) -> dict[str, Any]:
    frows = [r for r in rows if profile_filter(r)]
    pos_params = fit_linear_centers(frows, keys, lambda r: r['label'] == 'translation_x_pos')
    neg_params = fit_linear_centers(frows, keys, lambda r: r['label'] == 'translation_x_neg')
    per_scale = {}
    preds = []
    for scale in [64, 96, 128, 160]:
        subset = [r for r in frows if r['scale'] == scale]
        correct = total = 0
        pos_center = center_from_linear(pos_params, scale)
        neg_center = center_from_linear(neg_params, scale)
        for row in subset:
            d_pos = sum((row['z_features'][k] - pos_center[k]) ** 2 for k in keys)
            d_neg = sum((row['z_features'][k] - neg_center[k]) ** 2 for k in keys)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            preds.append({'scale': scale, 'seed': row['seed'], 'case_name': row['case_name'], 'label': row['label'], 'predicted': pred, 'd_pos': d_pos, 'd_neg': d_neg})
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
    early_rank = feature_rank(rows, feature_names, 'early_vs_non')
    early_sign_rank = feature_rank(rows, feature_names, 'early_sign')
    nonearly_sign_rank = feature_rank(rows, feature_names, 'nonearly_sign')

    top_early = [r['feature'] for r in early_rank[:12]]
    early_trials = []
    for size in [1,2,3]:
        for keys in itertools.combinations(top_early, size):
            trial = subset_eval_binary(rows, list(keys), lambda r: r['profile']=='early_sharp', 'early_sharp')
            per = trial['per_scale_accuracy']
            score = per['160'] + 0.5 * mean([per['64'], per['96'], per['128']]) - 0.03 * size
            early_trials.append({'keys': list(keys), 'score': score, 'per_scale_accuracy': per})
    early_trials.sort(key=lambda x: x['score'], reverse=True)

    top_es = [r['feature'] for r in early_sign_rank[:12]]
    es_trials=[]
    for size in [1,2,3]:
        for keys in itertools.combinations(top_es, size):
            trial = subset_eval_sign(rows, list(keys), lambda r: r['profile']=='early_sharp')
            per = trial['per_scale_accuracy']
            score = per['160'] + 0.5*mean([per['64'],per['96'],per['128']]) - 0.03*size
            es_trials.append({'keys': list(keys), 'score': score, 'per_scale_accuracy': per})
    es_trials.sort(key=lambda x: x['score'], reverse=True)

    top_ns = [r['feature'] for r in nonearly_sign_rank[:12]]
    ns_trials=[]
    for size in [1,2,3]:
        for keys in itertools.combinations(top_ns, size):
            trial = subset_eval_sign(rows, list(keys), lambda r: r['profile']!='early_sharp')
            per = trial['per_scale_accuracy']
            score = per['160'] + 0.5*mean([per['64'],per['96'],per['128']]) - 0.03*size
            ns_trials.append({'keys': list(keys), 'score': score, 'per_scale_accuracy': per})
    ns_trials.sort(key=lambda x: x['score'], reverse=True)

    result = {
        'protocol': 'stage1_translation_richer_profile_scale_audit',
        'panel_root': args.panel_root,
        'top_profile_routing_features': early_rank[:20],
        'top_profile_routing_subset_trials': early_trials[:20],
        'top_early_sign_features': early_sign_rank[:20],
        'top_early_sign_subset_trials': es_trials[:20],
        'top_nonearly_sign_features': nonearly_sign_rank[:20],
        'top_nonearly_sign_subset_trials': ns_trials[:20],
        'recommendation': {
            'status': 'richer_profile_translation_panel_built',
            'next_task': 'integrate an explicit early_sharp routing branch and test it on the full N160 richer nuisance panel',
        },
    }
    (outdir / 'stage1_translation_richer_profile_scale_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = ['# STAGE1 TRANSLATION RICHER PROFILE SCALE AUDIT', '', '## Goal', 'Audit whether explicit profile routing and profile-specific sign observables can be learned on seen scales (64/96/128) and extrapolated to N160.', '', '## Top profile-routing features (early_sharp vs non-early)', '']
    for row in early_rank[:10]:
        ds = ', '.join([f'N{s}={row['deltas_by_scale'][str(s)]:.3f}' for s in [64,96,128,160]])
        lines.append(f"- `{row['feature']}`: score={row['score']:.3f}, consistency={row['consistency']:.2f}, min_abs={row['min_abs_delta']:.3f}; {ds}")
    lines.extend(['', '## Best profile-routing subset trials', ''])
    for row in early_trials[:10]:
        per = row['per_scale_accuracy']
        lines.append(f"- keys={row['keys']} | N64={per['64']:.3f}, N96={per['96']:.3f}, N128={per['128']:.3f}, N160={per['160']:.3f}, score={row['score']:.3f}")
    lines.extend(['', '## Best early_sharp sign subset trials', ''])
    for row in es_trials[:5]:
        per = row['per_scale_accuracy']
        lines.append(f"- keys={row['keys']} | N64={per['64']:.3f}, N96={per['96']:.3f}, N128={per['128']:.3f}, N160={per['160']:.3f}, score={row['score']:.3f}")
    lines.extend(['', '## Best non-early sign subset trials', ''])
    for row in ns_trials[:5]:
        per = row['per_scale_accuracy']
        lines.append(f"- keys={row['keys']} | N64={per['64']:.3f}, N96={per['96']:.3f}, N128={per['128']:.3f}, N160={per['160']:.3f}, score={row['score']:.3f}")
    lines.extend(['', '## Hard conclusion', '', '- Explicit profile routing is now testable on a clean translation-only richer-profile panel.', '- If a small early_sharp-routing key set extrapolates to N160, then the remaining richer-nuisance failure should be attacked as a routing/conditioning problem, not as missing sign observability.', '- The next high-value move is to splice the best early_sharp routing subset into the full N160 richer-nuisance decoder and compare against the current hybrid and the earlier probe-informed candidate.'])
    (outdir / 'STAGE1_TRANSLATION_RICHER_PROFILE_SCALE_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote translation richer profile scale audit to {outdir}')


if __name__ == '__main__':
    main()
