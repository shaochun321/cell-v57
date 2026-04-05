from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

THIS_DIR = Path('/mnt/data')
PROJECT_ROOT = Path('/mnt/data/v47_proj/project')
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
POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD = -3.0
NEGATIVE_GUARD_CURL_CEILING = 3.2
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
                with (case_dir / 'summary.json').open('r', encoding='utf-8') as fh:
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


def eval_dataset(dataset: list[dict[str, Any]], t_center, nt_center, b_center, r_center, pos_center, neg_center):
    preds = []
    acts = {
        'translation_margin_guard_triggered': [],
        'negative_guard_overreach_restore_triggered': [],
        'negative_sign_aware_fallback_triggered': [],
        'positive_trace_basis_bridge_triggered': [],
        'baseline_support_guard_triggered': [],
        'positive_translation_margin_guard_triggered': [],
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
            'trace_basis_feature': POSITIVE_TRACE_FEATURE,
            'trace_basis_feature_value': trace_val,
            'trace_basis_threshold': POSITIVE_TRACE_THRESHOLD,
            'trace_basis_direction': POSITIVE_TRACE_DIRECTION,
            'translation_margin_guard_threshold': TRANSLATION_MARGIN_GUARD_THRESHOLD,
            'negative_guard_curl_ceiling': NEGATIVE_GUARD_CURL_CEILING,
            'baseline_support_guard_threshold': BASELINE_SUPPORT_THRESHOLD,
            'positive_translation_margin_guard_threshold': POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD,
        }
        if dt < dnt:
            row['stage1_predicted'] = 'translation'
            pred = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
            row['pre_bidirectional_predicted'] = pred
            row['translation_margin_guard_triggered'] = False
            row['negative_guard_overreach_restore_triggered'] = False
            row['positive_translation_margin_guard_triggered'] = False
            if curl > FIXED_SEPARATOR_THRESHOLD:
                if pred == 'translation_x_neg' and gate_margin <= TRANSLATION_MARGIN_GUARD_THRESHOLD:
                    row['translation_margin_guard_triggered'] = True
                    acts['translation_margin_guard_triggered'].append({
                        'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                        'gate_margin_translation_minus_nontranslation': gate_margin,
                        'bidirectional_veto_feature': curl,
                        'neg_over_pos_sign_ratio': neg_over_pos,
                    })
                    if curl > NEGATIVE_GUARD_CURL_CEILING:
                        row['negative_guard_overreach_restore_triggered'] = True
                        row['stage2_baseline_distance'] = db
                        row['stage2_rotation_distance'] = dr
                        pred = 'baseline' if db < dr else 'rotation_z_pos'
                        acts['negative_guard_overreach_restore_triggered'].append({
                            'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                            'gate_margin_translation_minus_nontranslation': gate_margin,
                            'bidirectional_veto_feature': curl,
                            'neg_over_pos_sign_ratio': neg_over_pos,
                            'restored_prediction': pred,
                        })
                elif pred == 'translation_x_pos' and gate_margin <= POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD:
                    row['positive_translation_margin_guard_triggered'] = True
                    acts['positive_translation_margin_guard_triggered'].append({
                        'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                        'gate_margin_translation_minus_nontranslation': gate_margin, 'bidirectional_veto_feature': curl,
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
            row['negative_guard_overreach_restore_triggered'] = False
            pred = 'baseline' if db < dr else 'rotation_z_pos'
            row['pre_sign_aware_predicted'] = pred
            neg_fallback = (
                pred == 'baseline' and curl <= FIXED_SEPARATOR_THRESHOLD and dneg < dpos and
                neg_over_pos <= FIXED_NEG_OVER_POS_RATIO_THRESHOLD and gate_margin <= FIXED_NEG_GATE_MARGIN_THRESHOLD
            )
            row['sign_aware_fallback_triggered'] = neg_fallback
            row['positive_trace_basis_bridge_triggered'] = False
            if neg_fallback:
                pred = 'translation_x_neg'
                acts['negative_sign_aware_fallback_triggered'].append({
                    'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                    'gate_margin_translation_minus_nontranslation': gate_margin, 'neg_over_pos_sign_ratio': neg_over_pos,
                    'bidirectional_veto_feature': curl,
                })
            else:
                pos_bridge = (
                    pred == 'baseline' and curl <= FIXED_SEPARATOR_THRESHOLD and dpos < dneg and
                    ((trace_val >= POSITIVE_TRACE_THRESHOLD) if POSITIVE_TRACE_DIRECTION == 'high' else (trace_val <= POSITIVE_TRACE_THRESHOLD))
                )
                row['positive_trace_basis_bridge_triggered'] = pos_bridge
                if pos_bridge:
                    pred = 'translation_x_pos'
                    acts['positive_trace_basis_bridge_triggered'].append({
                        'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                        'trace_basis_feature_value': trace_val, 'bidirectional_veto_feature': curl,
                    })
            row['predicted_after_translation_margin_guard'] = pred
            row['positive_translation_margin_guard_triggered'] = False
            row['predicted'] = pred
        baseline_guard = row['predicted'] == 'translation_x_pos' and trace_val <= BASELINE_SUPPORT_THRESHOLD
        row['baseline_support_guard_triggered'] = baseline_guard
        if baseline_guard:
            row['predicted_before_baseline_support_guard'] = row['predicted']
            row['predicted'] = 'baseline'
            acts['baseline_support_guard_triggered'].append({
                'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                'trace_basis_feature_value': trace_val, 'gate_margin_translation_minus_nontranslation': gate_margin,
            })
        row['predicted_after_baseline_support_guard'] = row['predicted']
        preds.append(row)
    return {
        'accuracy': accuracy(preds),
        'translation_accuracy': translation_accuracy(preds),
        'predictions': preds,
    }, acts


def main():
    ap = argparse.ArgumentParser(description='Evaluate a controlled anti-overreach ceiling on the carried-forward negative translation-margin guard.')
    ap.add_argument('--seen-root', default='/mnt/data/v51_n288_harder_seen78_raw')
    ap.add_argument('--target-root', default='/mnt/data/v51_n288_harder_target_seedexp_raw')
    ap.add_argument('--outdir', default='/mnt/data/v52_n288_harder_negative_guard_overreach_controlled_study')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    seen = load_panel(Path(args.seen_root))
    target = load_panel(Path(args.target_root))

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

    seen_eval, seen_acts = eval_dataset(seen_z, t_center, nt_center, b_center, r_center, pos_center, neg_center)
    target_eval, target_acts = eval_dataset(target_z, t_center, nt_center, b_center, r_center, pos_center, neg_center)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n288_harder_negative_guard_overreach_controlled_study',
        'source_protocol': 'stage1_global_overview_farther_scale_n288_harder_target_seedexp_fixed_three_guard_candidate',
        'seen_root': args.seen_root,
        'target_root': args.target_root,
        'selection_rule': 'carry forward the fixed three-guard stack unchanged, then add one controlled anti-overreach ceiling on the v47 negative translation-margin guard: if the negative translation-margin guard would trigger but the separator feature exceeds a fixed ceiling, restore the separator rather than suppressing it; ceiling selected as a relaxed cap above the largest previously clean protected negative-translation activation in the pre-seedexp panels, so this is a controlled candidate and not a promotable seen-scale-only mainline rule',
        'seen_scales': [64, 96, 128],
        'seen_seeds': [7, 8],
        'target_scale': 288,
        'target_seeds': [7, 8, 9, 10, 11, 12],
        'profiles': list(PROFILES),
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'bidirectional_veto_key': BIDIRECTIONAL_VETO_KEY,
        'bidirectional_veto_threshold': FIXED_SEPARATOR_THRESHOLD,
        'carried_forward_translation_margin_guard': {
            'guard_name': 'translation_margin_guard',
            'threshold': TRANSLATION_MARGIN_GUARD_THRESHOLD,
            'applies_when': ['bidirectional separator would trigger', 'pre-veto prediction is translation_x_neg', f'gate_margin_translation_minus_nontranslation <= {TRANSLATION_MARGIN_GUARD_THRESHOLD}'],
        },
        'controlled_guard': {
            'guard_name': 'negative_guard_overreach_restore',
            'separator_feature': BIDIRECTIONAL_VETO_KEY,
            'ceiling': NEGATIVE_GUARD_CURL_CEILING,
            'applies_when': ['translation_margin_guard would trigger', f'{BIDIRECTIONAL_VETO_KEY} > {NEGATIVE_GUARD_CURL_CEILING}', 'restore separator instead of suppressing it'],
            'selection_basis': {
                'pre_seedexp_clean_protected_cases': [
                    {'panel': 'n288_standard', 'seed': 7, 'case_name': 'translation_x_neg_early_sharp', 'bidirectional_veto_feature': 3.057899718269434},
                    {'panel': 'n288_harder', 'seed': 7, 'case_name': 'translation_x_neg_mid_sharp', 'bidirectional_veto_feature': 3.082029765557532},
                ],
                'protected_feature_max': 3.082029765557532,
                'ceiling_choice': NEGATIVE_GUARD_CURL_CEILING,
            },
        },
        'baseline_support_guard': {
            'guard_name': 'baseline_support_guard',
            'threshold': BASELINE_SUPPORT_THRESHOLD,
            'applies_when': ['current prediction is translation_x_pos', f'{POSITIVE_TRACE_FEATURE} <= {BASELINE_SUPPORT_THRESHOLD}'],
        },
        'positive_translation_margin_guard': {
            'guard_name': 'positive_translation_margin_guard',
            'threshold': POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD,
            'applies_when': ['bidirectional separator would trigger', 'pre-veto prediction is translation_x_pos', f'gate_margin_translation_minus_nontranslation <= {POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD}'],
        },
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_trigger_counts': {k: len(v) for k, v in seen_acts.items()},
        'target_trigger_counts': {k: len(v) for k, v in target_acts.items()},
        'seen_translation_margin_guard_triggered': seen_acts['translation_margin_guard_triggered'],
        'target_translation_margin_guard_triggered': target_acts['translation_margin_guard_triggered'],
        'seen_negative_guard_overreach_restore_triggered': seen_acts['negative_guard_overreach_restore_triggered'],
        'target_negative_guard_overreach_restore_triggered': target_acts['negative_guard_overreach_restore_triggered'],
        'seen_negative_fallback_triggered': seen_acts['negative_sign_aware_fallback_triggered'],
        'target_negative_fallback_triggered': target_acts['negative_sign_aware_fallback_triggered'],
        'seen_positive_bridge_triggered': seen_acts['positive_trace_basis_bridge_triggered'],
        'target_positive_bridge_triggered': target_acts['positive_trace_basis_bridge_triggered'],
        'seen_baseline_support_guard_triggered': seen_acts['baseline_support_guard_triggered'],
        'target_baseline_support_guard_triggered': target_acts['baseline_support_guard_triggered'],
        'seen_positive_translation_margin_guard_triggered': seen_acts['positive_translation_margin_guard_triggered'],
        'target_positive_translation_margin_guard_triggered': target_acts['positive_translation_margin_guard_triggered'],
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': [p for p in target_eval['predictions'] if p['predicted'] != p['label']],
        'verdict': 'controlled_candidate',
        'interpretation': 'This study does not change the overview-first mainline, the fixed separator, or the other two support layers. It only asks whether the v47 negative translation-margin guard has become too permissive on broadened harder N288 seeds and whether a narrow anti-overreach ceiling can restore the separator on that new residual family without polluting the carried-forward protected negative-translation cases.',
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n288_harder_negative_guard_overreach_controlled_study_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    errs = payload['target_misclassifications']
    lines = [
        '# Stage-1 farther-scale N288 harder negative guard overreach controlled study',
        '',
        'This study isolates the new harder-panel residual family exposed by N288 harder target-seed expansion: the carried-forward v47 negative translation-margin guard suppresses the separator on a small set of true rotation cases and leaves them as `translation_x_neg`.',
        '',
        '## Carried-forward stack',
        '- overview-first mainline unchanged',
        f'- fixed bidirectional separator: `{BIDIRECTIONAL_VETO_KEY} > {FIXED_SEPARATOR_THRESHOLD:.6f}`',
        f'- carried-forward negative translation-margin guard: `gate_margin_translation_minus_nontranslation <= {TRANSLATION_MARGIN_GUARD_THRESHOLD:.6f}` when pre-veto is `translation_x_neg`',
        f'- carried-forward baseline-support guard: `{POSITIVE_TRACE_FEATURE} <= {BASELINE_SUPPORT_THRESHOLD:.6f}` when current prediction is `translation_x_pos`',
        f'- carried-forward positive translation-margin guard: `gate_margin_translation_minus_nontranslation <= {POSITIVE_TRANSLATION_MARGIN_GUARD_THRESHOLD:.6f}` when pre-veto is `translation_x_pos`',
        '',
        '## Controlled anti-overreach candidate',
        f'- name: `negative_guard_overreach_restore`',
        f'- applies only when the negative translation-margin guard would trigger **and** `{BIDIRECTIONAL_VETO_KEY} > {NEGATIVE_GUARD_CURL_CEILING:.6f}`',
        '- action: restore the separator instead of suppressing it',
        '- governance status: controlled candidate only; not a promotable seen-scale-only mainline rule',
        '',
        '## Results',
        f'- seen overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N288 overall: `{target_eval["accuracy"]:.3f}`',
        f'- N288 translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Trigger counts',
        f'- seen negative translation-margin guard triggers: `{len(seen_acts["translation_margin_guard_triggered"])} `',
        f'- target negative translation-margin guard triggers: `{len(target_acts["translation_margin_guard_triggered"])} `',
        f'- seen negative guard overreach restores: `{len(seen_acts["negative_guard_overreach_restore_triggered"])} `',
        f'- target negative guard overreach restores: `{len(target_acts["negative_guard_overreach_restore_triggered"])} `',
        f'- seen negative fallback triggers: `{len(seen_acts["negative_sign_aware_fallback_triggered"])} `',
        f'- target negative fallback triggers: `{len(target_acts["negative_sign_aware_fallback_triggered"])} `',
        f'- seen positive bridge triggers: `{len(seen_acts["positive_trace_basis_bridge_triggered"])} `',
        f'- target positive bridge triggers: `{len(target_acts["positive_trace_basis_bridge_triggered"])} `',
        f'- seen baseline-support guard triggers: `{len(seen_acts["baseline_support_guard_triggered"])} `',
        f'- target baseline-support guard triggers: `{len(target_acts["baseline_support_guard_triggered"])} `',
        f'- seen positive translation-margin guard triggers: `{len(seen_acts["positive_translation_margin_guard_triggered"])} `',
        f'- target positive translation-margin guard triggers: `{len(target_acts["positive_translation_margin_guard_triggered"])} `',
        '',
        '## Remaining target errors',
    ]
    if errs:
        for row in errs:
            lines.append(f'- seed {row["seed"]} `{row["case_name"]}`: `{row["label"]}` -> `{row["predicted"]}`')
    else:
        lines.append('- none')
    lines += [
        '',
        '## Interpretation',
        '- the v47 negative translation-margin guard is now shown to have a sharper applicability boundary than the fixed three-guard stack previously assumed',
        '- the new harder-seed failures are not evidence that the overview-first mainline collapsed; they are evidence that one carried-forward compensator had become too permissive on a new farther-scale rotation family',
        '- because the new ceiling is not seen-scale-only, it must remain a controlled candidate rather than a promotable mainline rule',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N288_HARDER_NEGATIVE_GUARD_OVERREACH_CONTROLLED_STUDY_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
