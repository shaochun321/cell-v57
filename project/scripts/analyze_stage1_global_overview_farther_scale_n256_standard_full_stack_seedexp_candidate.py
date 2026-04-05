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
POSITIVE_TRACE_FEATURE = 'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.dynamic_phasic_family.mean_centroid_shell_index'
POSITIVE_TRACE_THRESHOLD = 1.3508873633981915
POSITIVE_TRACE_DIRECTION = 'high'
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
                feats = {}
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
    means, stds = {}, {}
    for k in keys:
        vals = [s['features'][k] for s in samples]
        mu = fmean(vals)
        var = fmean([(v - mu) ** 2 for v in vals])
        means[k] = mu
        stds[k] = math.sqrt(var) if var > 1e-9 else 1.0
    return means, stds


def zscore_apply(samples: list[dict[str, Any]], means: dict[str, float], stds: dict[str, float]) -> list[dict[str, Any]]:
    return [{**s, 'z': {k: (s['features'][k] - means[k]) / stds[k] for k in means}} for s in samples]


def class_mean(samples: list[dict[str, Any]], predicate, keys: list[str]) -> dict[str, float]:
    sel = [s for s in samples if predicate(s)]
    return {k: fmean([s['z'][k] for s in sel]) for k in keys}


def squared_distance(z: dict[str, float], center: dict[str, float], keys: list[str]) -> float:
    return sum((z[k] - center[k]) ** 2 for k in keys)


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def translation_accuracy(rows: list[dict[str, Any]]) -> float:
    trs = [p for p in rows if p['label'].startswith('translation')]
    return sum(int(r['predicted'] == r['label']) for r in trs) / len(trs) if trs else 0.0


def main() -> None:
    p = argparse.ArgumentParser(description='Evaluate the fixed v39 rule stack on the first beyond-N224 standard richer-profile panel.')
    p.add_argument('--panel-root', type=str, default='/mnt/data/v40_n256_standard_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n256_standard_full_stack_seedexp_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8, 9, 10, 11, 12])
    p.add_argument('--target-scale', type=int, default=256)
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

    def eval_dataset(dataset: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        preds = []
        neg_acts = []
        pos_acts = []
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
            pos_trace_val = s['features'][POSITIVE_TRACE_FEATURE]
            row = {
                'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'], 'profile': s['profile'],
                'translation_distance': dt, 'nontranslation_distance': dnt,
                'gate_margin_translation_minus_nontranslation': gate_margin,
                'sign_distance_pos': dpos, 'sign_distance_neg': dneg,
                'neg_over_pos_sign_ratio': neg_over_pos,
                'bidirectional_veto_feature': curl,
                'positive_trace_basis_feature': POSITIVE_TRACE_FEATURE,
                'positive_trace_basis_feature_value': pos_trace_val,
                'positive_trace_basis_threshold': POSITIVE_TRACE_THRESHOLD,
                'positive_trace_basis_direction': POSITIVE_TRACE_DIRECTION,
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
                row['positive_trace_basis_bridge_triggered'] = False
                row['predicted'] = pred
            else:
                row['stage1_predicted'] = 'nontranslation'
                row['stage2_baseline_distance'] = db
                row['stage2_rotation_distance'] = dr
                row['bidirectional_veto_triggered'] = False
                pred = 'baseline' if db < dr else 'rotation_z_pos'
                row['pre_sign_aware_predicted'] = pred
                neg_fallback = (
                    pred == 'baseline' and curl <= FIXED_THRESHOLD and dneg < dpos and
                    neg_over_pos <= neg_sign_ratio_threshold and gate_margin <= baseline_bridge_gate_margin_threshold
                )
                row['sign_aware_fallback_triggered'] = neg_fallback
                row['positive_trace_basis_bridge_triggered'] = False
                if neg_fallback:
                    pred = 'translation_x_neg'
                    neg_acts.append({
                        'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'],
                        'profile': s['profile'], 'gate_margin_translation_minus_nontranslation': gate_margin,
                        'neg_over_pos_sign_ratio': neg_over_pos, 'bidirectional_veto_feature': curl,
                        'stage2_baseline_distance': db, 'stage2_rotation_distance': dr,
                    })
                else:
                    pos_bridge = (
                        pred == 'baseline' and curl <= FIXED_THRESHOLD and dpos < dneg and
                        ((pos_trace_val >= POSITIVE_TRACE_THRESHOLD) if POSITIVE_TRACE_DIRECTION == 'high' else (pos_trace_val <= POSITIVE_TRACE_THRESHOLD))
                    )
                    row['positive_trace_basis_bridge_triggered'] = pos_bridge
                    if pos_bridge:
                        pred = 'translation_x_pos'
                        pos_acts.append({
                            'scale': s['scale'], 'seed': s['seed'], 'case_name': s['case_name'], 'label': s['label'],
                            'profile': s['profile'], 'feature_value': pos_trace_val,
                            'bidirectional_veto_feature': curl, 'stage2_baseline_distance': db, 'stage2_rotation_distance': dr,
                        })
                row['predicted'] = pred
            preds.append(row)
        return {
            'accuracy': accuracy(preds),
            'translation_accuracy': translation_accuracy(preds),
            'predictions': preds,
        }, neg_acts, pos_acts

    seen_eval, seen_neg_acts, seen_pos_acts = eval_dataset(seen_z)
    target_eval, target_neg_acts, target_pos_acts = eval_dataset(target_z)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n256_standard_full_stack_seedexp_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'carry forward the v39 full rule stack unchanged into the first beyond-N224 standard richer-profile probe: keep the overview-first mainline unchanged, keep the fixed bidirectional rotation separator unchanged, keep the negative sign-aware fallback unchanged, and keep the positive trace-basis bridge unchanged; no threshold reselection and no target-scale tuning',
        'seen_scales': args.seen_scales,
        'seen_seeds': args.seen_seeds,
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'bidirectional_veto_key': BIDIRECTIONAL_VETO_KEY,
        'bidirectional_veto_threshold': FIXED_THRESHOLD,
        'negative_sign_aware_fallback_conditions': {
            'stage2_class_must_be': 'baseline',
            'curl_must_be_at_or_below': FIXED_THRESHOLD,
            'neg_over_pos_sign_ratio_at_or_below': neg_sign_ratio_threshold,
            'gate_margin_translation_minus_nontranslation_at_or_below': baseline_bridge_gate_margin_threshold,
            'sign_must_prefer': 'translation_x_neg',
        },
        'positive_trace_bridge_conditions': {
            'stage2_class_must_be': 'baseline',
            'curl_must_be_at_or_below': FIXED_THRESHOLD,
            'sign_must_prefer': 'translation_x_pos',
            'feature': POSITIVE_TRACE_FEATURE,
            'direction': POSITIVE_TRACE_DIRECTION,
            'threshold': POSITIVE_TRACE_THRESHOLD,
        },
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_negative_fallback_triggered': seen_neg_acts,
        'target_negative_fallback_triggered': target_neg_acts,
        'seen_positive_bridge_triggered': seen_pos_acts,
        'target_positive_bridge_triggered': target_pos_acts,
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': [p for p in target_eval['predictions'] if p['predicted'] != p['label']],
        'verdict': 'beyond_n224_standard_full_stack_probe',
        'interpretation': 'This seed-expansion evaluation keeps the current full rule stack fixed and asks whether the overview-first geometry, the bidirectional separator, the negative sign-aware fallback, and the positive trace-basis bridge remain controlled at N256 under the standard richer-profile panel.'
    }
    (outdir / 'stage1_global_overview_farther_scale_n256_standard_full_stack_seedexp_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N256 standard full-stack seed-expansion candidate',
        '',
        'This seed-expansion evaluation carries forward the **current fixed rule stack** into the N256 standard richer-profile panel across target seeds 7-12.',
        '',
        '## Fixed stack',
        '- overview-first mainline unchanged',
        f'- bidirectional rotation separator: `{BIDIRECTIONAL_VETO_KEY} > {FIXED_THRESHOLD:.6f}`',
        f'- negative sign-aware fallback retained with seen-derived guard thresholds',
        f'- positive trace-basis bridge retained on `{POSITIVE_TRACE_FEATURE}` ({POSITIVE_TRACE_DIRECTION} / `{POSITIVE_TRACE_THRESHOLD:.6f}`)',
        '',
        '## Results',
        f'- seen overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Trigger counts',
        f'- seen negative fallback triggers: `{len(seen_neg_acts)}`',
        f'- target negative fallback triggers: `{len(target_neg_acts)}`',
        f'- seen positive bridge triggers: `{len(seen_pos_acts)}`',
        f'- target positive bridge triggers: `{len(target_pos_acts)}`',
        '',
        '## Remaining target errors',
    ]
    remaining = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    if remaining:
        for row in remaining:
            lines.append(f'- N{row["scale"]} seed {row["seed"]} `{row["case_name"]}`: `{row["label"]}` -> `{row["predicted"]}`')
    else:
        lines.append('- none')
    lines += [
        '',
        '## Interpretation',
        '- this is the N256 standard seed-expansion pressure test of the full current rule stack',
        '- the question is not just whether accuracy stays high, but whether the support layers remain sparse and controlled',
        '- any new farther-scale residual should be treated as a structured audit target, not as automatic proof of core collapse',
        '',
        '## Mainline impact',
        '- keep the overview-first mainline unchanged',
        '- keep residual discussion on the dedicated residual / geometric appendix axes',
        '- if N256 standard seed-expansion is clean, the next honest move is to keep the route fixed and carry that discipline forward',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N256_STANDARD_FULL_STACK_SEEDEXP_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
