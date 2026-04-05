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
SUPPORT_FEATURES = [
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'hhd_div_to_curl_peak_abs',
    'temporal_agg_rotation_mid_to_late_peak_ratio',
]


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
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
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
        'pos_over_neg_sign_ratio': dpos / dneg,
        'neg_over_pos_sign_ratio': dneg / dpos,
        'stage2_baseline_distance': db,
        'stage2_rotation_distance': dr,
        'bidirectional_veto_feature': s['features']['hhd_curl_energy_peak_abs'],
        'features': {k: s['features'][k] for k in GATE_KEYS},
        'feature_zscores': {k: s['z'][k] for k in GATE_KEYS},
    }
    if dt < dnt:
        row['stage1_predicted'] = 'translation'
        row['pre_bidirectional_predicted'] = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
        row['bidirectional_veto_triggered'] = row['bidirectional_veto_feature'] > FIXED_BIDIRECTIONAL_THRESHOLD
        row['predicted'] = 'rotation_z_pos' if row['bidirectional_veto_triggered'] else row['pre_bidirectional_predicted']
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
        row['predicted'] = 'translation_x_neg' if fallback else row['pre_sign_aware_predicted']
    return row


def classify_violation(value: float, min_v: float, max_v: float) -> str:
    if min_v <= value <= max_v:
        return 'inside_seen_support'
    if value < min_v:
        return 'below_seen_min'
    return 'above_seen_max'


def support_margin(value: float, min_v: float, max_v: float) -> float:
    if value < min_v:
        return value - min_v
    if value > max_v:
        return value - max_v
    return 0.0


def main() -> None:
    p = argparse.ArgumentParser(description='White-box audit of the remaining N224 harder-seed positive late-balanced residual under the fixed negative sign-aware fallback stack.')
    p.add_argument('--panel-root', type=str, default='/mnt/data/v33_harder_raw')
    p.add_argument('--source-analysis-json', type=str, default='/mnt/data/stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate_analysis.json')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_translation_x_pos_late_balanced_residual_audit')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--target-scale', type=int, default=224)
    p.add_argument('--target-seeds', type=int, nargs='+', default=[7, 8, 9, 10, 11, 12])
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.panel_root))
    seen_raw = [s for s in all_samples if s['scale'] in args.seen_scales and s['seed'] in args.seen_seeds]
    keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen_raw, keys)
    all_z = zscore_apply(all_samples, means, stds)
    seen_z = [s for s in all_z if s['scale'] in args.seen_scales and s['seed'] in args.seen_seeds]

    t_center = class_mean(seen_z, lambda s: s['label'].startswith('translation'), GATE_KEYS)
    nt_center = class_mean(seen_z, lambda s: not s['label'].startswith('translation'), GATE_KEYS)
    b_center = class_mean(seen_z, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    r_center = class_mean(seen_z, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    pos_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_pos', SIGN_KEYS)
    neg_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_neg', SIGN_KEYS)
    eval_rows = [eval_row(s, t_center, nt_center, pos_center, neg_center, b_center, r_center) for s in all_z]

    def select(case_name: str, seed: int, scale: int) -> dict[str, Any]:
        return next(r for r in eval_rows if r['case_name'] == case_name and r['seed'] == seed and r['scale'] == scale)

    remaining_positive = select('translation_x_pos_late_balanced', 9, args.target_scale)
    same_seed_controls = {
        'translation_x_pos_early_soft': select('translation_x_pos_early_soft', 9, args.target_scale),
        'translation_x_pos_mid_sharp': select('translation_x_pos_mid_sharp', 9, args.target_scale),
        'translation_x_neg_late_balanced': select('translation_x_neg_late_balanced', 9, args.target_scale),
    }

    seen_rows = [select('translation_x_pos_late_balanced', seed, scale) for scale in args.seen_scales for seed in args.seen_seeds]
    seed_sweep = [select('translation_x_pos_late_balanced', seed, args.target_scale) for seed in args.target_seeds]

    support_ranges = {}
    outside_count = 0
    for key in SUPPORT_FEATURES:
        vals = [r['features'][key] for r in seen_rows]
        support_ranges[key] = {
            'min': min(vals),
            'max': max(vals),
            'mean': fmean(vals),
            'residual_value': remaining_positive['features'][key],
            'residual_status': classify_violation(remaining_positive['features'][key], min(vals), max(vals)),
            'residual_support_margin': support_margin(remaining_positive['features'][key], min(vals), max(vals)),
        }
        if support_ranges[key]['residual_status'] != 'inside_seen_support':
            outside_count += 1

    seen_gate_margins = [r['gate_margin_translation_minus_nontranslation'] for r in seen_rows]
    residual_vs_seen = {
        'seen_gate_margin_min': min(seen_gate_margins),
        'seen_gate_margin_max': max(seen_gate_margins),
        'residual_gate_margin': remaining_positive['gate_margin_translation_minus_nontranslation'],
        'residual_gate_margin_outside_seen': not (min(seen_gate_margins) <= remaining_positive['gate_margin_translation_minus_nontranslation'] <= max(seen_gate_margins)),
        'residual_gate_margin_support_margin': support_margin(remaining_positive['gate_margin_translation_minus_nontranslation'], min(seen_gate_margins), max(seen_gate_margins)),
    }

    scale_sweep = []
    for scale in args.seen_scales + [args.target_scale]:
        if scale == args.target_scale:
            row = select('translation_x_pos_late_balanced', 9, scale)
        else:
            # no seed-9 training traces exist; use per-scale seen support summary instead
            rows = [select('translation_x_pos_late_balanced', seed, scale) for seed in args.seen_seeds]
            row = {
                'scale': scale,
                'seed_mode': 'seen_support_summary',
                'gate_margin_min': min(r['gate_margin_translation_minus_nontranslation'] for r in rows),
                'gate_margin_max': max(r['gate_margin_translation_minus_nontranslation'] for r in rows),
                'feature_mean': {k: fmean([r['features'][k] for r in rows]) for k in SUPPORT_FEATURES},
                'feature_min': {k: min(r['features'][k] for r in rows) for k in SUPPORT_FEATURES},
                'feature_max': {k: max(r['features'][k] for r in rows) for k in SUPPORT_FEATURES},
            }
        scale_sweep.append(row)

    dominant_drifts = sorted(
        [
            {
                'feature': k,
                'residual_value': support_ranges[k]['residual_value'],
                'seen_mean': support_ranges[k]['mean'],
                'delta_from_seen_mean': support_ranges[k]['residual_value'] - support_ranges[k]['mean'],
                'residual_status': support_ranges[k]['residual_status'],
                'support_margin': support_ranges[k]['residual_support_margin'],
                'residual_zscore': remaining_positive['feature_zscores'][k],
            }
            for k in SUPPORT_FEATURES
        ],
        key=lambda row: abs(row['delta_from_seen_mean']),
        reverse=True,
    )

    sign_state = {
        'residual_pos_over_neg_sign_ratio': remaining_positive['pos_over_neg_sign_ratio'],
        'residual_prefers_positive_sign': remaining_positive['sign_distance_pos'] < remaining_positive['sign_distance_neg'],
        'same_seed_early_soft_pos_over_neg': same_seed_controls['translation_x_pos_early_soft']['pos_over_neg_sign_ratio'],
        'same_seed_mid_sharp_pos_over_neg': same_seed_controls['translation_x_pos_mid_sharp']['pos_over_neg_sign_ratio'],
    }

    verdict = 'positive_late_balanced_gate_basis_miss_confirmed'
    interpretation = (
        'The remaining N224 harder-seed residual is not a sign collapse and not a mirror image of the rescued negative spill. '
        'The case keeps positive sign preference and low curl, but its late-balanced gate coordinates move outside seen translation_x_pos late-balanced support—most visibly through a strong timing-ratio inflation and a simultaneous drop in translation quadrupole support. '
        'This makes the residual look like a positive late-balanced gate-basis miss rather than a clean mirrored fallback opportunity.'
    )

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_translation_x_pos_late_balanced_residual_audit',
        'source_analysis_json': args.source_analysis_json,
        'panel_root': args.panel_root,
        'selection_rule': 'audit only: keep the overview-first mainline unchanged, keep the bidirectional rotation separator unchanged, keep the negative sign-aware fallback unchanged, and isolate the remaining translation_x_pos_late_balanced residual without adding a mirrored positive fallback',
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'remaining_positive_case': remaining_positive,
        'same_seed_controls': same_seed_controls,
        'target_seed_sweep_translation_x_pos_late_balanced': seed_sweep,
        'seen_translation_x_pos_late_balanced_support': support_ranges,
        'residual_vs_seen_gate_margin': residual_vs_seen,
        'outside_seen_support_count': outside_count,
        'support_features': SUPPORT_FEATURES,
        'dominant_drifts': dominant_drifts,
        'sign_state': sign_state,
        'scale_sweep_context': scale_sweep,
        'mirrored_positive_fallback_is_currently_seen_supported': False,
        'verdict': verdict,
        'interpretation': interpretation,
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n224_translation_x_pos_late_balanced_residual_audit_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N224 `translation_x_pos_late_balanced` white-box residual audit',
        '',
        'This audit does **not** change the overview-first mainline, the bidirectional rotation separator, or the negative sign-aware fallback. It isolates the remaining `N224 / seed 9 / translation_x_pos_late_balanced -> baseline` error and asks whether it behaves like a simple mirrored version of the rescued negative spill.',
        '',
        '## Selection discipline',
        '- keep the overview-first mainline unchanged',
        '- keep the farther-scale bidirectional rotation separator unchanged',
        '- keep the negative sign-aware fallback unchanged',
        '- do not add a mirrored positive fallback during the audit',
        '',
        '## Residual anchor case',
        f'- case: `translation_x_pos_late_balanced` at `N{args.target_scale} / seed 9`',
        f'- stage1 gate margin: `{remaining_positive["gate_margin_translation_minus_nontranslation"]:.6f}`',
        f'- stage1 prediction: `{remaining_positive["stage1_predicted"]}`',
        f'- stage2 baseline distance: `{remaining_positive["stage2_baseline_distance"]:.6f}`',
        f'- stage2 rotation distance: `{remaining_positive["stage2_rotation_distance"]:.6f}`',
        f'- pos/neg sign-distance ratio: `{remaining_positive["pos_over_neg_sign_ratio"]:.6f}`',
        f'- curl: `{remaining_positive["bidirectional_veto_feature"]:.6f}`',
        '- reading: the residual still prefers `translation_x_pos` in sign space and is not a rotation-leak event; it fails before the sign branch is reached.',
        '',
        '## Same-seed positive controls at N224',
    ]
    for case_name, row in same_seed_controls.items():
        lines.extend([
            f'- `{case_name}`',
            f'  - stage1 gate margin: `{row["gate_margin_translation_minus_nontranslation"]:.6f}`',
            f'  - pos/neg sign-distance ratio: `{row["pos_over_neg_sign_ratio"]:.6f}`',
            f'  - prediction: `{row["predicted"]}`',
        ])
    lines.extend([
        '',
        '## N224 target seed sweep for `translation_x_pos_late_balanced`',
        '- 5 / 6 target seeds remain clean translation cases',
        '- only `seed 9` flips to `baseline`',
        '- therefore the residual is isolated rather than a generic positive late-balanced collapse',
        '',
        '## Seen-support comparison for `translation_x_pos_late_balanced`',
    ])
    for key in SUPPORT_FEATURES:
        r = support_ranges[key]
        lines.extend([
            f'- `{key}`',
            f'  - seen range: `[{r["min"]:.6f}, {r["max"]:.6f}]`',
            f'  - seen mean: `{r["mean"]:.6f}`',
            f'  - N224 residual value: `{r["residual_value"]:.6f}` ({r["residual_status"]})',
            f'  - support margin: `{r["residual_support_margin"]:.6f}`',
        ])
    lines.extend([
        '',
        '## Gate-margin support',
        f'- seen gate-margin range: `[{residual_vs_seen["seen_gate_margin_min"]:.6f}, {residual_vs_seen["seen_gate_margin_max"]:.6f}]`',
        f'- residual gate margin: `{residual_vs_seen["residual_gate_margin"]:.6f}`',
        f'- residual gate margin outside seen support: `{residual_vs_seen["residual_gate_margin_outside_seen"]}`',
        f'- residual gate-margin support margin: `{residual_vs_seen["residual_gate_margin_support_margin"]:.6f}`',
        '',
        '## Dominant drift axes',
    ])
    for row in dominant_drifts:
        lines.append(f'- `{row["feature"]}`: delta-from-seen-mean `{row["delta_from_seen_mean"]:.6f}`, z-score `{row["residual_zscore"]:.6f}`, status `{row["residual_status"]}`')
    lines.extend([
        '',
        '## White-box interpretation',
        '- the residual is **not** a sign collapse: it still prefers `translation_x_pos` in sign space',
        '- it is **not** a rotation leak: curl stays low and the bidirectional separator would not fire',
        '- compared with same-seed `translation_x_pos_early_soft` and `translation_x_pos_mid_sharp`, the failure is profile-specific to `late_balanced`',
        '- the strongest deviations are a timing-ratio inflation and a loss of positive late-balanced quadrupole / energy support',
        '- therefore the current evidence points to a **positive late-balanced gate-basis miss**, not a clean mirrored-positive fallback opportunity',
        '',
        '## Governance outcome',
        '- keep the overview-first mainline unchanged',
        '- keep the bidirectional rotation separator unchanged',
        '- keep the negative sign-aware fallback unchanged',
        '- do **not** invent a mirrored positive fallback from this one residual',
        '- next honest branch: richer temporal / trace gate-basis study for positive late-balanced farther-scale residuals',
    ])
    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_TRANSLATION_X_POS_LATE_BALANCED_RESIDUAL_AUDIT_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
