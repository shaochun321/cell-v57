from __future__ import annotations

import argparse
import json
import os
import sys
from math import sqrt
from pathlib import Path
from statistics import mean

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_hierarchical_stress_audit import load_train_panel, load_stress_panel, sign_predict, sign_spec, squared_distance, zscore
from scripts.analyze_stage1_hierarchical_gate_sign_tuned_audit import TRANSLATION_GROUP_KEYS, NONTRANSLATION_KEYS, SIGN_KEYS, class_mean


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Apply the tuned stage-1 gate+sign external readout to a stressed panel.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-train-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw/N64')
    p.add_argument('--target-dir', type=str, required=True)
    p.add_argument('--out', type=str, default='outputs/stage1_hierarchical_gate_sign_tuned_predictions.json')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    minimal_train = load_train_panel(Path(args.minimal_train_dir))
    feature_names = list(minimal_train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in minimal_train]) for k in feature_names}
    stds = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in minimal_train])
        stds[k] = sqrt(var) if var > 0.0 else 1.0
    zscore(minimal_train, feature_names, means, stds)

    stress_train = load_stress_panel(Path(args.stress_train_dir))
    zscore(stress_train, feature_names, means, stds)
    target = load_stress_panel(Path(args.target_dir))
    zscore(target, feature_names, means, stds)

    translation_center = class_mean(stress_train, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(stress_train, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = class_mean(stress_train, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    rotation_center = class_mean(stress_train, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in minimal_train if s['label'].startswith('translation')], SIGN_KEYS)

    preds = []
    for sample in target:
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
                'translation_distance': d_translation,
                'nontranslation_distance': d_nontranslation,
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
                'translation_distance': d_translation,
                'nontranslation_distance': d_nontranslation,
                'stage2_baseline_distance': d_baseline,
                'stage2_rotation_distance': d_rotation,
            })

    out = {
        'protocol': 'stage1_hierarchical_gate_sign_tuned_apply',
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'accuracy': sum(int(p['predicted'] == p['label']) for p in preds) / len(preds),
        'predictions': preds,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'[OK] wrote tuned gate+sign predictions to {out_path} (accuracy={out["accuracy"]:.3f})')


if __name__ == '__main__':
    main()
