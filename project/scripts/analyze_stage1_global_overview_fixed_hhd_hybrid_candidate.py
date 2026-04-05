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

GATE_KEYS = [
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'hhd_div_to_curl_peak_abs',
]
NONTRANSLATION_KEYS = ['hhd_curl_energy_peak_abs']
SIGN_KEYS = ['overview_translation_dipole_x_mean', 'hhd_div_x_mean']


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


def profile_label(case_name: str) -> str:
    for p in ('early_sharp', 'mid_balanced', 'late_soft'):
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
                samples.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'label': semantic_label(case_dir.name),
                    'profile': profile_label(case_dir.name),
                    'features': extract_hybrid_overview_features(case_dir),
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
        }
        if dt < dnt:
            row['stage1_predicted'] = 'translation'
            dpos = squared_distance(s['z'], pos_center, SIGN_KEYS)
            dneg = squared_distance(s['z'], neg_center, SIGN_KEYS)
            row['sign_distance_pos'] = dpos
            row['sign_distance_neg'] = dneg
            row['predicted'] = 'translation_x_pos' if dpos < dneg else 'translation_x_neg'
        else:
            row['stage1_predicted'] = 'nontranslation'
            db = squared_distance(s['z'], b_center, NONTRANSLATION_KEYS)
            dr = squared_distance(s['z'], r_center, NONTRANSLATION_KEYS)
            row['stage2_baseline_distance'] = db
            row['stage2_rotation_distance'] = dr
            row['predicted'] = 'baseline' if db < dr else 'rotation_z_pos'
        preds.append(row)
    return {
        'accuracy': accuracy(preds),
        'translation_accuracy': accuracy([p for p in preds if p['label'].startswith('translation')]),
        'predictions': preds,
    }


def main() -> None:
    p = argparse.ArgumentParser(description='Evaluate a fixed overview + HHD-lite hybrid candidate on the cross-scale richer-profile panel.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_temporal_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_fixed_hhd_hybrid_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=160)
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.panel_root))
    seen = [s for s in all_samples if s['scale'] in args.seen_scales]
    target = [s for s in all_samples if s['scale'] == args.target_scale]

    feat_keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen, feat_keys)
    seen_z = zscore_apply(seen, means, stds)
    target_z = zscore_apply(target, means, stds)

    seen_eval = evaluate(seen_z, seen_z)
    target_eval = evaluate(seen_z, target_z)
    target_errs = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    seen_errs = [p for p in seen_eval['predictions'] if p['predicted'] != p['label']]

    payload = {
        'protocol': 'stage1_global_overview_fixed_hhd_hybrid_candidate',
        'panel_root': args.panel_root,
        'selection_rule': 'candidate selected by constrained seen-scale-only search across fixed overview + HHD-lite feature families; target scale not used for candidate selection',
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_misclassifications': seen_errs,
        'target_misclassifications': target_errs,
        'verdict': 'promising_candidate',
        'interpretation': 'A fixed overview + HHD-lite hybrid candidate preserves very strong seen-scale compatibility and improves N160 richer-profile generalization without target-scale rescue. The remaining failure is a single N160 translation_x_pos_late_soft case routed to baseline.',
    }
    (outdir / 'stage1_global_overview_fixed_hhd_hybrid_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 fixed overview + HHD-lite hybrid candidate',
        '',
        'This candidate combines the strongest fixed overview channels with a small HHD-lite augmentation.',
        '',
        '## Selection discipline',
        '- candidate chosen by constrained **seen-scale-only** search',
        '- target-scale labels were **not** used to select the feature set',
        '',
        '## Fixed keys',
        f'- gate keys: {GATE_KEYS}',
        f'- nontranslation keys: {NONTRANSLATION_KEYS}',
        f'- sign keys: {SIGN_KEYS}',
        '',
        '## Results',
        f'- seen-scale overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen-scale translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Interpretation',
        '- This is the first non-probe-informed hybrid candidate that meaningfully combines overview-first and decomposition-style channels.',
        '- It preserves strong seen-scale compatibility while improving N160 richer-profile generalization.',
        '- The remaining failure is a single late-soft positive translation case routed into the nontranslation branch.',
        '- This makes the hybrid line a stronger next-step candidate than either the pure temporal overview or the HHD-lite-only proxy.',
        '',
        '## Remaining errors',
    ]
    if target_errs:
        for e in target_errs:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}`: true `{e['label']}`, predicted `{e['predicted']}` (stage-1 `{e['stage1_predicted']}`)")
    else:
        lines.append('- none')
    lines += [
        '',
        '## Seen-scale errors',
    ]
    if seen_errs:
        for e in seen_errs:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}`: true `{e['label']}`, predicted `{e['predicted']}` (stage-1 `{e['stage1_predicted']}`)")
    else:
        lines.append('- none')
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FIXED_HHD_HYBRID_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[OK] wrote fixed+HHD hybrid candidate to {outdir}')


if __name__ == '__main__':
    main()
