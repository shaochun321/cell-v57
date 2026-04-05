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
SRC_DIR = PROJECT_ROOT / 'src'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.global_overview import extract_overview_features
from scripts.analyze_stage1_global_overview_audit import (
    semantic_label,
    zscore,
    squared_distance,
    mean_dict,
    class_mean,
    accuracy,
)

GATE_KEYS = [
    'overview_translation_dipole_norm_peak_abs',
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
]
NONTRANSLATION_KEYS = ['overview_event_energy_peak_abs']
SIGN_KEYS = ['overview_translation_dipole_x_mean']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate a fixed, physically interpretable global overview candidate.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=160)
    return p.parse_args()


def load_panel(panel_dir: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            samples.append({
                'scale': int(panel_dir.name[1:]),
                'seed': seed,
                'case_name': case_dir.name,
                'label': semantic_label(case_dir.name),
                'features': extract_overview_features(case_dir),
            })
    return samples


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
    all_samples = seen + target
    feature_names = list(seen[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in seen]) for k in feature_names}
    stds = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in seen])
        stds[k] = math.sqrt(var) if var > 0.0 else 1.0
    zscore(all_samples, feature_names, means, stds)

    seen_eval = evaluate(seen, seen)
    target_eval = evaluate(seen, target)
    result = {
        'protocol': 'stage1_global_overview_candidate',
        'panel_root': args.panel_root,
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'seen_eval': seen_eval,
        'target_eval': target_eval,
    }
    (outdir / 'stage1_global_overview_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 global overview candidate',
        '',
        'This candidate is intentionally simple and physically interpretable. It does not use local rescue logic.',
        '',
        '## Fixed overview keys',
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
        '## Interpretation',
        '',
        'If this candidate holds up, then the project has initial evidence that a missing global overview layer is not only philosophically plausible but already operational on the current stress panel.',
        '',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote global overview candidate to {outdir}')


if __name__ == '__main__':
    main()
