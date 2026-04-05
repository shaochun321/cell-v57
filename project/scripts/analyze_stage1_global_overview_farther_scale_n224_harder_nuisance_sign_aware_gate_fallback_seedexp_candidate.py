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
FIXED_NEG_OVER_POS_RATIO_THRESHOLD = 0.40240299738842616
FIXED_GATE_MARGIN_BRIDGE_THRESHOLD = 0.38450789102402827
PROFILES = ('early_soft', 'mid_sharp', 'late_balanced')
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
    p = argparse.ArgumentParser(description='Expand the N224 harder unseen-nuisance target seed set and evaluate the fixed v32 sign-aware gate fallback without changing thresholds or mainline structure.')
    p.add_argument('--panel-root', type=str, default='/mnt/data/v33_harder_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate')
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
                'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                'translation_distance': dt, 'nontranslation_distance': dnt,
                'gate_margin_translation_minus_nontranslation': gate_margin,
                'sign_distance_pos': dpos, 'sign_distance_neg': dneg,
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
                    and neg_over_pos <= FIXED_NEG_OVER_POS_RATIO_THRESHOLD
                    and gate_margin <= FIXED_GATE_MARGIN_BRIDGE_THRESHOLD
                )
                row['sign_aware_fallback_triggered'] = fallback
                if fallback:
                    pred = 'translation_x_neg'
                    activations.append({
                        'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
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
        'protocol': 'stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'carry forward the v32 sign-aware fallback unchanged into N224 harder unseen nuisance seed expansion: keep the overview-first mainline unchanged, keep the farther-scale bidirectional rotation separator unchanged, and keep the v32 sign-aware fallback thresholds fixed; no threshold reselection and no target-scale tuning',
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
            'neg_over_pos_sign_ratio_at_or_below': FIXED_NEG_OVER_POS_RATIO_THRESHOLD,
            'gate_margin_translation_minus_nontranslation_at_or_below': FIXED_GATE_MARGIN_BRIDGE_THRESHOLD,
            'sign_must_prefer': 'translation_x_neg',
            'threshold_source': 'carried forward unchanged from v32 standard seed-expansion sign-aware fallback candidate',
        },
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_sign_aware_fallback_triggered': seen_activations,
        'target_sign_aware_fallback_triggered': target_activations,
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': [p for p in target_eval['predictions'] if p['predicted'] != p['label']],
        'verdict': 'harder_nuisance_seed_expansion_stress_test',
        'interpretation': 'This audit asks whether the exact v32 sign-aware fallback still carries cleanly into the N224 harder unseen-nuisance panel when the target seed set is expanded to 7-12 without changing thresholds or mainline structure.',
    }
    (outdir / 'stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    remaining = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    lines = [
        '# Stage-1 farther-scale N224 harder unseen-nuisance sign-aware gate-fallback seed-expansion candidate',
        '',
        'This stress test keeps the **v32 sign-aware fallback unchanged** and broadens the N224 harder unseen-nuisance target seed set to `7,8,9,10,11,12`.',
        '',
        '## Selection discipline',
        '- keep the overview-first mainline unchanged',
        '- keep the farther-scale bidirectional rotation separator unchanged',
        '- keep the v32 sign-aware fallback thresholds unchanged',
        '- no target-scale tuning and no harder-panel reselection',
        '',
        '## Fixed fallback conditions',
        f'- stage2 class must be `baseline`',
        f'- curl must satisfy `{BIDIRECTIONAL_VETO_KEY} <= {FIXED_THRESHOLD:.15f}`',
        f'- neg/pos sign-distance ratio must satisfy `<= {FIXED_NEG_OVER_POS_RATIO_THRESHOLD:.15f}`',
        f'- gate margin `(translation_distance - nontranslation_distance)` must satisfy `<= {FIXED_GATE_MARGIN_BRIDGE_THRESHOLD:.15f}`',
        '- sign must prefer `translation_x_neg`',
        '',
        '## Results',
        f'- seen-scale overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen-scale translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N224 overall: `{target_eval["accuracy"]:.3f}`',
        f'- N224 translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Seen fallback activations',
    ]
    if seen_activations:
        for row in seen_activations:
            lines.append(f"- seen fallback triggered on `{row['case_name']}` at scale {row['scale']} seed {row['seed']}")
    else:
        lines.append('- none')
    lines.extend(['', '## Target fallback activations'])
    if target_activations:
        for row in target_activations:
            lines.append(
                f"- N224 seed {row['seed']} `{row['case_name']}` rescued from baseline to `translation_x_neg` "
                f"(gate margin={row['gate_margin_translation_minus_nontranslation']:.6f}, "
                f"neg/pos ratio={row['neg_over_pos_sign_ratio']:.6f}, curl={row['bidirectional_veto_feature']:.6f})"
            )
    else:
        lines.append('- none')
    lines.extend(['', '## Remaining target errors'])
    if remaining:
        for row in remaining:
            lines.append(f"- N224 seed {row['seed']} `{row['case_name']}`: predicted `{row['predicted']}` vs label `{row['label']}`")
    else:
        lines.append('- none')
    lines.extend([
        '',
        '## Interpretation',
        '- If the carried-forward fallback still triggers sparsely and leaves seen-scale behavior untouched, it behaves more like a controlled farther-scale recovery layer than a new patch stack.',
        '- If new errors or widespread activations appear under seed expansion, the fallback should not be promoted further and the route should pivot toward richer gate basis / trace-aware studies instead of threshold multiplication.',
    ])
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_HARDER_NUISANCE_SIGN_AWARE_GATE_FALLBACK_SEEDEXP_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
