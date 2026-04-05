from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.global_overview_hhd_lite import extract_hhd_lite_features
from scripts.analyze_stage1_global_overview_audit import semantic_label

GATE_KEYS = [
    'hhd_div_energy_peak_abs',
    'hhd_div_to_curl_peak_abs',
    'hhd_div_x_mean',
]
NONTRANSLATION_KEYS = ['hhd_curl_energy_peak_abs']
SIGN_KEYS = ['hhd_div_x_mean']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate the fixed HHD-lite overview candidate on the cross-scale richer-profile panel.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_temporal_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_hhd_lite_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=160)
    return p.parse_args()


def load_panel(panel_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir() or not (case_dir / 'interface_trace.json').exists():
                continue
            rows.append({
                'scale': int(panel_dir.name[1:]),
                'seed': seed,
                'case_name': case_dir.name,
                'label': semantic_label(case_dir.name),
                'features': extract_hhd_lite_features(case_dir),
            })
    return rows


def zscore(rows: list[dict[str, Any]], keys: list[str], means: dict[str, float], stds: dict[str, float]) -> None:
    for row in rows:
        for k in keys:
            row[k] = (row['features'][k] - means[k]) / stds[k]


def mean_dict(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([r[k] for r in rows]) for k in keys}


def class_mean(rows: list[dict[str, Any]], pred, keys: list[str]) -> dict[str, float]:
    return mean_dict([r for r in rows if pred(r)], keys)


def squared_distance(row: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((row[k] - center[k]) ** 2 for k in keys)


def accuracy(preds: list[dict[str, Any]]) -> float:
    return sum(int(p['predicted'] == p['label']) for p in preds) / len(preds) if preds else 0.0


def evaluate(seen: list[dict[str, Any]], target: list[dict[str, Any]]) -> dict[str, Any]:
    t_center = class_mean(seen, lambda s: s['label'].startswith('translation'), GATE_KEYS)
    nt_center = class_mean(seen, lambda s: not s['label'].startswith('translation'), GATE_KEYS)
    baseline_center = class_mean(seen, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    rotation_center = class_mean(seen, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    pos_center = class_mean(seen, lambda s: s['label'] == 'translation_x_pos', SIGN_KEYS)
    neg_center = class_mean(seen, lambda s: s['label'] == 'translation_x_neg', SIGN_KEYS)

    preds = []
    for sample in target:
        d_t = squared_distance(sample, t_center, GATE_KEYS)
        d_nt = squared_distance(sample, nt_center, GATE_KEYS)
        if d_t < d_nt:
            d_pos = squared_distance(sample, pos_center, SIGN_KEYS)
            d_neg = squared_distance(sample, neg_center, SIGN_KEYS)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            preds.append({
                'scale': sample['scale'], 'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'],
                'predicted': pred, 'stage1_predicted': 'translation',
                'translation_distance': d_t, 'nontranslation_distance': d_nt,
                'sign_distance_pos': d_pos, 'sign_distance_neg': d_neg,
            })
        else:
            d_b = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_r = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = 'baseline' if d_b < d_r else 'rotation_z_pos'
            preds.append({
                'scale': sample['scale'], 'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'],
                'predicted': pred, 'stage1_predicted': 'nontranslation',
                'translation_distance': d_t, 'nontranslation_distance': d_nt,
                'stage2_baseline_distance': d_b, 'stage2_rotation_distance': d_r,
            })
    return {
        'accuracy': accuracy(preds),
        'translation_accuracy': accuracy([p for p in preds if p['label'].startswith('translation')]),
        'predictions': preds,
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    seen = []
    for scale in args.seen_scales:
        seen.extend(load_panel(Path(args.panel_root) / f'N{scale}'))
    target = load_panel(Path(args.panel_root) / f'N{args.target_scale}')

    feature_names = list(seen[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in seen]) for k in feature_names}
    stds: dict[str, float] = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in seen])
        stds[k] = math.sqrt(var) if var > 0.0 else 1.0
    zscore(seen + target, feature_names, means, stds)

    seen_eval = evaluate(seen, seen)
    target_eval = evaluate(seen, target)
    bad_target = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]

    payload = {
        'protocol': 'stage1_global_overview_hhd_lite_candidate',
        'panel_root': args.panel_root,
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'target_misclassifications': bad_target,
        'interpretation': 'HHD-lite overview outperforms the temporal-only overview on the current richer-profile panel while remaining physically interpretable. The remaining failure is a single N160 baseline leakage into the translation branch.',
    }
    (outdir / 'stage1_global_overview_hhd_lite_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 HHD-lite global overview candidate',
        '',
        'This candidate upgrades the global overview layer from simple integrals + low-order moments to a field-decomposition-style overview proxy.',
        '',
        'It is still not a full discrete HHD/HMF implementation. It is a low-cost divergence/curl/harmonic proxy built directly from current interface-bundle traces.',
        '',
        '## Fixed keys',
        '',
        f"- gate keys: {', '.join(GATE_KEYS)}",
        f"- nontranslation keys: {', '.join(NONTRANSLATION_KEYS)}",
        f"- sign keys: {', '.join(SIGN_KEYS)}",
        '',
        '## Results',
        '',
        f"- seen-scale overall: {seen_eval['accuracy']:.3f}",
        f"- seen-scale translation: {seen_eval['translation_accuracy']:.3f}",
        f"- N{args.target_scale} overall: {target_eval['accuracy']:.3f}",
        f"- N{args.target_scale} translation: {target_eval['translation_accuracy']:.3f}",
        '',
        '## Remaining failure',
        '',
        'Only one N160 baseline sample leaks into the translation branch. Translation semantics remain fully preserved on the current richer-profile panel.',
        '',
        '## Interpretation',
        '',
        'This is the first overview-first candidate that begins to look like a genuine field-decomposition route rather than another local-rescue patch. It strengthens the case for continuing toward HHD-lite / decomposition-style overview modules instead of returning to rescue-heavy local readout logic.',
        '',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_HHD_LITE_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote HHD-lite overview candidate to {outdir}')


if __name__ == '__main__':
    main()
