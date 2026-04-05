from __future__ import annotations

import argparse
import itertools
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
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.global_overview import extract_overview_features

GATE_FEATURE_CANDIDATES = [
    'overview_translation_dipole_norm_peak_abs',
    'overview_translation_dipole_x_peak_abs',
    'overview_polarity_dipole_norm_peak_abs',
    'overview_polarity_dipole_x_peak_abs',
    'overview_rotation_energy_peak_abs',
    'overview_event_energy_peak_abs',
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_translation_quad_zz_mean',
    'overview_translation_to_rotation_ratio',
    'overview_translation_to_event_ratio',
]

SIGN_FEATURE_CANDIDATES = [
    'overview_translation_dipole_x_mean',
    'overview_translation_dipole_x_peak',
    'overview_polarity_dipole_x_mean',
    'overview_polarity_dipole_x_peak',
    'overview_translation_quad_xx_mean',
    'overview_translation_quad_zz_mean',
    'overview_polarity_quad_xx_mean',
    'overview_polarity_quad_zz_mean',
]

NONTRANSLATION_FEATURE_CANDIDATES = [
    'overview_rotation_energy_peak_abs',
    'overview_event_energy_peak_abs',
    'overview_rotation_dipole_norm_peak_abs',
    'overview_translation_to_rotation_ratio',
    'overview_translation_to_event_ratio',
    'overview_agg_static_peak_abs',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze a parallel global overview prototype.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_audit')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=160)
    return p.parse_args()


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


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
                'run_dir': str(case_dir),
                'features': extract_overview_features(case_dir),
            })
    return samples


def zscore(samples: list[dict[str, Any]], feature_names: list[str], means: dict[str, float], stds: dict[str, float]) -> None:
    for s in samples:
        s['z_features'] = {k: (s['features'][k] - means[k]) / stds[k] for k in feature_names}


def squared_distance(sample: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((sample['z_features'][k] - center[k]) ** 2 for k in keys)


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def gate_label(label: str) -> str:
    return 'translation' if label.startswith('translation') else 'nontranslation'


def class_mean(samples: list[dict[str, Any]], predicate, keys: list[str]) -> dict[str, float]:
    subset = [s for s in samples if predicate(s)]
    return mean_dict(subset, keys)


def leave_one_seed_out_gate_accuracy(samples: list[dict[str, Any]], keys: list[str]) -> float:
    seeds = sorted({(s['scale'], s['seed']) for s in samples})
    rows = []
    for held_scale, held_seed in seeds:
        train = [s for s in samples if not (s['scale'] == held_scale and s['seed'] == held_seed)]
        test = [s for s in samples if s['scale'] == held_scale and s['seed'] == held_seed]
        t_center = class_mean(train, lambda s: gate_label(s['label']) == 'translation', keys)
        nt_center = class_mean(train, lambda s: gate_label(s['label']) == 'nontranslation', keys)
        for sample in test:
            d_t = squared_distance(sample, t_center, keys)
            d_nt = squared_distance(sample, nt_center, keys)
            pred = 'translation' if d_t < d_nt else 'nontranslation'
            rows.append({'predicted': pred, 'label': gate_label(sample['label'])})
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows)


def leave_one_seed_out_sign_accuracy(samples: list[dict[str, Any]], keys: list[str]) -> float:
    seeds = sorted({(s['scale'], s['seed']) for s in samples})
    rows = []
    for held_scale, held_seed in seeds:
        train = [s for s in samples if not (s['scale'] == held_scale and s['seed'] == held_seed)]
        test = [s for s in samples if s['scale'] == held_scale and s['seed'] == held_seed]
        pos_center = class_mean(train, lambda s: s['label'] == 'translation_x_pos', keys)
        neg_center = class_mean(train, lambda s: s['label'] == 'translation_x_neg', keys)
        for sample in test:
            d_pos = squared_distance(sample, pos_center, keys)
            d_neg = squared_distance(sample, neg_center, keys)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            rows.append({'predicted': pred, 'label': sample['label']})
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows)




def leave_one_seed_out_binary_accuracy(samples: list[dict[str, Any]], keys: list[str], pos_label: str, neg_label: str) -> float:
    seeds = sorted({(s["scale"], s["seed"]) for s in samples})
    rows = []
    for held_scale, held_seed in seeds:
        train = [s for s in samples if not (s["scale"] == held_scale and s["seed"] == held_seed)]
        test = [s for s in samples if s["scale"] == held_scale and s["seed"] == held_seed]
        pos_center = class_mean(train, lambda s: s["label"] == pos_label, keys)
        neg_center = class_mean(train, lambda s: s["label"] == neg_label, keys)
        for sample in test:
            d_pos = squared_distance(sample, pos_center, keys)
            d_neg = squared_distance(sample, neg_center, keys)
            pred = pos_label if d_pos < d_neg else neg_label
            rows.append({"predicted": pred, "label": sample["label"]})
    return sum(int(r["predicted"] == r["label"]) for r in rows) / len(rows)

def choose_best_subset(samples: list[dict[str, Any]], candidates: list[str], subset_sizes: tuple[int, ...], scorer) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for k in subset_sizes:
        for subset in itertools.combinations(candidates, k):
            score = scorer(samples, list(subset))
            cand = {'keys': list(subset), 'score': score}
            if best is None or cand['score'] > best['score']:
                best = cand
    assert best is not None
    return best


def evaluate_full_readout(seen_samples: list[dict[str, Any]], target_samples: list[dict[str, Any]], gate_keys: list[str], nontranslation_keys: list[str], sign_keys: list[str]) -> dict[str, Any]:
    t_center = class_mean(seen_samples, lambda s: gate_label(s['label']) == 'translation', gate_keys)
    nt_center = class_mean(seen_samples, lambda s: gate_label(s['label']) == 'nontranslation', gate_keys)
    baseline_center = class_mean(seen_samples, lambda s: s['label'] == 'baseline', nontranslation_keys)
    rotation_center = class_mean(seen_samples, lambda s: s['label'] == 'rotation_z_pos', nontranslation_keys)
    pos_center = class_mean(seen_samples, lambda s: s['label'] == 'translation_x_pos', sign_keys)
    neg_center = class_mean(seen_samples, lambda s: s['label'] == 'translation_x_neg', sign_keys)

    preds = []
    for sample in target_samples:
        d_t = squared_distance(sample, t_center, gate_keys)
        d_nt = squared_distance(sample, nt_center, gate_keys)
        if d_t < d_nt:
            d_pos = squared_distance(sample, pos_center, sign_keys)
            d_neg = squared_distance(sample, neg_center, sign_keys)
            pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
            preds.append({
                'scale': sample['scale'],
                'seed': sample['seed'],
                'case_name': sample['case_name'],
                'label': sample['label'],
                'predicted': pred,
                'stage1_predicted': 'translation',
                'translation_distance': d_t,
                'nontranslation_distance': d_nt,
                'sign_distance_pos': d_pos,
                'sign_distance_neg': d_neg,
            })
        else:
            d_baseline = squared_distance(sample, baseline_center, nontranslation_keys)
            d_rotation = squared_distance(sample, rotation_center, nontranslation_keys)
            pred = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
            preds.append({
                'scale': sample['scale'],
                'seed': sample['seed'],
                'case_name': sample['case_name'],
                'label': sample['label'],
                'predicted': pred,
                'stage1_predicted': 'nontranslation',
                'translation_distance': d_t,
                'nontranslation_distance': d_nt,
                'stage2_baseline_distance': d_baseline,
                'stage2_rotation_distance': d_rotation,
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

    best_gate = choose_best_subset(seen, GATE_FEATURE_CANDIDATES, (1, 2, 3), leave_one_seed_out_gate_accuracy)
    translation_seen = [s for s in seen if s['label'].startswith('translation')]
    best_sign = choose_best_subset(translation_seen, SIGN_FEATURE_CANDIDATES, (1, 2, 3), leave_one_seed_out_sign_accuracy)
    nontranslation_seen = [s for s in seen if not s['label'].startswith('translation')]
    best_nontranslation = choose_best_subset(nontranslation_seen, NONTRANSLATION_FEATURE_CANDIDATES, (1, 2, 3), lambda samples, keys: leave_one_seed_out_binary_accuracy(samples, keys, 'baseline', 'rotation_z_pos'))

    seen_eval = evaluate_full_readout(seen, seen, best_gate['keys'], best_nontranslation['keys'], best_sign['keys'])
    target_eval = evaluate_full_readout(seen, target, best_gate['keys'], best_nontranslation['keys'], best_sign['keys'])

    result = {
        'protocol': 'stage1_global_overview_audit',
        'panel_root': args.panel_root,
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_feature_candidates': GATE_FEATURE_CANDIDATES,
        'sign_feature_candidates': SIGN_FEATURE_CANDIDATES,
        'nontranslation_feature_candidates': NONTRANSLATION_FEATURE_CANDIDATES,
        'best_gate': best_gate,
        'best_sign': best_sign,
        'best_nontranslation': best_nontranslation,
        'seen_eval': seen_eval,
        'target_eval': target_eval,
    }
    (outdir / 'stage1_global_overview_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 global overview prototype audit',
        '',
        'This audit does not replace the existing readout stack. It adds a parallel overview layer built from global bundle integrals and low-order angular moments, then tests whether a low-complexity overview-only readout can hold semantic equivalence across scale.',
        '',
        '## Best overview feature sets selected on seen scales only',
        '',
        f"- gate keys: {', '.join(best_gate['keys'])} (seen-scale LOO={best_gate['score']:.3f})",
        f"- nontranslation keys: {', '.join(best_nontranslation['keys'])} (seen-scale LOO={best_nontranslation['score']:.3f})",
        f"- sign keys: {', '.join(best_sign['keys'])} (seen-scale LOO={best_sign['score']:.3f})",
        '',
        '## Full readout results',
        '',
        f"- seen-scale overall: {seen_eval['accuracy']:.3f}",
        f"- seen-scale translation: {seen_eval['translation_accuracy']:.3f}",
        f"- N{args.target_scale} overall: {target_eval['accuracy']:.3f}",
        f"- N{args.target_scale} translation: {target_eval['translation_accuracy']:.3f}",
        '',
        '## Current interpretation',
        '',
        'If this prototype holds useful accuracy with low-complexity overview variables, it supports the project hypothesis that a missing global overview layer is a real architectural gap. If it fails cleanly, that is still useful because it means the project cannot skip local/profile-specific handling so easily.',
        '',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote global overview audit to {outdir}')


if __name__ == '__main__':
    main()
