
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

from cell_sphere_core.analysis.global_overview_temporal import extract_temporal_overview_features

GATE_KEYS = [
    'temporal_translation_dipole_norm_peak_abs',
    'temporal_translation_energy_peak_abs',
    'temporal_rotation_energy_peak_abs',
]
NONTRANSLATION_KEYS = ['temporal_rotation_energy_peak_abs']
SIGN_KEYS = ['temporal_translation_x_at_translation_peak']


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
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                req = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']
                if not all((case_dir / r).exists() for r in req):
                    continue
                samples.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'label': semantic_label(case_dir.name),
                    'profile': profile_label(case_dir.name),
                    'features': extract_temporal_overview_features(case_dir),
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
    p = argparse.ArgumentParser(description='Evaluate a temporal global overview candidate on richer-profile scales.')
    p.add_argument('--panel-root', type=str, default='outputs/stage1_global_overview_temporal_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_temporal_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=160)
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.panel_root))
    seen = [s for s in all_samples if s['scale'] in args.seen_scales]
    target = [s for s in all_samples if s['scale'] == args.target_scale]
    feature_keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen, feature_keys)
    seen_z = zscore_apply(seen, means, stds)
    target_z = zscore_apply(target, means, stds)

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

    result = {
        'accuracy': accuracy(preds),
        'translation_accuracy': accuracy([p for p in preds if p['label'].startswith('translation')]),
        'predictions': preds,
    }
    payload = {
        'protocol': 'stage1_global_overview_temporal_candidate',
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'result': result,
        'verdict': 'candidate_not_promoted',
        'rationale': 'Temporal overview recovers early-sharp translation but leaks baseline into translation; timing alone is not a sufficient global overview fix.',
    }
    (outdir / 'stage1_global_overview_temporal_candidate_analysis.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')

    errs = [p for p in preds if p['predicted'] != p['label']]
    lines = [
        '# Stage-1 Global Overview Temporal Candidate',
        '',
        '## Verdict',
        '`candidate_not_promoted`',
        '',
        '## Fixed candidate',
        f'- gate keys: {GATE_KEYS}',
        f'- nontranslation key: {NONTRANSLATION_KEYS}',
        f'- sign key: {SIGN_KEYS}',
        '',
        '## Result on richer-profile N160 panel',
        f'- overall: `{result["accuracy"]:.3f}`',
        f'- translation: `{result["translation_accuracy"]:.3f}`',
        '',
        '## Interpretation',
        '- Temporal global overview fixes the early-sharp translation sign failures that motivated this branch.',
        '- But it introduces a new failure mode: baseline leaks into the translation branch.',
        '- Therefore time-aware overview alone is not a sufficient replacement for the current overview candidate.',
        '- The next cleaner step is not “more timing features”, but a field-decomposition style overview layer (HHD-lite / divergence-vs-circulation split).',
        '',
        '## Errors',
    ]
    if errs:
        for e in errs:
            lines.append(f'- seed {e["seed"]} `{e["case_name"]}`: true `{e["label"]}`, predicted `{e["predicted"]}` (stage-1 `{e["stage1_predicted"]}`)')
    else:
        lines.append('- none')
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_TEMPORAL_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
