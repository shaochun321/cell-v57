from __future__ import annotations

import argparse
import json
import os
import sys
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_hierarchical_stress_audit import load_train_panel, load_stress_panel, zscore

TRANSLATION_GROUP_KEYS = [
    'discrete_channel_track_swirl_circulation_family_shell_0',
    'discrete_channel_track_swirl_circulation_family_inner_level',
    'layered_coupling_track_bandwidth_shell_2',
    'discrete_channel_track_bandwidth_shell_2',
]
NONTRANSLATION_KEYS = ['discrete_channel_track_transfer_std']
SIGN_KEYS = [
    'layered_coupling_track_circvec_z',
    'layered_coupling_track_source_circ_z',
    'local_propagation_track_circvec_z',
    'local_propagation_track_source_circ_z',
    'discrete_channel_track_circvec_z',
    'discrete_channel_track_source_circ_z',
    'bundle_fast_event_mean',
    'discrete_channel_track_dynamic_phasic_family_shell_2',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Apply the nuisance-robust hierarchical readout candidate.')
    p.add_argument('--train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_hierarchical_stress_robust_audit')
    return p.parse_args()


def class_mean(samples: list[dict[str, Any]], pred, keys: list[str]) -> dict[str, float]:
    subset = [s for s in samples if pred(s)]
    return {k: mean([s['z_features'][k] for s in subset]) for k in keys}


def squared_distance(sample: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((sample['z_features'][k] - center[k]) ** 2 for k in keys)


def sign_spec(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    pos = class_mean(samples, lambda s: s['label'] == 'translation_x_pos', keys)
    neg = class_mean(samples, lambda s: s['label'] == 'translation_x_neg', keys)
    return {
        'mid': {k: 0.5 * (pos[k] + neg[k]) for k in keys},
        'weights': {k: pos[k] - neg[k] for k in keys},
    }


def sign_predict(sample: dict[str, Any], spec: dict[str, dict[str, float]], keys: list[str]) -> tuple[str, float]:
    score = sum(spec['weights'][k] * (sample['z_features'][k] - spec['mid'][k]) for k in keys)
    return ('translation_x_pos' if score > 0.0 else 'translation_x_neg'), score


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    train = load_train_panel(Path(args.train_dir))
    feature_names = list(train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in train]) for k in feature_names}
    stds = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in train])
        stds[k] = sqrt(var) if var > 0.0 else 1.0
    zscore(train, feature_names, means, stds)

    translation_center = class_mean(train, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(train, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = class_mean(train, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    rotation_center = class_mean(train, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in train if s['label'].startswith('translation')], SIGN_KEYS)

    results: dict[str, Any] = {}
    for scale in [64, 96]:
        panel = load_stress_panel(Path(args.stress_dir) / f'N{scale}')
        zscore(panel, feature_names, means, stds)
        preds = []
        for sample in panel:
            d_t = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
            d_n = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
            if d_t < d_n:
                pred, score = sign_predict(sample, spec, SIGN_KEYS)
                preds.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': pred,
                    'stage1_predicted': 'translation',
                    'sign_score': score,
                    'translation_distance': d_t,
                    'nontranslation_distance': d_n,
                })
            else:
                d_b = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
                d_r = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
                pred = 'baseline' if d_b < d_r else 'rotation_z_pos'
                preds.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': pred,
                    'stage1_predicted': 'nontranslation',
                    'stage2_baseline_distance': d_b,
                    'stage2_rotation_distance': d_r,
                    'translation_distance': d_t,
                    'nontranslation_distance': d_n,
                })
        by_case = {}
        for case_name in sorted({p['case_name'] for p in preds}):
            rows = [p for p in preds if p['case_name'] == case_name]
            by_case[case_name] = {
                'semantic_label': rows[0]['label'],
                'accuracy': accuracy(rows),
                'num_samples': len(rows),
            }
        translation_rows = [p for p in preds if p['label'].startswith('translation')]
        results[f'N{scale}'] = {
            'accuracy': accuracy(preds),
            'translation_accuracy': accuracy(translation_rows),
            'by_case': by_case,
            'predictions': preds,
        }

    result = {
        'protocol': 'stage1_hierarchical_stress_robust_audit',
        'train_dir': args.train_dir,
        'stress_dir': args.stress_dir,
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'results': results,
    }
    (outdir / 'stage1_hierarchical_stress_robust_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 hierarchical stress robust audit',
        '',
        'Goal: apply a nuisance-robust hierarchical decoder candidate using sign-stable z-circulation features while keeping the external readout simple.',
        '',
    ]
    for scale in ['N64', 'N96']:
        r = results[scale]
        lines.extend([
            f'## {scale}',
            '',
            f"- overall accuracy: {r['accuracy']:.3f}",
            f"- translation accuracy: {r['translation_accuracy']:.3f}",
            '',
            '### By case',
            '',
        ])
        for case_name, row in r['by_case'].items():
            lines.append(f"- {case_name} ({row['semantic_label']}): {row['accuracy']:.3f}")
        lines.append('')
    lines.extend(['## Key sets', '', '### Translation-group keys'])
    for k in TRANSLATION_GROUP_KEYS:
        lines.append(f'- {k}')
    lines.extend(['', '### Nontranslation keys'])
    for k in NONTRANSLATION_KEYS:
        lines.append(f'- {k}')
    lines.extend(['', '### Sign keys'])
    for k in SIGN_KEYS:
        lines.append(f'- {k}')
    (outdir / 'STAGE1_HIERARCHICAL_STRESS_ROBUST_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] robust hierarchical stress audit written to {outdir}')


if __name__ == '__main__':
    main()
