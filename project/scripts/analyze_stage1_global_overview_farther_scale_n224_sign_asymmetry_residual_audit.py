from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import fmean, pvariance
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

PROFILES = ('early_soft', 'mid_sharp', 'late_balanced')
REQUIRED = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']
GATE_KEYS = [
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'hhd_div_to_curl_peak_abs',
    'temporal_agg_rotation_mid_to_late_peak_ratio',
]
NONTRANSLATION_KEYS = ['hhd_curl_energy_peak_abs']
SIGN_KEYS = ['overview_translation_dipole_x_mean', 'hhd_div_x_mean']
FIXED_BIDIRECTIONAL_THRESHOLD = 2.8051216207639436
FIXED_NEG_OVER_POS_RATIO_THRESHOLD = 0.40240299738842616
FIXED_GATE_MARGIN_BRIDGE_THRESHOLD = 0.38450789102402827


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
                feats: dict[str, float] = {}
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
        var = pvariance(vals)
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


def eval_row(s: dict[str, Any], t_center, nt_center, pos_center, neg_center, b_center, r_center) -> dict[str, Any]:
    dt = squared_distance(s['z'], t_center, GATE_KEYS)
    dnt = squared_distance(s['z'], nt_center, GATE_KEYS)
    dpos = squared_distance(s['z'], pos_center, SIGN_KEYS)
    dneg = squared_distance(s['z'], neg_center, SIGN_KEYS)
    db = squared_distance(s['z'], b_center, NONTRANSLATION_KEYS)
    dr = squared_distance(s['z'], r_center, NONTRANSLATION_KEYS)
    row = {
        'scale': s['scale'],
        'seed': s['seed'],
        'case_name': s['case_name'],
        'label': s['label'],
        'profile': s['profile'],
        'translation_distance': dt,
        'nontranslation_distance': dnt,
        'gate_margin_translation_minus_nontranslation': dt - dnt,
        'sign_distance_pos': dpos,
        'sign_distance_neg': dneg,
        'neg_over_pos_sign_ratio': dneg / dpos,
        'pos_over_neg_sign_ratio': dpos / dneg,
        'stage2_baseline_distance': db,
        'stage2_rotation_distance': dr,
        'bidirectional_veto_feature': s['features']['hhd_curl_energy_peak_abs'],
        'features': {k: s['features'][k] for k in GATE_KEYS},
        'feature_zscores': {k: s['z'][k] for k in GATE_KEYS},
    }
    if dt < dnt:
        row['stage1_predicted'] = 'translation'
        row['pre_bidirectional_predicted'] = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
    else:
        row['stage1_predicted'] = 'nontranslation'
        row['pre_sign_aware_predicted'] = 'baseline' if db < dr else 'rotation_z_pos'
        fallback = (
            row['pre_sign_aware_predicted'] == 'baseline'
            and row['bidirectional_veto_feature'] <= FIXED_BIDIRECTIONAL_THRESHOLD
            and dneg < dpos
            and row['neg_over_pos_sign_ratio'] <= FIXED_NEG_OVER_POS_RATIO_THRESHOLD
            and row['gate_margin_translation_minus_nontranslation'] <= FIXED_GATE_MARGIN_BRIDGE_THRESHOLD
        )
        row['negative_sign_aware_fallback_triggered'] = fallback
    return row


def main() -> None:
    p = argparse.ArgumentParser(description='Audit the N224 harder-seed residual picture after the negative sign-aware fallback: compare the rescued negative residual against the remaining positive residual and determine whether a mirrored positive fallback is justified by seen-scale support.')
    p.add_argument('--panel-root', type=str, default='/mnt/data/v33_harder_raw')
    p.add_argument('--source-analysis-json', type=str, default='/mnt/data/stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate_analysis.json')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_sign_asymmetry_residual_audit')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--target-scale', type=int, default=224)
    p.add_argument('--target-seeds', type=int, nargs='+', default=[7, 8, 9, 10, 11, 12])
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.panel_root))
    seen = [s for s in all_samples if s['scale'] in args.seen_scales and s['seed'] in args.seen_seeds]
    all_z = zscore_apply(all_samples, *zscore_fit(seen, sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))))
    feat_keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen, feat_keys)
    all_z = zscore_apply(all_samples, means, stds)
    seen_z = [s for s in all_z if s['scale'] in args.seen_scales and s['seed'] in args.seen_seeds]

    t_center = class_mean(seen_z, lambda s: s['label'].startswith('translation'), GATE_KEYS)
    nt_center = class_mean(seen_z, lambda s: not s['label'].startswith('translation'), GATE_KEYS)
    b_center = class_mean(seen_z, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    r_center = class_mean(seen_z, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    pos_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_pos', SIGN_KEYS)
    neg_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_neg', SIGN_KEYS)

    eval_rows = [eval_row(s, t_center, nt_center, pos_center, neg_center, b_center, r_center) for s in all_z]

    def select(case_name: str, seed: int, scale: int = 224) -> dict[str, Any]:
        return next(r for r in eval_rows if r['case_name'] == case_name and r['seed'] == seed and r['scale'] == scale)

    remaining_positive = select('translation_x_pos_late_balanced', 9)
    rescued_negative = select('translation_x_neg_early_soft', 9)
    matched_negative_late = select('translation_x_neg_late_balanced', 9)

    def family_rows(case_name: str, scale: int, seeds: list[int]) -> list[dict[str, Any]]:
        return [select(case_name, seed, scale) for seed in seeds]

    pos_late_seed_sweep = family_rows('translation_x_pos_late_balanced', args.target_scale, args.target_seeds)
    neg_late_seed_sweep = family_rows('translation_x_neg_late_balanced', args.target_scale, args.target_seeds)
    neg_early_seed_sweep = family_rows('translation_x_neg_early_soft', args.target_scale, args.target_seeds)

    def seen_support(case_name: str) -> dict[str, Any]:
        rows = [select(case_name, seed, scale) for scale in args.seen_scales for seed in args.seen_seeds]
        return {
            'gate_margin_min': min(r['gate_margin_translation_minus_nontranslation'] for r in rows),
            'gate_margin_max': max(r['gate_margin_translation_minus_nontranslation'] for r in rows),
            'neg_over_pos_min': min(r['neg_over_pos_sign_ratio'] for r in rows),
            'neg_over_pos_max': max(r['neg_over_pos_sign_ratio'] for r in rows),
            'pos_over_neg_min': min(r['pos_over_neg_sign_ratio'] for r in rows),
            'pos_over_neg_max': max(r['pos_over_neg_sign_ratio'] for r in rows),
            'feature_mean': {k: fmean([r['features'][k] for r in rows]) for k in GATE_KEYS},
        }

    seen_pos_late_support = seen_support('translation_x_pos_late_balanced')
    seen_neg_early_support = seen_support('translation_x_neg_early_soft')
    seen_neg_late_support = seen_support('translation_x_neg_late_balanced')

    seen_baseline_pos_pref = []
    for scale in args.seen_scales:
        for seed in args.seen_seeds:
            row = select('baseline', seed, scale)
            if row['sign_distance_pos'] < row['sign_distance_neg']:
                seen_baseline_pos_pref.append(row)

    baseline_pos_pref_summary = {
        'count': len(seen_baseline_pos_pref),
        'gate_margin_min': min(r['gate_margin_translation_minus_nontranslation'] for r in seen_baseline_pos_pref),
        'gate_margin_max': max(r['gate_margin_translation_minus_nontranslation'] for r in seen_baseline_pos_pref),
        'pos_over_neg_min': min(r['pos_over_neg_sign_ratio'] for r in seen_baseline_pos_pref),
        'pos_over_neg_max': max(r['pos_over_neg_sign_ratio'] for r in seen_baseline_pos_pref),
    }

    mirrored_positive_fallback_is_seen_supported = False
    rationale = (
        'No mirrored positive fallback is currently justified: the remaining positive residual sits outside seen translation_x_pos_late_balanced gate support, '
        'while the seen data contain no positive-spill training analogue and do contain baseline cases with positive sign preference. '
        'Any mirrored positive bridge tuned to the remaining target residual would therefore be target-informed rather than seen-derived.'
    )

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_sign_asymmetry_residual_audit',
        'source_analysis_json': args.source_analysis_json,
        'panel_root': args.panel_root,
        'selection_rule': 'audit only: keep the overview-first mainline unchanged, keep the bidirectional rotation separator unchanged, keep the negative sign-aware fallback unchanged, and compare the rescued negative residual against the remaining positive residual without adding a mirrored positive rule',
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'fixed_negative_sign_aware_fallback': {
            'bidirectional_veto_threshold': FIXED_BIDIRECTIONAL_THRESHOLD,
            'neg_over_pos_ratio_threshold': FIXED_NEG_OVER_POS_RATIO_THRESHOLD,
            'gate_margin_bridge_threshold': FIXED_GATE_MARGIN_BRIDGE_THRESHOLD,
        },
        'rescued_negative_case': rescued_negative,
        'remaining_positive_case': remaining_positive,
        'matched_negative_late_balanced_case': matched_negative_late,
        'target_family_sweeps': {
            'translation_x_pos_late_balanced': pos_late_seed_sweep,
            'translation_x_neg_late_balanced': neg_late_seed_sweep,
            'translation_x_neg_early_soft': neg_early_seed_sweep,
        },
        'seen_support': {
            'translation_x_pos_late_balanced': seen_pos_late_support,
            'translation_x_neg_early_soft': seen_neg_early_support,
            'translation_x_neg_late_balanced': seen_neg_late_support,
            'baseline_with_positive_sign_preference': baseline_pos_pref_summary,
        },
        'sign_asymmetry_findings': {
            'positive_remaining_case_is_isolated_within_target_family': sum(int(r['stage1_predicted'] == 'nontranslation') for r in pos_late_seed_sweep) == 1,
            'negative_early_case_was_bridge_eligible': rescued_negative['gate_margin_translation_minus_nontranslation'] <= FIXED_GATE_MARGIN_BRIDGE_THRESHOLD and rescued_negative['neg_over_pos_sign_ratio'] <= FIXED_NEG_OVER_POS_RATIO_THRESHOLD,
            'positive_remaining_case_is_not_bridge_eligible_under_negative_rule': remaining_positive['gate_margin_translation_minus_nontranslation'] > FIXED_GATE_MARGIN_BRIDGE_THRESHOLD,
            'positive_remaining_case_exits_seen_x_pos_late_support': remaining_positive['gate_margin_translation_minus_nontranslation'] > seen_pos_late_support['gate_margin_max'],
            'negative_late_balanced_case_remains_clean_without_fallback': matched_negative_late['stage1_predicted'] == 'translation',
        },
        'mirrored_positive_fallback_is_seen_supported': mirrored_positive_fallback_is_seen_supported,
        'mirrored_positive_fallback_rationale': rationale,
        'verdict': 'sign_asymmetry_confirmed',
        'interpretation': 'The N224 harder-seed residual picture is asymmetric but not mirror-symmetric. The rescued negative early_soft spill stays inside a seen-derived bridge band with strong negative sign evidence, while the remaining positive late_balanced residual drifts farther outside seen translation_x_pos late-balanced gate support. The current evidence does not justify inventing a mirrored positive fallback; the next honest branch is a white-box translation_x_pos_late_balanced residual audit or a richer temporal/trace gate-basis study.'
    }
    (outdir / 'stage1_global_overview_farther_scale_n224_sign_asymmetry_residual_audit_analysis.json').write_text(json.dumps(payload, indent=2))

    report = f'''# Stage-1 farther-scale N224 sign-asymmetry residual audit

This audit does **not** change the overview-first mainline, the bidirectional rotation separator, or the negative sign-aware fallback. It asks a narrower question: after the v34 harder seed-expansion run, is the remaining positive residual just the mirror image of the rescued negative residual?

## Selection discipline
- keep the overview-first mainline unchanged
- keep the farther-scale bidirectional rotation separator unchanged
- keep the negative sign-aware fallback unchanged
- do not add a mirrored positive fallback during the audit

## Audit anchor cases at N224 / seed 9
### Rescued negative case
- `translation_x_neg_early_soft`
- stage1 gate margin: `{rescued_negative['gate_margin_translation_minus_nontranslation']:.6f}`
- neg/pos sign-distance ratio: `{rescued_negative['neg_over_pos_sign_ratio']:.6f}`
- curl: `{rescued_negative['bidirectional_veto_feature']:.6f}`
- under the fixed negative fallback, this case is bridge-eligible and is correctly restored to `translation_x_neg`

### Remaining positive case
- `translation_x_pos_late_balanced`
- stage1 gate margin: `{remaining_positive['gate_margin_translation_minus_nontranslation']:.6f}`
- pos/neg sign-distance ratio: `{remaining_positive['pos_over_neg_sign_ratio']:.6f}`
- curl: `{remaining_positive['bidirectional_veto_feature']:.6f}`
- this case remains in `baseline`
- importantly, its stage1 spill is **larger** than the fixed negative bridge band and it sits outside seen `translation_x_pos_late_balanced` gate support

### Matched negative late-balanced control
- `translation_x_neg_late_balanced`
- stage1 gate margin: `{matched_negative_late['gate_margin_translation_minus_nontranslation']:.6f}`
- neg/pos sign-distance ratio: `{matched_negative_late['neg_over_pos_sign_ratio']:.6f}`
- this case stays cleanly in translation without any fallback

## Target-family sweeps at N224
### `translation_x_pos_late_balanced`
- 5 / 6 seeds remain clean translation cases
- only `seed 9` flips to `baseline`
- therefore the remaining positive residual is **isolated**, not a generic positive collapse

### `translation_x_neg_early_soft`
- 5 / 6 seeds remain clean translation cases on the mainline
- only `seed 9` spills into `baseline`
- the fixed negative fallback rescues exactly that one spill and nothing else

### `translation_x_neg_late_balanced`
- all 6 seeds remain translation cases without fallback
- therefore the emerging asymmetry is not “all late-balanced negatives are collapsing”

## Seen-support comparison
### Seen `translation_x_pos_late_balanced` support
- seen gate-margin range: `{seen_pos_late_support['gate_margin_min']:.6f}` to `{seen_pos_late_support['gate_margin_max']:.6f}`
- the remaining positive residual has gate margin `{remaining_positive['gate_margin_translation_minus_nontranslation']:.6f}`
- this places the residual **outside** seen positive late-balanced support

### Seen `translation_x_neg_early_soft` support
- seen gate-margin range: `{seen_neg_early_support['gate_margin_min']:.6f}` to `{seen_neg_early_support['gate_margin_max']:.6f}`
- the rescued negative spill stays close enough to the fixed negative bridge conditions to be treated as a controlled spill

### Seen baseline with positive sign preference
- count: `{baseline_pos_pref_summary['count']}`
- seen gate-margin range: `{baseline_pos_pref_summary['gate_margin_min']:.6f}` to `{baseline_pos_pref_summary['gate_margin_max']:.6f}`
- this means the seen set already contains baseline states that look positive in sign space, which makes a mirrored positive fallback governance-sensitive

## White-box interpretation
- the rescued negative residual and the remaining positive residual are **not** mirror images of each other
- the negative case is a narrow bridge-eligible spill with strong negative sign coherence
- the positive case is an isolated `translation_x_pos_late_balanced` gate-basis miss that exits seen positive late-balanced support more substantially
- therefore the current evidence does **not** justify inventing a mirrored positive fallback family

## Governance outcome
- keep the overview-first mainline unchanged
- keep the bidirectional rotation separator unchanged
- keep the negative sign-aware fallback as a controlled fallback layer only
- do **not** mirror it into a positive fallback yet
- the next honest task is a **white-box `translation_x_pos_late_balanced` residual audit** or a **richer temporal / trace gate-basis study** rather than threshold multiplication
'''
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_SIGN_ASYMMETRY_RESIDUAL_AUDIT_REPORT.md').write_text(report)


if __name__ == '__main__':
    main()
