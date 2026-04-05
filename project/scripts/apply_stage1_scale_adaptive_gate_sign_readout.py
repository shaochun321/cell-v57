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

from scripts.analyze_stage1_scale_sign_audit import load_panel
from scripts.analyze_stage1_hierarchical_stress_audit import load_stress_panel, zscore, squared_distance
from scripts.analyze_stage1_hierarchical_gate_sign_tuned_audit import TRANSLATION_GROUP_KEYS, class_mean
from scripts.analyze_stage1_scale_adaptive_gate_sign_audit import (
    VETO_KEY,
    VETO_GAP_THRESHOLD,
    NONTRANSLATION_KEYS,
    LEGACY_SIGN_KEYS,
    SCALE_ADAPTIVE_SIGN_KEYS,
    SIGN_HANDOFF_SCALE,
    fit_affine_centers,
    center_from_affine,
    compute_veto_threshold,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Apply the scale-adaptive gate+sign readout to a stressed panel.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--target-scale', type=int, required=True)
    p.add_argument('--out', type=str, default='outputs/stage1_scale_adaptive_gate_sign_predictions.json')
    return p.parse_args()


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def main() -> None:
    args = parse_args()
    minimal_train = load_panel(Path(args.minimal_train_dir))
    feature_names = list(minimal_train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in minimal_train]) for k in feature_names}
    stds: dict[str, float] = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in minimal_train])
        stds[k] = math.sqrt(var) if var > 0.0 else 1.0
    for sample in minimal_train:
        sample['z_features'] = {k: (sample['features'][k] - means[k]) / stds[k] for k in feature_names}

    panels: dict[int, list[dict[str, Any]]] = {}
    for scale in [64, 96, args.target_scale]:
        panel = load_stress_panel(Path(args.stress_root) / f'N{scale}')
        zscore(panel, feature_names, means, stds)
        panels[scale] = panel

    gate_train = panels[64]
    stage2_train = panels[64] + panels[96]
    translation_center = class_mean(gate_train, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(gate_train, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = mean_dict([s for s in stage2_train if s['label'] == 'baseline'], NONTRANSLATION_KEYS)
    rotation_center = mean_dict([s for s in stage2_train if s['label'] == 'rotation_z_pos'], NONTRANSLATION_KEYS)
    pos_affine = fit_affine_centers({64: panels[64], 96: panels[96]}, 'translation_x_pos', SCALE_ADAPTIVE_SIGN_KEYS)
    neg_affine = fit_affine_centers({64: panels[64], 96: panels[96]}, 'translation_x_neg', SCALE_ADAPTIVE_SIGN_KEYS)
    pos_center = center_from_affine(pos_affine, args.target_scale)
    neg_center = center_from_affine(neg_affine, args.target_scale)
    legacy_pos = mean_dict([s for s in minimal_train if s['label'] == 'translation_x_pos'], LEGACY_SIGN_KEYS)
    legacy_neg = mean_dict([s for s in minimal_train if s['label'] == 'translation_x_neg'], LEGACY_SIGN_KEYS)
    legacy_mid = {k: 0.5 * (legacy_pos[k] + legacy_neg[k]) for k in LEGACY_SIGN_KEYS}
    legacy_weights = {k: legacy_pos[k] - legacy_neg[k] for k in LEGACY_SIGN_KEYS}

    stage1_rows: list[dict[str, Any]] = []
    for sample in panels[args.target_scale]:
        d_translation = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
        d_nontranslation = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
        stage1_rows.append({
            'sample': sample,
            'translation_distance': d_translation,
            'nontranslation_distance': d_nontranslation,
            'stage1_predicted': 'translation' if d_translation < d_nontranslation else 'nontranslation',
            VETO_KEY: sample['z_features'][VETO_KEY],
        })

    veto_threshold = compute_veto_threshold(stage1_rows)
    predictions: list[dict[str, Any]] = []
    for row in stage1_rows:
        sample = row['sample']
        stage1_predicted = row['stage1_predicted']
        rerouted = False
        if stage1_predicted == 'translation' and veto_threshold is not None and row[VETO_KEY] < veto_threshold:
            stage1_predicted = 'nontranslation'
            rerouted = True
        if stage1_predicted == 'translation':
            if args.target_scale < SIGN_HANDOFF_SCALE:
                legacy_score = sum(legacy_weights[k] * (sample['z_features'][k] - legacy_mid[k]) for k in LEGACY_SIGN_KEYS)
                predicted = 'translation_x_pos' if legacy_score > 0.0 else 'translation_x_neg'
                predictions.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': predicted,
                    'stage1_predicted': 'translation',
                    'sign_mode': 'legacy',
                    'rerouted_by_veto': rerouted,
                    'translation_distance': row['translation_distance'],
                    'nontranslation_distance': row['nontranslation_distance'],
                    'veto_key_value': row[VETO_KEY],
                    'veto_threshold': veto_threshold,
                    'legacy_sign_score': legacy_score,
                })
            else:
                d_pos = squared_distance(sample, pos_center, SCALE_ADAPTIVE_SIGN_KEYS)
                d_neg = squared_distance(sample, neg_center, SCALE_ADAPTIVE_SIGN_KEYS)
                predicted = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
                predictions.append({
                    'seed': sample['seed'],
                    'case_name': sample['case_name'],
                    'label': sample['label'],
                    'predicted': predicted,
                    'stage1_predicted': 'translation',
                    'sign_mode': 'scale_adaptive',
                    'rerouted_by_veto': rerouted,
                    'translation_distance': row['translation_distance'],
                    'nontranslation_distance': row['nontranslation_distance'],
                    'veto_key_value': row[VETO_KEY],
                    'veto_threshold': veto_threshold,
                    'sign_distance_pos': d_pos,
                    'sign_distance_neg': d_neg,
                })
        else:
            d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            predicted = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
            predictions.append({
                'seed': sample['seed'],
                'case_name': sample['case_name'],
                'label': sample['label'],
                'predicted': predicted,
                'stage1_predicted': 'nontranslation',
                'rerouted_by_veto': rerouted,
                'translation_distance': row['translation_distance'],
                'nontranslation_distance': row['nontranslation_distance'],
                'veto_key_value': row[VETO_KEY],
                'veto_threshold': veto_threshold,
                'stage2_baseline_distance': d_baseline,
                'stage2_rotation_distance': d_rotation,
            })

    out = {
        'protocol': 'stage1_scale_adaptive_gate_sign_apply',
        'target_scale': args.target_scale,
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'veto_key': VETO_KEY,
        'veto_gap_threshold': VETO_GAP_THRESHOLD,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'legacy_sign_keys': LEGACY_SIGN_KEYS,
        'scale_adaptive_sign_keys': SCALE_ADAPTIVE_SIGN_KEYS,
        'sign_handoff_scale': SIGN_HANDOFF_SCALE,
        'accuracy': sum(int(p['predicted'] == p['label']) for p in predictions) / len(predictions),
        'predictions': predictions,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'[OK] wrote scale-adaptive gate+sign predictions to {out_path} (accuracy={out["accuracy"]:.3f})')


if __name__ == '__main__':
    main()
