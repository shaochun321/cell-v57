from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

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
FIXED_SEPARATOR_THRESHOLD = 2.8051216207639436
FIXED_NEG_OVER_POS_RATIO_THRESHOLD = 0.40240299738842616
FIXED_NEG_GATE_MARGIN_THRESHOLD = 0.38450789102402827
TRANSLATION_MARGIN_GUARD_THRESHOLD = -2.5
POSITIVE_TRACE_FEATURE = 'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.dynamic_phasic_family.mean_centroid_shell_index'
POSITIVE_TRACE_THRESHOLD = 1.3508873633981915
POSITIVE_TRACE_DIRECTION = 'high'
BASELINE_SUPPORT_THRESHOLD = 0.6521918153113626
PROFILES = ('early_soft', 'mid_sharp', 'late_balanced')
REQUIRED = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']
SECTION_KEYS = [
    'interface_network_diagnostics',
    'interface_temporal_diagnostics',
    'interface_topology_diagnostics',
    'interface_spectrum_diagnostics',
    'channel_hypergraph_diagnostics',
    'channel_motif_diagnostics',
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


def flatten_numeric(obj: Any, prefix: str = '') -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f'{prefix}.{k}' if prefix else k
            out.update(flatten_numeric(v, nk))
    elif isinstance(obj, list):
        pass
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = float(obj)
    return out


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
                summary_path = case_dir / 'summary.json'
                with summary_path.open('r', encoding='utf-8') as fh:
                    summary = json.load(fh)
                feats.update(flatten_numeric({k: summary[k] for k in SECTION_KEYS if k in summary}))
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
        var = fmean([(v - mu) ** 2 for v in vals])
        means[k] = mu
        stds[k] = math.sqrt(var) if var > 1e-9 else 1.0
    return means, stds


def zscore_apply(samples: list[dict[str, Any]], means: dict[str, float], stds: dict[str, float]) -> list[dict[str, Any]]:
    return [{**s, 'z': {k: (s['features'][k] - means[k]) / stds[k] for k in means}} for s in samples]


def class_mean(samples: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], keys: list[str]) -> dict[str, float]:
    sel = [s for s in samples if predicate(s)]
    return {k: fmean([s['z'][k] for s in sel]) for k in keys}


def squared_distance(z: dict[str, float], center: dict[str, float], keys: list[str]) -> float:
    return sum((z[k] - center[k]) ** 2 for k in keys)


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def translation_accuracy(rows: list[dict[str, Any]]) -> float:
    trs = [r for r in rows if r['label'].startswith('translation')]
    return sum(int(r['predicted'] == r['label']) for r in trs) / len(trs) if trs else 0.0


def support_stats(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], feature_name: str) -> dict[str, float]:
    sel = [r for r in rows if predicate(r)]
    return {
        'sample_count': len(sel),
        'feature_min': min(r['trace_basis_feature_value'] for r in sel),
        'feature_max': max(r['trace_basis_feature_value'] for r in sel),
        'gate_margin_min': min(r['gate_margin_translation_minus_nontranslation'] for r in sel),
        'gate_margin_max': max(r['gate_margin_translation_minus_nontranslation'] for r in sel),
        'feature_name': feature_name,
    }


def main() -> None:
    p = argparse.ArgumentParser(description='Evaluate the fixed two-guard farther-scale stack on the first N288 harder unseen-nuisance panel.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_farther_scale_n288_harder_nuisance_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n288_harder_nuisance_fixed_two_guard_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--target-scale', type=int, default=288)
    p.add_argument('--target-seeds', type=int, nargs='+', default=[7, 8])
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

    def eval_dataset(dataset: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        preds: list[dict[str, Any]] = []
        acts = {
            'translation_margin_guard_triggered': [],
            'negative_sign_aware_fallback_triggered': [],
            'positive_trace_basis_bridge_triggered': [],
            'baseline_support_guard_triggered': [],
        }
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
            trace_val = s['features'][POSITIVE_TRACE_FEATURE]
            row: dict[str, Any] = {
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
                'trace_basis_feature': POSITIVE_TRACE_FEATURE,
                'trace_basis_feature_value': trace_val,
                'trace_basis_threshold': POSITIVE_TRACE_THRESHOLD,
                'trace_basis_direction': POSITIVE_TRACE_DIRECTION,
                'translation_margin_guard_threshold': TRANSLATION_MARGIN_GUARD_THRESHOLD,
                'baseline_support_guard_threshold': BASELINE_SUPPORT_THRESHOLD,
            }
            if dt < dnt:
                row['stage1_predicted'] = 'translation'
                pred = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
                row['pre_bidirectional_predicted'] = pred
                row['translation_margin_guard_triggered'] = False
                if curl > FIXED_SEPARATOR_THRESHOLD:
                    if pred == 'translation_x_neg' and gate_margin <= TRANSLATION_MARGIN_GUARD_THRESHOLD:
                        row['translation_margin_guard_triggered'] = True
                        acts['translation_margin_guard_triggered'].append({
                            'scale': s['scale'],
                            'seed': s['seed'],
                            'case_name': s['case_name'],
                            'label': s['label'],
                            'profile': s['profile'],
                            'gate_margin_translation_minus_nontranslation': gate_margin,
                            'bidirectional_veto_feature': curl,
                            'pre_bidirectional_predicted': pred,
                        })
                    else:
                        row['bidirectional_veto_triggered'] = True
                        row['stage2_baseline_distance'] = db
                        row['stage2_rotation_distance'] = dr
                        pred = 'baseline' if db < dr else 'rotation_z_pos'
                        row['stage1_predicted'] = 'bidirectional_rotation_veto'
                row.setdefault('bidirectional_veto_triggered', False)
                row['sign_aware_fallback_triggered'] = False
                row['positive_trace_basis_bridge_triggered'] = False
                row['predicted_after_translation_margin_guard'] = pred
                row['predicted'] = pred
            else:
                row['stage1_predicted'] = 'nontranslation'
                row['stage2_baseline_distance'] = db
                row['stage2_rotation_distance'] = dr
                row['bidirectional_veto_triggered'] = False
                row['translation_margin_guard_triggered'] = False
                pred = 'baseline' if db < dr else 'rotation_z_pos'
                row['pre_sign_aware_predicted'] = pred
                neg_fallback = (
                    pred == 'baseline' and
                    curl <= FIXED_SEPARATOR_THRESHOLD and
                    dneg < dpos and
                    neg_over_pos <= FIXED_NEG_OVER_POS_RATIO_THRESHOLD and
                    gate_margin <= FIXED_NEG_GATE_MARGIN_THRESHOLD
                )
                row['sign_aware_fallback_triggered'] = neg_fallback
                row['positive_trace_basis_bridge_triggered'] = False
                if neg_fallback:
                    pred = 'translation_x_neg'
                    acts['negative_sign_aware_fallback_triggered'].append({
                        'scale': s['scale'],
                        'seed': s['seed'],
                        'case_name': s['case_name'],
                        'label': s['label'],
                        'profile': s['profile'],
                        'gate_margin_translation_minus_nontranslation': gate_margin,
                        'neg_over_pos_sign_ratio': neg_over_pos,
                        'bidirectional_veto_feature': curl,
                    })
                else:
                    pos_bridge = (
                        pred == 'baseline' and
                        curl <= FIXED_SEPARATOR_THRESHOLD and
                        dpos < dneg and
                        ((trace_val >= POSITIVE_TRACE_THRESHOLD) if POSITIVE_TRACE_DIRECTION == 'high' else (trace_val <= POSITIVE_TRACE_THRESHOLD))
                    )
                    row['positive_trace_basis_bridge_triggered'] = pos_bridge
                    if pos_bridge:
                        pred = 'translation_x_pos'
                        acts['positive_trace_basis_bridge_triggered'].append({
                            'scale': s['scale'],
                            'seed': s['seed'],
                            'case_name': s['case_name'],
                            'label': s['label'],
                            'profile': s['profile'],
                            'trace_basis_feature_value': trace_val,
                            'bidirectional_veto_feature': curl,
                        })
                row['predicted_after_translation_margin_guard'] = pred
                row['predicted'] = pred

            baseline_guard = (
                row['predicted'] == 'translation_x_pos' and
                trace_val <= BASELINE_SUPPORT_THRESHOLD
            )
            row['baseline_support_guard_triggered'] = baseline_guard
            if baseline_guard:
                row['predicted'] = 'baseline'
                acts['baseline_support_guard_triggered'].append({
                    'scale': s['scale'],
                    'seed': s['seed'],
                    'case_name': s['case_name'],
                    'label': s['label'],
                    'profile': s['profile'],
                    'trace_basis_feature_value': trace_val,
                    'gate_margin_translation_minus_nontranslation': gate_margin,
                    'predicted_before_baseline_support_guard': row['predicted_after_translation_margin_guard'],
                })
            row['predicted_after_baseline_support_guard'] = row['predicted']
            preds.append(row)

        return {
            'accuracy': accuracy(preds),
            'translation_accuracy': translation_accuracy(preds),
            'predictions': preds,
        }, acts

    seen_eval, seen_acts = eval_dataset(seen_z)
    target_eval, target_acts = eval_dataset(target_z)

    seen_baseline_support = support_stats(seen_eval['predictions'], lambda r: r['label'] == 'baseline', POSITIVE_TRACE_FEATURE)
    seen_pos_support = support_stats(seen_eval['predictions'], lambda r: r['label'] == 'translation_x_pos', POSITIVE_TRACE_FEATURE)
    open_gap = seen_pos_support['feature_min'] - seen_baseline_support['feature_max']
    remaining = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n288_harder_nuisance_fixed_two_guard_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'carry forward the fixed two-guard farther-scale stack unchanged into the first N288 harder unseen-nuisance panel: keep the overview-first mainline unchanged, keep the fixed bidirectional separator unchanged, keep the legacy negative sign-aware fallback unchanged, keep the legacy positive trace-basis bridge unchanged, keep the v47 translation-margin guard unchanged, and keep the v48 baseline-support guard unchanged; no threshold reselection and no target-scale tuning',
        'seen_scales': args.seen_scales,
        'seen_seeds': args.seen_seeds,
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'profiles': list(PROFILES),
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'bidirectional_veto_key': BIDIRECTIONAL_VETO_KEY,
        'bidirectional_veto_threshold': FIXED_SEPARATOR_THRESHOLD,
        'negative_sign_aware_fallback_conditions': {
            'stage2_class_must_be': 'baseline',
            'curl_must_be_at_or_below': FIXED_SEPARATOR_THRESHOLD,
            'neg_over_pos_sign_ratio_at_or_below': FIXED_NEG_OVER_POS_RATIO_THRESHOLD,
            'gate_margin_translation_minus_nontranslation_at_or_below': FIXED_NEG_GATE_MARGIN_THRESHOLD,
            'sign_must_prefer': 'translation_x_neg',
            'threshold_source': 'carried forward unchanged from the standard full-stack rule stack',
        },
        'positive_trace_bridge_conditions': {
            'stage2_class_must_be': 'baseline',
            'curl_must_be_at_or_below': FIXED_SEPARATOR_THRESHOLD,
            'sign_must_prefer': 'translation_x_pos',
            'feature': POSITIVE_TRACE_FEATURE,
            'direction': POSITIVE_TRACE_DIRECTION,
            'threshold': POSITIVE_TRACE_THRESHOLD,
            'threshold_source': 'carried forward unchanged from the standard full-stack rule stack',
        },
        'translation_margin_guard': {
            'guard_name': 'translation_margin_guard',
            'applies_when': [
                'bidirectional separator would trigger',
                'pre-veto prediction is translation_x_neg',
                f'gate_margin_translation_minus_nontranslation <= {TRANSLATION_MARGIN_GUARD_THRESHOLD}',
            ],
            'threshold_source': 'carried forward unchanged from the v47 N288 separator-overreach controlled study',
        },
        'baseline_support_guard': {
            'guard_name': 'baseline_support_guard',
            'applies_when': [
                'current prediction after the carried-forward stack is translation_x_pos',
                f'{POSITIVE_TRACE_FEATURE} <= {BASELINE_SUPPORT_THRESHOLD}',
            ],
            'threshold_source': 'carried forward unchanged from the v48 N288 baseline-edge controlled study',
            'seen_support_reference': {
                'baseline_family': seen_baseline_support,
                'translation_x_pos_family': seen_pos_support,
                'open_gap_width': open_gap,
            },
        },
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_trigger_counts': {k: len(v) for k, v in seen_acts.items()},
        'target_trigger_counts': {k: len(v) for k, v in target_acts.items()},
        'seen_translation_margin_guard_triggered': seen_acts['translation_margin_guard_triggered'],
        'target_translation_margin_guard_triggered': target_acts['translation_margin_guard_triggered'],
        'seen_negative_fallback_triggered': seen_acts['negative_sign_aware_fallback_triggered'],
        'target_negative_fallback_triggered': target_acts['negative_sign_aware_fallback_triggered'],
        'seen_positive_bridge_triggered': seen_acts['positive_trace_basis_bridge_triggered'],
        'target_positive_bridge_triggered': target_acts['positive_trace_basis_bridge_triggered'],
        'seen_baseline_support_guard_triggered': seen_acts['baseline_support_guard_triggered'],
        'target_baseline_support_guard_triggered': target_acts['baseline_support_guard_triggered'],
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': remaining,
        'verdict': 'first_n288_harder_two_guard_probe',
        'interpretation': 'This first N288 harder unseen-nuisance probe keeps the full fixed two-guard stack unchanged and asks whether the overview-first geometry plus the carried-forward compensators remain sparse and controlled beyond the cleaned N288 standard frontier.',
    }
    (outdir / 'stage1_global_overview_farther_scale_n288_harder_nuisance_fixed_two_guard_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N288 harder unseen-nuisance fixed two-guard candidate',
        '',
        'This probe carries forward the **full fixed controlled stack** into the first `N288` harder unseen-nuisance panel.',
        '',
        '## Fixed stack',
        '- overview-first mainline unchanged',
        f'- bidirectional rotation separator: `{BIDIRECTIONAL_VETO_KEY} > {FIXED_SEPARATOR_THRESHOLD:.6f}`',
        '- negative sign-aware fallback retained with fixed carried-forward thresholds',
        f'- positive trace-basis bridge retained on `{POSITIVE_TRACE_FEATURE}` ({POSITIVE_TRACE_DIRECTION} / `{POSITIVE_TRACE_THRESHOLD:.6f}`)',
        f'- v47 translation-margin guard retained on `gate_margin_translation_minus_nontranslation <= {TRANSLATION_MARGIN_GUARD_THRESHOLD:.6f}` for separator-overreach suppression',
        f'- v48 baseline-support guard retained on `{POSITIVE_TRACE_FEATURE} <= {BASELINE_SUPPORT_THRESHOLD:.6f}`',
        '',
        '## Harder unseen-nuisance panel',
        '- profiles: `early_soft / mid_sharp / late_balanced`',
        f'- seen scales: `{args.seen_scales}` on seeds `{args.seen_seeds}`',
        f'- target scale: `N{args.target_scale}` on seeds `{args.target_seeds}`',
        '',
        '## Results',
        f'- seen overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Trigger counts',
        f'- seen translation-margin guard triggers: `{len(seen_acts["translation_margin_guard_triggered"])} `',
        f'- target translation-margin guard triggers: `{len(target_acts["translation_margin_guard_triggered"])} `',
        f'- seen negative fallback triggers: `{len(seen_acts["negative_sign_aware_fallback_triggered"])} `',
        f'- target negative fallback triggers: `{len(target_acts["negative_sign_aware_fallback_triggered"])} `',
        f'- seen positive bridge triggers: `{len(seen_acts["positive_trace_basis_bridge_triggered"])} `',
        f'- target positive bridge triggers: `{len(target_acts["positive_trace_basis_bridge_triggered"])} `',
        f'- seen baseline-support guard triggers: `{len(seen_acts["baseline_support_guard_triggered"])} `',
        f'- target baseline-support guard triggers: `{len(target_acts["baseline_support_guard_triggered"])} `',
        '',
        '## Remaining target errors',
    ]
    if remaining:
        for row in remaining:
            lines.append(f'- N{row["scale"]} seed {row["seed"]} `{row["case_name"]}`: `{row["label"]}` -> `{row["predicted"]}`')
    else:
        lines.append('- none')
    lines += [
        '',
        '## Interpretation',
        '- this is the first harder unseen-nuisance pressure test at N288 after the standard frontier was cleaned under the fixed two-guard stack',
        '- the question is not whether support layers can be renamed as theory, but whether they remain sparse, fixed, and non-inflating under panel change',
        '- any new farther-scale residual should still be treated as a structured audit target rather than as proof of unrestricted collapse or unrestricted success',
        '',
        '## Mainline impact',
        '- keep the overview-first mainline unchanged',
        '- do not retune either controlled guard on the harder panel',
        '- if this panel is also clean, the next honest move is broader seed expansion or farther unseen scale rather than new patch invention',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N288_HARDER_NUISANCE_FIXED_TWO_GUARD_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
