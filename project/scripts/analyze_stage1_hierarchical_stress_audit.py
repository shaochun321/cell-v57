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

from scripts.analyze_stage1_scale_sign_audit import extract_features

TRANSLATION_GROUP_KEYS = [
    'discrete_channel_track_swirl_circulation_family_shell_0',
    'discrete_channel_track_swirl_circulation_family_inner_level',
    'layered_coupling_track_bandwidth_shell_2',
    'discrete_channel_track_bandwidth_shell_2',
]
NONTRANSLATION_KEYS = [
    'discrete_channel_track_transfer_std',
    'agg_magnitude',
]
SIGN_KEYS = ['layered_coupling_track_circvec_z']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Stress-test the stage-1 hierarchical readout on richer perturbations.')
    p.add_argument('--train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-dir', type=str, default='outputs/stage1_hierarchical_stress_panel')
    p.add_argument('--outdir', type=str, default='outputs/stage1_hierarchical_stress_audit')
    return p.parse_args()


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def squared_distance(sample: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((sample['z_features'][k] - center[k]) ** 2 for k in keys)


def sign_spec(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    pos = mean_dict([s for s in samples if s['label'] == 'translation_x_pos'], keys)
    neg = mean_dict([s for s in samples if s['label'] == 'translation_x_neg'], keys)
    return {
        'mid': {k: 0.5 * (pos[k] + neg[k]) for k in keys},
        'weights': {k: pos[k] - neg[k] for k in keys},
    }


def sign_predict(sample: dict[str, Any], spec: dict[str, dict[str, float]], keys: list[str]) -> tuple[str, float]:
    score = sum(spec['weights'][k] * (sample['z_features'][k] - spec['mid'][k]) for k in keys)
    return ('translation_x_pos' if score > 0.0 else 'translation_x_neg'), score


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


def load_train_panel(panel_dir: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            samples.append({
                'seed': seed,
                'case_name': case_dir.name,
                'label': case_dir.name,
                'run_dir': str(case_dir),
                'features': extract_features(case_dir),
            })
    return samples


def load_stress_panel(panel_dir: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            samples.append({
                'seed': seed,
                'case_name': case_dir.name,
                'label': semantic_label(case_dir.name),
                'run_dir': str(case_dir),
                'features': extract_features(case_dir),
            })
    return samples


def zscore(samples: list[dict[str, Any]], feature_names: list[str], means: dict[str, float], stds: dict[str, float]) -> None:
    for s in samples:
        s['z_features'] = {k: (s['features'][k] - means[k]) / stds[k] for k in feature_names}


def accuracy(preds: list[dict[str, Any]]) -> float:
    return sum(int(p['predicted'] == p['label']) for p in preds) / len(preds) if preds else 0.0


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

    translation_center = mean_dict([s for s in train if s['label'].startswith('translation')], TRANSLATION_GROUP_KEYS)
    nontranslation_center = mean_dict([s for s in train if not s['label'].startswith('translation')], TRANSLATION_GROUP_KEYS)
    baseline_center = mean_dict([s for s in train if s['label'] == 'baseline'], NONTRANSLATION_KEYS)
    rotation_center = mean_dict([s for s in train if s['label'] == 'rotation_z_pos'], NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in train if s['label'].startswith('translation')], SIGN_KEYS)

    all_results: dict[str, Any] = {}
    for scale in [64, 96]:
        stress = load_stress_panel(Path(args.stress_dir) / f'N{scale}')
        zscore(stress, feature_names, means, stds)
        preds = []
        for sample in stress:
            d_translation = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
            d_nontranslation = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
            if d_translation < d_nontranslation:
                pred, score = sign_predict(sample, spec, SIGN_KEYS)
                preds.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': pred,
                    'stage1_predicted': 'translation',
                    'sign_score': score,
                })
            else:
                d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
                d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
                pred = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
                preds.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': pred,
                    'stage1_predicted': 'nontranslation',
                    'stage2_baseline_distance': d_baseline,
                    'stage2_rotation_distance': d_rotation,
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
        all_results[f'N{scale}'] = {
            'accuracy': accuracy(preds),
            'translation_accuracy': accuracy(translation_rows),
            'by_case': by_case,
            'predictions': preds,
        }

    result = {
        'protocol': 'stage1_hierarchical_stress_audit',
        'train_dir': args.train_dir,
        'stress_dir': args.stress_dir,
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'results': all_results,
    }
    (outdir / 'stage1_hierarchical_stress_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 hierarchical stress audit',
        '',
        'Goal: test whether the minimal hierarchical external readout survives richer nuisance variations while the semantic class stays the same.',
        '',
        'Training reference: N64 minimal panel only.',
        '',
    ]
    for scale in ['N64', 'N96']:
        r = all_results[scale]
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
    (outdir / 'STAGE1_HIERARCHICAL_STRESS_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] hierarchical stress audit written to {outdir}')


if __name__ == '__main__':
    main()
