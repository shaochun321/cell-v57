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
from scripts.analyze_stage1_hierarchical_stress_robust_audit import (
    TRANSLATION_GROUP_KEYS, NONTRANSLATION_KEYS, SIGN_KEYS, class_mean, squared_distance, sign_spec, sign_predict
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Apply the nuisance-robust stage-1 hierarchical readout.')
    p.add_argument('--train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--target-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw/N96')
    p.add_argument('--out', type=str, default='outputs/stage1_hierarchical_stress_robust_predictions.json')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    train = load_train_panel(Path(args.train_dir))
    feature_names = list(train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in train]) for k in feature_names}
    stds = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in train])
        stds[k] = sqrt(var) if var > 0.0 else 1.0
    zscore(train, feature_names, means, stds)

    panel = load_stress_panel(Path(args.target_dir))
    zscore(panel, feature_names, means, stds)

    translation_center = class_mean(train, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(train, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = class_mean(train, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    rotation_center = class_mean(train, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in train if s['label'].startswith('translation')], SIGN_KEYS)

    preds = []
    for sample in panel:
        d_t = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
        d_n = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
        if d_t < d_n:
            pred, score = sign_predict(sample, spec, SIGN_KEYS)
            preds.append({'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred, 'stage1_predicted': 'translation', 'sign_score': score})
        else:
            d_b = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_r = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = 'baseline' if d_b < d_r else 'rotation_z_pos'
            preds.append({'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred, 'stage1_predicted': 'nontranslation'})

    out = {
        'protocol': 'stage1_hierarchical_stress_robust_apply',
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'accuracy': sum(int(p['predicted'] == p['label']) for p in preds) / len(preds),
        'predictions': preds,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'[OK] wrote robust hierarchical predictions to {out_path} (accuracy={out["accuracy"]:.3f})')


if __name__ == '__main__':
    main()
