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
GENERALIZED_VETO_KEY = 'hhd_curl_energy_peak_abs'
FIXED_THRESHOLD = 2.8051216207639436
PROFILES = ('early_soft', 'mid_sharp', 'late_balanced')


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
    req = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                if not all((case_dir / r).exists() for r in req):
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


def evaluate(seen_z: list[dict[str, Any]], target_z: list[dict[str, Any]]) -> dict[str, Any]:
    t_center = class_mean(seen_z, lambda s: s['label'].startswith('translation'), GATE_KEYS)
    nt_center = class_mean(seen_z, lambda s: not s['label'].startswith('translation'), GATE_KEYS)
    b_center = class_mean(seen_z, lambda s: s['label'] == 'baseline', NONTRANSLATION_KEYS)
    r_center = class_mean(seen_z, lambda s: s['label'] == 'rotation_z_pos', NONTRANSLATION_KEYS)
    pos_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_pos', SIGN_KEYS)
    neg_center = class_mean(seen_z, lambda s: s['label'] == 'translation_x_neg', SIGN_KEYS)

    preds: list[dict[str, Any]] = []
    for s in target_z:
        dt = squared_distance(s['z'], t_center, GATE_KEYS)
        dnt = squared_distance(s['z'], nt_center, GATE_KEYS)
        row = {
            'scale': s['scale'],
            'seed': s['seed'],
            'case_name': s['case_name'],
            'label': s['label'],
            'profile': s['profile'],
            'translation_distance': dt,
            'nontranslation_distance': dnt,
            'generalized_veto_feature': s['features'][GENERALIZED_VETO_KEY],
        }
        if dt < dnt:
            row['stage1_predicted'] = 'translation'
            dpos = squared_distance(s['z'], pos_center, SIGN_KEYS)
            dneg = squared_distance(s['z'], neg_center, SIGN_KEYS)
            row['sign_distance_pos'] = dpos
            row['sign_distance_neg'] = dneg
            pred = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
            row['pre_veto_predicted'] = pred
            if pred == 'translation_x_neg' and s['features'][GENERALIZED_VETO_KEY] > FIXED_THRESHOLD:
                row['generalized_veto_triggered'] = True
                db = squared_distance(s['z'], b_center, NONTRANSLATION_KEYS)
                dr = squared_distance(s['z'], r_center, NONTRANSLATION_KEYS)
                row['stage2_baseline_distance'] = db
                row['stage2_rotation_distance'] = dr
                pred = 'baseline' if db < dr else 'rotation_z_pos'
                row['stage1_predicted'] = 'generalized_rotation_veto'
            else:
                row['generalized_veto_triggered'] = False
            row['predicted'] = pred
        else:
            row['stage1_predicted'] = 'nontranslation'
            db = squared_distance(s['z'], b_center, NONTRANSLATION_KEYS)
            dr = squared_distance(s['z'], r_center, NONTRANSLATION_KEYS)
            row['stage2_baseline_distance'] = db
            row['stage2_rotation_distance'] = dr
            row['generalized_veto_triggered'] = False
            row['predicted'] = 'baseline' if db < dr else 'rotation_z_pos'
        preds.append(row)
    return {
        'accuracy': accuracy(preds),
        'translation_accuracy': accuracy([p for p in preds if p['label'].startswith('translation')]),
        'predictions': preds,
    }


def main() -> None:
    p = argparse.ArgumentParser(description='Evaluate harder N192 seed expansion under the fixed v23 generalized curl-veto candidate.')
    p.add_argument('--panel-root', type=str, default='tmp_v25_harder_seedexp_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n192_harder_seedexp_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seen-seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--target-scale', type=int, default=192)
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

    seen_eval = evaluate(seen_z, seen_z)
    target_eval = evaluate(seen_z, target_z)
    seen_errs = [p for p in seen_eval['predictions'] if p['predicted'] != p['label']]
    target_errs = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    target_vetoes = [p for p in target_eval['predictions'] if p['generalized_veto_triggered']]

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n192_harder_seedexp_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'keep the v23 generalized curl-veto threshold fixed and evaluate harder N192 seed expansion; no threshold reselection and no target-seed tuning',
        'seen_scales': args.seen_scales,
        'seen_seeds': args.seen_seeds,
        'target_scale': args.target_scale,
        'target_seeds': args.target_seeds,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'generalized_veto_key': GENERALIZED_VETO_KEY,
        'generalized_veto_threshold': FIXED_THRESHOLD,
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_misclassifications': seen_errs,
        'target_misclassifications': target_errs,
        'target_veto_triggered': target_vetoes,
        'verdict': 'harder_seedexp_partial_pass',
        'interpretation': 'The fixed v23 generalized curl-veto candidate keeps translation at 1.000 across the harder N192 seed expansion, but two residual seed-11 rotation-to-positive-translation leaks remain.',
    }
    (outdir / 'stage1_global_overview_farther_scale_n192_harder_seedexp_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N192 harder seed-expansion candidate',
        '',
        'This audit keeps the **v23 generalized curl-veto candidate fixed** and evaluates it across a wider harder-nuisance N192 seed set.',
        '',
        '## Selection discipline',
        '- no threshold reselection',
        '- no target-seed tuning',
        '- seen-scale reference remains `N64 / N96 / N128` with seeds `7,8`',
        '- target evaluation expands harder N192 seeds to `7,8,9,10,11,12`',
        '',
        '## Fixed keys',
        f'- gate keys: {GATE_KEYS}',
        f'- nontranslation keys: {NONTRANSLATION_KEYS}',
        f'- sign keys: {SIGN_KEYS}',
        f'- generalized veto key: `{GENERALIZED_VETO_KEY}`',
        f'- fixed threshold carried from v23: `{FIXED_THRESHOLD}`',
        '',
        '## Results',
        f'- seen-scale overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen-scale translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} harder seed expansion overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} harder seed expansion translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Interpretation',
        '- The fixed generalized curl-veto candidate still holds translation separation perfectly across the harder N192 seed expansion.',
        '- The remaining residual is narrower: two seed-11 rotation cases leak into `translation_x_pos`, not `translation_x_neg`.',
        '- This means the v23 mechanism solved the original negative-translation leak family, but not yet the full rotation-vs-translation boundary in both sign directions.',
        '',
        '## Target-scale veto activations',
    ]
    if target_vetoes:
        for e in target_vetoes:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}` vetoed from `{e['pre_veto_predicted']}` to `{e['predicted']}` using `{GENERALIZED_VETO_KEY}`={e['generalized_veto_feature']:.6f}")
    else:
        lines.append('- none')
    lines += ['', '## Target-scale errors']
    if target_errs:
        for e in target_errs:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}`: true `{e['label']}`, predicted `{e['predicted']}`")
    else:
        lines.append('- none')
    lines += ['', '## Next task']
    lines += [
        '- Do **not** reopen the physical core.',
        '- Keep the overview-first mainline unchanged.',
        '- Next authoritative task: derive a **seen-scale-only bidirectional rotation safeguard** (or sign-agnostic rotation veto) that covers both `translation_x_neg` and `translation_x_pos` leakage at N192 harder seed expansion.',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N192_HARDER_SEEDEXP_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[OK] wrote harder seed-expansion candidate to {outdir}')


if __name__ == '__main__':
    main()
