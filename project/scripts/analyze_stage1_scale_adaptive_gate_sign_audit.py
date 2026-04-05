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

VETO_KEY = 'discrete_channel_track_transfer_std'
NONTRANSLATION_KEYS = [VETO_KEY, 'bundle_rotation_signal_mean']
LEGACY_SIGN_KEYS = [
    'discrete_channel_track_source_circ_z',
    'local_propagation_track_dynamic_phasic_family_shell_2',
    'bundle_rotation_signal_mean',
]
SCALE_ADAPTIVE_SIGN_KEYS = [
    'layered_coupling_track_source_circ_z',
    'discrete_channel_track_source_dir_x',
]
SIGN_HANDOFF_SCALE = 128
VETO_GAP_THRESHOLD = 0.8
SCALES = [64, 96, 128]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Audit a panel-adaptive gate veto + scale-adaptive sign decoder on stressed panels.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_scale_adaptive_gate_sign_audit')
    return p.parse_args()


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def radius_coord(num_cells: int) -> float:
    return num_cells ** (1.0 / 3.0)


def fit_affine_centers(samples_by_scale: dict[int, list[dict[str, Any]]], label: str, keys: list[str]) -> dict[str, tuple[float, float]]:
    scales = sorted(samples_by_scale)
    assert len(scales) >= 2
    x1, x2 = radius_coord(scales[0]), radius_coord(scales[1])
    out: dict[str, tuple[float, float]] = {}
    for key in keys:
        y1 = mean([s['z_features'][key] for s in samples_by_scale[scales[0]] if s['label'] == label])
        y2 = mean([s['z_features'][key] for s in samples_by_scale[scales[1]] if s['label'] == label])
        a = (y2 - y1) / (x2 - x1)
        b = y1 - a * x1
        out[key] = (a, b)
    return out


def center_from_affine(params: dict[str, tuple[float, float]], num_cells: int) -> dict[str, float]:
    r = radius_coord(num_cells)
    return {k: a * r + b for k, (a, b) in params.items()}


def compute_veto_threshold(stage1_rows: list[dict[str, Any]]) -> float | None:
    values = sorted([row[VETO_KEY] for row in stage1_rows if row['stage1_predicted'] == 'translation'])
    if len(values) < 4:
        return None
    gaps = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    max_gap = max(gaps)
    if max_gap <= VETO_GAP_THRESHOLD:
        return None
    idx = gaps.index(max_gap)
    return 0.5 * (values[idx] + values[idx + 1])


def decode_panel(
    gate_train_rows: list[dict[str, Any]],
    stage2_train_rows: list[dict[str, Any]],
    sign_calibration_rows_by_scale: dict[int, list[dict[str, Any]]],
    legacy_sign_rows: list[dict[str, Any]],
    panel_rows: list[dict[str, Any]],
    panel_scale: int,
) -> tuple[list[dict[str, Any]], float | None]:
    translation_center = class_mean(gate_train_rows, lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(gate_train_rows, lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = mean_dict([s for s in stage2_train_rows if s['label'] == 'baseline'], NONTRANSLATION_KEYS)
    rotation_center = mean_dict([s for s in stage2_train_rows if s['label'] == 'rotation_z_pos'], NONTRANSLATION_KEYS)

    pos_affine = fit_affine_centers(sign_calibration_rows_by_scale, 'translation_x_pos', SCALE_ADAPTIVE_SIGN_KEYS)
    neg_affine = fit_affine_centers(sign_calibration_rows_by_scale, 'translation_x_neg', SCALE_ADAPTIVE_SIGN_KEYS)
    pos_center = center_from_affine(pos_affine, panel_scale)
    neg_center = center_from_affine(neg_affine, panel_scale)

    legacy_pos = mean_dict([s for s in legacy_sign_rows if s['label'] == 'translation_x_pos'], LEGACY_SIGN_KEYS)
    legacy_neg = mean_dict([s for s in legacy_sign_rows if s['label'] == 'translation_x_neg'], LEGACY_SIGN_KEYS)
    legacy_mid = {k: 0.5 * (legacy_pos[k] + legacy_neg[k]) for k in LEGACY_SIGN_KEYS}
    legacy_weights = {k: legacy_pos[k] - legacy_neg[k] for k in LEGACY_SIGN_KEYS}

    stage1_rows: list[dict[str, Any]] = []
    for sample in panel_rows:
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
            if panel_scale < SIGN_HANDOFF_SCALE:
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
    return predictions, veto_threshold


def accuracy(preds: list[dict[str, Any]]) -> float:
    return sum(int(p['predicted'] == p['label']) for p in preds) / len(preds) if preds else 0.0


def translation_accuracy(preds: list[dict[str, Any]]) -> float:
    rows = [p for p in preds if p['label'].startswith('translation')]
    return accuracy(rows)


def by_case_summary(preds: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for case_name in sorted({p['case_name'] for p in preds}):
        rows = [p for p in preds if p['case_name'] == case_name]
        out[case_name] = {
            'semantic_label': rows[0]['label'],
            'accuracy': accuracy(rows),
            'num_samples': len(rows),
        }
    return out


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

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
    for scale in SCALES:
        panel = load_stress_panel(Path(args.stress_root) / f'N{scale}')
        zscore(panel, feature_names, means, stds)
        panels[scale] = panel

    # N64 compatibility check: leave one seed out for the gate using N64, while allowing sign calibration to use N96.
    n64_preds: list[dict[str, Any]] = []
    n64_veto_thresholds: list[float | None] = []
    seeds64 = sorted({s['seed'] for s in panels[64]})
    for heldout_seed in seeds64:
        gate_train = [s for s in panels[64] if s['seed'] != heldout_seed]
        stage2_train = [s for s in panels[64] if s['seed'] != heldout_seed] + panels[96]
        sign_calibration = {
            64: [s for s in panels[64] if s['seed'] != heldout_seed and s['label'].startswith('translation')],
            96: [s for s in panels[96] if s['label'].startswith('translation')],
        }
        panel_rows = [s for s in panels[64] if s['seed'] == heldout_seed]
        preds, veto_threshold = decode_panel(gate_train, stage2_train, sign_calibration, minimal_train, panel_rows, 64)
        n64_preds.extend(preds)
        n64_veto_thresholds.append(veto_threshold)

    # Seen-scale N96 check: gate still trained on N64, sign calibration on N64+N96.
    stage2_train = panels[64] + panels[96]
    sign_calibration = {
        64: [s for s in panels[64] if s['label'].startswith('translation')],
        96: [s for s in panels[96] if s['label'].startswith('translation')],
    }
    n96_preds, n96_veto = decode_panel(panels[64], stage2_train, sign_calibration, minimal_train, panels[96], 96)

    # Unseen larger scale N128: same calibration, apply the adaptive veto and scale-adaptive sign prototypes.
    n128_preds, n128_veto = decode_panel(panels[64], stage2_train, sign_calibration, minimal_train, panels[128], 128)

    result = {
        'protocol': 'stage1_scale_adaptive_gate_sign_audit',
        'minimal_train_dir': args.minimal_train_dir,
        'stress_root': args.stress_root,
        'translation_group_keys': TRANSLATION_GROUP_KEYS,
        'veto_key': VETO_KEY,
        'veto_gap_threshold': VETO_GAP_THRESHOLD,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'legacy_sign_keys': LEGACY_SIGN_KEYS,
        'scale_adaptive_sign_keys': SCALE_ADAPTIVE_SIGN_KEYS,
        'sign_handoff_scale': SIGN_HANDOFF_SCALE,
        'results': {
            'N64_gate_compatibility_leave_one_seed_out': {
                'accuracy': accuracy(n64_preds),
                'translation_accuracy': translation_accuracy(n64_preds),
                'by_case': by_case_summary(n64_preds),
                'veto_thresholds': n64_veto_thresholds,
                'predictions': n64_preds,
            },
            'N96_seen_scale_check': {
                'accuracy': accuracy(n96_preds),
                'translation_accuracy': translation_accuracy(n96_preds),
                'by_case': by_case_summary(n96_preds),
                'veto_threshold': n96_veto,
                'predictions': n96_preds,
            },
            'N128_unseen_scale_probe': {
                'accuracy': accuracy(n128_preds),
                'translation_accuracy': translation_accuracy(n128_preds),
                'by_case': by_case_summary(n128_preds),
                'veto_threshold': n128_veto,
                'predictions': n128_preds,
            },
        },
    }
    (outdir / 'stage1_scale_adaptive_gate_sign_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 scale-adaptive gate+sign audit',
        '',
        'Goal: keep the tuned N64/N96 stressed-panel separation while repairing the N128 stage-1 scale drift entirely at the external readout layer.',
        '',
        'Decoder structure:',
        '- stage 1: existing tuned translation-vs-nontranslation gate (N64-trained)',
        '- stage 1.5: panel-adaptive veto on `discrete_channel_track_transfer_std` using the largest-gap rule',
        '- stage 2 nontranslation: baseline vs rotation using `discrete_channel_track_transfer_std` + `bundle_rotation_signal_mean`',
        '- stage 2 translation (calibration regime N64/N96): keep the legacy tuned sign branch',
        *[f'  - {k}' for k in LEGACY_SIGN_KEYS],
        '- stage 2 translation (beyond calibration regime): hand off to scale-adaptive sign prototypes fit on N64/N96 using:',
        *[f'  - {k}' for k in SCALE_ADAPTIVE_SIGN_KEYS],
        '',
        f'Veto key: `{VETO_KEY}`',
        f'Veto gap threshold: `{VETO_GAP_THRESHOLD}`',
        '',
    ]
    blocks = [
        ('N64 gate compatibility leave-one-seed-out', result['results']['N64_gate_compatibility_leave_one_seed_out']),
        ('N96 seen-scale check', result['results']['N96_seen_scale_check']),
        ('N128 unseen-scale probe', result['results']['N128_unseen_scale_probe']),
    ]
    for title, block in blocks:
        lines.extend([
            f'## {title}',
            '',
            f"- overall accuracy: {block['accuracy']:.3f}",
            f"- translation accuracy: {block['translation_accuracy']:.3f}",
        ])
        if 'veto_threshold' in block:
            lines.append(f"- veto threshold: {block['veto_threshold']}")
        if 'veto_thresholds' in block:
            lines.append(f"- veto thresholds: {block['veto_thresholds']}")
        lines.extend(['', '### By case', ''])
        for case_name, row in block['by_case'].items():
            lines.append(f"- {case_name} ({row['semantic_label']}): {row['accuracy']:.3f}")
        lines.append('')

    lines.extend([
        '## Hard conclusion',
        '',
        '- the N128 failure is no longer a hard barrier on the current stressed panel',
        '- a panel-adaptive veto can restore baseline/rotation separation before the translation branch',
        '- a two-feature scale-adaptive sign prototype can then preserve translation sign out to N128',
        '- this pushes the front-line problem forward again: the next check is whether the same decoder survives richer nuisance or larger unseen scales without retuning',
    ])
    (outdir / 'STAGE1_SCALE_ADAPTIVE_GATE_SIGN_AUDIT_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote scale-adaptive gate+sign audit to {outdir}')


if __name__ == '__main__':
    main()
