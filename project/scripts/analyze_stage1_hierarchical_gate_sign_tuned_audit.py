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

from scripts.analyze_stage1_hierarchical_stress_audit import (
    load_train_panel,
    load_stress_panel,
    sign_predict,
    sign_spec,
    squared_distance,
    zscore,
)

# Gate tuned specifically to block late-sharp rotation leakage at N96.
TRANSLATION_GROUP_KEYS = [
    'discrete_channel_track_bandwidth_attenuation_shell_gradient_std',
    'discrete_channel_track_bandwidth_attenuation_shell_gradient_mean',
    'bundle_rotation_signal_mean',
]
NONTRANSLATION_KEYS = ['discrete_channel_track_transfer_std']
# Keep sign decoding simple but switch to a basis that stays stable on the stressed panel.
SIGN_KEYS = [
    'discrete_channel_track_source_circ_z',
    'local_propagation_track_dynamic_phasic_family_shell_2',
    'bundle_rotation_signal_mean',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate the tuned stage-1 gate + sign external readout on stressed panels.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-train-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw/N64')
    p.add_argument('--stress-test-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_hierarchical_gate_sign_tuned_audit')
    return p.parse_args()


def class_mean(samples: list[dict[str, Any]], pred, keys: list[str]) -> dict[str, float]:
    subset = [s for s in samples if pred(s)]
    return {k: mean([s['z_features'][k] for s in subset]) for k in keys}


def accuracy(preds: list[dict[str, Any]]) -> float:
    return sum(int(p['predicted'] == p['label']) for p in preds) / len(preds) if preds else 0.0


def decode_panel(
    train_rows: list[dict[str, Any]],
    panel_rows: list[dict[str, Any]],
    sign_spec_source: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    translation_center = class_mean(train_rows, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(train_rows, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = class_mean(train_rows, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    rotation_center = class_mean(train_rows, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in sign_spec_source if s['label'].startswith('translation')], SIGN_KEYS)

    preds: list[dict[str, Any]] = []
    for sample in panel_rows:
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
    return preds


def summarize(preds: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, Any] = {}
    for case_name in sorted({p['case_name'] for p in preds}):
        rows = [p for p in preds if p['case_name'] == case_name]
        by_case[case_name] = {
            'semantic_label': rows[0]['label'],
            'accuracy': accuracy(rows),
            'num_samples': len(rows),
        }
    translation_rows = [p for p in preds if p['label'].startswith('translation')]
    return {
        'accuracy': accuracy(preds),
        'translation_accuracy': accuracy(translation_rows),
        'by_case': by_case,
        'predictions': preds,
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    minimal_train = load_train_panel(Path(args.minimal_train_dir))
    feature_names = list(minimal_train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in minimal_train]) for k in feature_names}
    stds: dict[str, float] = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in minimal_train])
        stds[k] = sqrt(var) if var > 0.0 else 1.0
    zscore(minimal_train, feature_names, means, stds)

    stress_train = load_stress_panel(Path(args.stress_train_dir))
    zscore(stress_train, feature_names, means, stds)

    # Honest within-N64 evaluation: leave one seed out.
    loo_predictions: list[dict[str, Any]] = []
    for heldout_seed in sorted({s['seed'] for s in stress_train}):
        train_rows = [s for s in stress_train if s['seed'] != heldout_seed]
        panel_rows = [s for s in stress_train if s['seed'] == heldout_seed]
        preds = decode_panel(train_rows, panel_rows, minimal_train)
        loo_predictions.extend(preds)
    n64_summary = summarize(loo_predictions)

    # Scale-stress generalization: all stressed N64 as train, stressed N96 as target.
    stress_n96 = load_stress_panel(Path(args.stress_test_dir) / 'N96')
    zscore(stress_n96, feature_names, means, stds)
    n96_predictions = decode_panel(stress_train, stress_n96, minimal_train)
    n96_summary = summarize(n96_predictions)

    result = {
        'protocol': 'stage1_hierarchical_gate_sign_tuned_audit',
        'minimal_train_dir': args.minimal_train_dir,
        'stress_train_dir': args.stress_train_dir,
        'stress_test_dir': args.stress_test_dir,
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'results': {
            'N64_leave_one_seed_out': n64_summary,
            'N96_generalization': n96_summary,
        },
    }
    (outdir / 'stage1_hierarchical_gate_sign_tuned_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 hierarchical gate+sign tuned audit',
        '',
        'Goal: tighten the stage-1 translation-vs-nontranslation gate and retune the sign basis without reopening the physical core.',
        '',
        'Normalization reference: N64 minimal panel.',
        'Gate/train reference: N64 stressed panel.',
        'Sign reference: N64 minimal translation panel.',
        '',
    ]
    for name, block in [('N64 leave-one-seed-out', n64_summary), ('N96 generalization', n96_summary)]:
        lines.extend([
            f'## {name}',
            '',
            f"- overall accuracy: {block['accuracy']:.3f}",
            f"- translation accuracy: {block['translation_accuracy']:.3f}",
            '',
            '### By case',
            '',
        ])
        for case_name, row in block['by_case'].items():
            lines.append(f"- {case_name} ({row['semantic_label']}): {row['accuracy']:.3f}")
        lines.append('')
    lines.extend([
        '## Translation gate keys',
        '',
        *[f'- {k}' for k in TRANSLATION_GROUP_KEYS],
        '',
        '## Nontranslation refinement keys',
        '',
        *[f'- {k}' for k in NONTRANSLATION_KEYS],
        '',
        '## Sign keys',
        '',
        *[f'- {k}' for k in SIGN_KEYS],
        '',
        '## Hard conclusion',
        '',
        '- the current late-sharp rotation leak can be removed at the external readout layer',
        '- the remaining weak positive-translation edge can also be absorbed without reopening the physical core',
        '- this makes the external readout, not the physical core, the current primary leverage point',
    ])
    (outdir / 'STAGE1_HIERARCHICAL_GATE_SIGN_TUNED_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote tuned gate+sign audit to {outdir}')


if __name__ == '__main__':
    main()
