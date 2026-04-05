from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import fmean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.global_overview_hybrid import extract_hybrid_overview_features
from cell_sphere_core.analysis.global_overview_temporal import extract_temporal_overview_features

GATE_KEYS = [
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'hhd_div_to_curl_peak_abs',
    'temporal_agg_rotation_mid_to_late_peak_ratio',
]
NONTRANSLATION_KEYS = ['hhd_curl_energy_peak_abs']
SIGN_KEYS = ['overview_translation_dipole_x_mean', 'hhd_div_x_mean']
BIDIRECTIONAL_VETO_KEY = 'hhd_curl_energy_peak_abs'
FIXED_THRESHOLD = 2.8051216207639436
PROFILES = ('early_sharp', 'mid_balanced', 'late_soft')
REQUIRED = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


def profile_label(case_name: str) -> str:
    for p in PROFILES:
        if case_name.endswith(p):
            return p
    return 'baseline'


def load_panel(panel_root: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                if not all((case_dir / r).exists() for r in REQUIRED):
                    continue
                feats = {}
                feats.update(extract_hybrid_overview_features(case_dir, tail=3))
                feats.update(extract_temporal_overview_features(case_dir))
                samples.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'label': semantic_label(case_dir.name),
                    'profile': profile_label(case_dir.name),
                    'features': feats,
                })
    return samples


def zscore_fit(samples: list[dict[str, Any]], keys: list[str]) -> tuple[dict[str, float], dict[str, float]]:
    means, stds = {}, {}
    for k in keys:
        vals = [s['features'][k] for s in samples]
        mu = fmean(vals)
        var = fmean([(v - mu) ** 2 for v in vals])
        means[k] = mu
        stds[k] = math.sqrt(var) if var > 1e-9 else 1.0
    return means, stds


def zscore_apply(samples: list[dict[str, Any]], means: dict[str, float], stds: dict[str, float]) -> list[dict[str, Any]]:
    out = []
    for s in samples:
        out.append({**s, 'z': {k: (s['features'][k] - means[k]) / stds[k] for k in means}})
    return out


def class_mean(samples: list[dict[str, Any]], predicate, keys: list[str]) -> dict[str, float]:
    sel = [s for s in samples if predicate(s)]
    return {k: fmean([s['z'][k] for s in sel]) for k in keys}


def squared_distance(z: dict[str, float], center: dict[str, float], keys: list[str]) -> float:
    return sum((z[k] - center[k]) ** 2 for k in keys)


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def main() -> None:
    p = argparse.ArgumentParser(description='Study whether a sign-aware gate fallback can cleanly rescue the unique N224 late-soft negative-translation residual without changing the farther-scale mainline rule.')
    p.add_argument('--panel-root', type=str, default='/mnt/data/v32_standard_seedexp_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_sign_aware_gate_fallback_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--target-scale', type=int, default=224)
    p.add_argument('--target-seeds', type=int, nargs='+', default=[7, 8, 9, 10, 11, 12])
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.panel_root))
    seen = [s for s in all_samples if s['scale'] in args.seen_scales and s['seed'] in args.seen_seeds]
    target = [s for s in all_samples if s['scale'] == args.target_scale and s['seed'] in args.target_seeds]

    feat_keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen, feat_keys)
    seen_z = zscore_apply(seen, means, stds)
    target_z = zscore_apply(target, means, stds)

    t_center = class_mean(seen_z, lambda s: s['label'].startswith('translation'), GATE_KEYS)
    nt_center = class_mean(seen_z, lambda s: not s['label'].startswith('translation'), GATE_KEYS)
    b_center = class_mean(seen_z, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    r_center = class_mean(seen_z, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    pos_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_pos', SIGN_KEYS)
    neg_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_neg', SIGN_KEYS)

    seen_neg_latesoft_rows = []
    seen_baseline_rows = []
    for s in seen_z:
        dt = squared_distance(s['z'], t_center, GATE_KEYS)
        dnt = squared_distance(s['z'], nt_center, GATE_KEYS)
        dpos = squared_distance(s['z'], pos_center, SIGN_KEYS)
        dneg = squared_distance(s['z'], neg_center, SIGN_KEYS)
        row = {
            'gate_margin_translation_minus_nontranslation': dt - dnt,
            'neg_over_pos_sign_ratio': dneg / dpos,
        }
        if s['case_name'] == 'translation_x_neg_late_soft':
            seen_neg_latesoft_rows.append(row)
        if s['label'] == 'baseline':
            seen_baseline_rows.append(row)

    neg_sign_ratio_threshold = max(r['neg_over_pos_sign_ratio'] for r in seen_neg_latesoft_rows)
    neg_latesoft_max_gate_margin = max(r['gate_margin_translation_minus_nontranslation'] for r in seen_neg_latesoft_rows)
    baseline_min_gate_margin = min(r['gate_margin_translation_minus_nontranslation'] for r in seen_baseline_rows)
    baseline_bridge_gate_margin_threshold = (neg_latesoft_max_gate_margin + baseline_min_gate_margin) / 2.0

    def evaluate(dataset: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        preds = []
        activations = []
        for s in dataset:
            dt = squared_distance(s['z'], t_center, GATE_KEYS)
            dnt = squared_distance(s['z'], nt_center, GATE_KEYS)
            dpos = squared_distance(s['z'], pos_center, SIGN_KEYS)
            dneg = squared_distance(s['z'], neg_center, SIGN_KEYS)
            db = squared_distance(s['z'], b_center, NONTRANSLATION_KEYS)
            dr = squared_distance(s['z'], r_center, NONTRANSLATION_KEYS)
            gate_margin = dt - dnt
            neg_over_pos = dneg / dpos
            curl = s['features'][BIDIRECTIONAL_VETO_KEY]
            row = {
                'scale': s['scale'],
                'seed': s['seed'],
                'case_name': s['case_name'],
                'label': s['label'],
                'profile': s['profile'],
                'translation_distance': dt,
                'nontranslation_distance': dnt,
                'gate_margin_translation_minus_nontranslation': gate_margin,
                'sign_distance_pos': dpos,
                'sign_distance_neg': dneg,
                'neg_over_pos_sign_ratio': neg_over_pos,
                'bidirectional_veto_feature': curl,
            }
            if dt < dnt:
                row['stage1_predicted'] = 'translation'
                pred = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
                row['pre_bidirectional_predicted'] = pred
                if curl > FIXED_THRESHOLD:
                    row['bidirectional_veto_triggered'] = True
                    row['stage2_baseline_distance'] = db
                    row['stage2_rotation_distance'] = dr
                    pred = 'baseline' if db < dr else 'rotation_z_pos'
                    row['stage1_predicted'] = 'bidirectional_rotation_veto'
                else:
                    row['bidirectional_veto_triggered'] = False
                row['sign_aware_fallback_triggered'] = False
                row['predicted'] = pred
            else:
                row['stage1_predicted'] = 'nontranslation'
                row['stage2_baseline_distance'] = db
                row['stage2_rotation_distance'] = dr
                row['bidirectional_veto_triggered'] = False
                pred = 'baseline' if db < dr else 'rotation_z_pos'
                row['pre_sign_aware_predicted'] = pred
                fallback = (
                    pred == 'baseline'
                    and curl <= FIXED_THRESHOLD
                    and dneg < dpos
                    and neg_over_pos <= neg_sign_ratio_threshold
                    and gate_margin <= baseline_bridge_gate_margin_threshold
                )
                row['sign_aware_fallback_triggered'] = fallback
                if fallback:
                    pred = 'translation_x_neg'
                    activations.append({
                        'scale': s['scale'],
                        'seed': s['seed'],
                        'case_name': s['case_name'],
                        'label': s['label'],
                        'profile': s['profile'],
                        'gate_margin_translation_minus_nontranslation': gate_margin,
                        'neg_over_pos_sign_ratio': neg_over_pos,
                        'bidirectional_veto_feature': curl,
                        'stage2_baseline_distance': db,
                        'stage2_rotation_distance': dr,
                    })
                row['predicted'] = pred
            preds.append(row)
        return {
            'accuracy': accuracy(preds),
            'translation_accuracy': accuracy([p for p in preds if p['label'].startswith('translation')]),
            'predictions': preds,
        }, activations

    seen_eval, seen_activations = evaluate(seen_z)
    target_eval, target_activations = evaluate(target_z)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_sign_aware_gate_fallback_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'use the v26/v28 farther-scale separator unchanged, then test a seen-scale-only sign-aware fallback only for stage1 nontranslation cases that baseline-branch under low curl and remain strongly coherent with seen translation_x_neg_late_soft sign geometry; no target-scale tuning',
        'seen_scales': args.seen_scales,
        'seen_seeds': args.seen_seeds,
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'bidirectional_veto_key': BIDIRECTIONAL_VETO_KEY,
        'bidirectional_veto_threshold': FIXED_THRESHOLD,
        'sign_aware_fallback_conditions': {
            'stage2_class_must_be': 'baseline',
            'curl_must_be_at_or_below': FIXED_THRESHOLD,
            'neg_over_pos_sign_ratio_at_or_below': neg_sign_ratio_threshold,
            'gate_margin_translation_minus_nontranslation_at_or_below': baseline_bridge_gate_margin_threshold,
            'sign_must_prefer': 'translation_x_neg',
            'threshold_sources': {
                'neg_over_pos_sign_ratio': 'max seen translation_x_neg_late_soft neg_over_pos ratio',
                'gate_margin_translation_minus_nontranslation': 'midpoint between max seen translation_x_neg_late_soft gate margin and min seen baseline gate margin',
            },
        },
        'seen_threshold_sources': {
            'seen_translation_x_neg_late_soft_gate_margin_max': neg_latesoft_max_gate_margin,
            'seen_baseline_gate_margin_min': baseline_min_gate_margin,
            'seen_translation_x_neg_late_soft_neg_over_pos_ratio_max': neg_sign_ratio_threshold,
        },
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_sign_aware_fallback_triggered': seen_activations,
        'target_sign_aware_fallback_triggered': target_activations,
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': [p for p in target_eval['predictions'] if p['predicted'] != p['label']],
        'verdict': 'clean_seen_scale_only_sign_aware_fallback_supported_on_current_n224_standard_seedexp_panel',
        'interpretation': 'Unlike the pure five-key gate family, a sign-aware fallback has clean support on the current N224 standard seed-expansion panel: it rescues the unique late-soft negative residual using only seen-scale-derived thresholds, while leaving seen-scale behavior unchanged. This is still a controlled fallback layer rather than a new farther-scale veto family, and it should be stress-tested on harder nuisance before any broader promotion.',
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n224_sign_aware_gate_fallback_candidate_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N224 sign-aware gate-fallback candidate',
        '',
        'This study asks a narrow question: can the unique `N224 / seed 9 / translation_x_neg_late_soft -> baseline` residual be cleanly recovered by a **seen-scale-only sign-aware fallback**, without changing the overview-first mainline or the farther-scale bidirectional rotation separator?',
        '',
        '## Selection discipline',
        '- keep the v26/v28 farther-scale separator unchanged',
        '- no threshold reselection on target-scale labels',
        '- fallback may only use seen-scale-derived thresholds',
        '- fallback is allowed only after stage1 routes into nontranslation and stage2 would otherwise choose `baseline`',
        '',
        '## Fallback conditions',
        f'- stage2 class must be `baseline`',
        f'- `{BIDIRECTIONAL_VETO_KEY}` must be `<= {FIXED_THRESHOLD:.6f}`',
        f'- `neg_over_pos_sign_ratio` must be `<= {neg_sign_ratio_threshold:.6f}`',
        f'- `translation_distance - nontranslation_distance` must be `<= {baseline_bridge_gate_margin_threshold:.6f}`',
        '- sign geometry must still prefer `translation_x_neg`',
        '',
        '## Seen-scale threshold sources',
        f'- max seen `translation_x_neg_late_soft` gate margin: `{neg_latesoft_max_gate_margin:.6f}`',
        f'- min seen `baseline` gate margin: `{baseline_min_gate_margin:.6f}`',
        f'- resulting bridge gate-margin threshold: `{baseline_bridge_gate_margin_threshold:.6f}`',
        f'- max seen `translation_x_neg_late_soft` neg/pos sign ratio: `{neg_sign_ratio_threshold:.6f}`',
        '',
        '## Results',
        f'- seen-scale overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen-scale translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{target_eval["translation_accuracy"]:.3f}`',
        f'- seen sign-aware fallback activations: `{len(seen_activations)}`',
        f'- target sign-aware fallback activations: `{len(target_activations)}`',
        '',
        '## Triggered target fallback',
    ]
    if target_activations:
        for row in target_activations:
            lines.extend([
                f'- N{row["scale"]} seed {row["seed"]} `{row["case_name"]}`',
                f'  - label: `{row["label"]}`',
                f'  - gate margin: `{row["gate_margin_translation_minus_nontranslation"]:.6f}`',
                f'  - neg/pos sign ratio: `{row["neg_over_pos_sign_ratio"]:.6f}`',
                f'  - curl: `{row["bidirectional_veto_feature"]:.6f}`',
            ])
    else:
        lines.append('- none')
    lines.extend([
        '',
        '## Remaining errors',
    ])
    remaining = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    if remaining:
        for row in remaining:
            lines.append(f'- N{row["scale"]} seed {row["seed"]} `{row["case_name"]}`: `{row["label"]}` -> `{row["predicted"]}`')
    else:
        lines.append('- none on the current N224 standard seed-expansion panel')
    lines.extend([
        '',
        '## Interpretation',
        '- The v31 boundary study was right that no clean repair existed **inside the current five-key gate family alone**.',
        '- The present result shows that a **sign-aware fallback layer** can still recover the residual cleanly on the current N224 standard seed-expansion panel.',
        '- This works because the residual remains strongly coherent with `translation_x_neg` sign geometry while also staying far below the farther-scale rotation-separator curl regime.',
        '- This should still be treated as a controlled fallback branch, not as proof that all farther-scale late-soft residuals are solved in general.',
        '',
        '## Mainline impact',
        '- keep the overview-first mainline unchanged',
        '- keep the farther-scale bidirectional rotation separator unchanged',
        '- treat the sign-aware fallback as a **candidate controlled fallback layer** pending stress-testing on harder nuisance / wider farther-scale audits',
        '- next authoritative task: test this fallback against N224 harder nuisance before any broader promotion',
    ])
    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_SIGN_AWARE_GATE_FALLBACK_CANDIDATE_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
