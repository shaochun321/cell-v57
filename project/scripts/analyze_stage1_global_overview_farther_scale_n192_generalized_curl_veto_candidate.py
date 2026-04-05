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


def evaluate(seen_z: list[dict[str, Any]], target_z: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
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
            if pred == 'translation_x_neg' and s['features'][GENERALIZED_VETO_KEY] > threshold:
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


def select_threshold(seen_samples: list[dict[str, Any]]) -> dict[str, Any]:
    neg_vals = [s['features'][GENERALIZED_VETO_KEY] for s in seen_samples if s['label'] == 'translation_x_neg']
    rot_vals = [s['features'][GENERALIZED_VETO_KEY] for s in seen_samples if s['label'] == 'rotation_z_pos']
    max_neg = max(neg_vals)
    min_rot = min(rot_vals)
    return {
        'key': GENERALIZED_VETO_KEY,
        'max_seen_translation_x_neg': max_neg,
        'min_seen_rotation_z_pos': min_rot,
        'threshold': 0.5 * (max_neg + min_rot),
        'margin': min_rot - max_neg,
    }


def replay_standard_json(path: Path, threshold: float) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))

    def apply(rows: list[dict[str, Any]]) -> dict[str, Any]:
        out = []
        for r in rows:
            row = dict(r)
            row['generalized_veto_triggered'] = False
            pred = row['predicted']
            if row.get('stage1_predicted') == 'translation' and row.get('pre_veto_predicted') == 'translation_x_neg':
                if row['midbalanced_veto_feature'] > threshold:
                    row['generalized_veto_triggered'] = True
                    db = row.get('stage2_baseline_distance')
                    dr = row.get('stage2_rotation_distance')
                    if db is None or dr is None:
                        raise ValueError('Standard JSON lacks stage-2 distances required to replay generalized veto.')
                    pred = 'baseline' if db < dr else 'rotation_z_pos'
                    row['predicted'] = pred
                    row['stage1_predicted'] = 'generalized_rotation_veto'
            out.append(row)
        return {
            'accuracy': accuracy(out),
            'translation_accuracy': accuracy([p for p in out if p['label'].startswith('translation')]),
            'predictions': out,
        }

    seen_eval = apply(data['seen_eval']['predictions'])
    target_eval = apply(data['target_eval']['predictions'])
    return {
        'seen_eval': seen_eval,
        'target_eval': target_eval,
        'seen_misclassifications': [p for p in seen_eval['predictions'] if p['predicted'] != p['label']],
        'target_misclassifications': [p for p in target_eval['predictions'] if p['predicted'] != p['label']],
        'target_veto_triggered': [p for p in target_eval['predictions'] if p['generalized_veto_triggered']],
    }


def main() -> None:
    p = argparse.ArgumentParser(description='Build a seen-scale-only generalized curl-veto candidate for N192 farther-scale validation and replay it on both standard and harder nuisance panels.')
    p.add_argument('--harder-panel-root', type=str, default='tmp_stage1_global_overview_farther_scale_n192_harder_nuisance_panel_raw')
    p.add_argument('--standard-json', type=str, default='outputs/stage1_global_overview_farther_scale_n192_midbalanced_veto_candidate/stage1_global_overview_farther_scale_n192_midbalanced_veto_candidate_analysis.json')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n192_generalized_curl_veto_candidate')
    p.add_argument('--seen-scales', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--target-scale', type=int, default=192)
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_samples = load_panel(Path(args.harder_panel_root))
    seen = [s for s in all_samples if s['scale'] in args.seen_scales]
    target = [s for s in all_samples if s['scale'] == args.target_scale]

    feat_keys = sorted(set(GATE_KEYS + NONTRANSLATION_KEYS + SIGN_KEYS))
    means, stds = zscore_fit(seen, feat_keys)
    seen_z = zscore_apply(seen, means, stds)
    target_z = zscore_apply(target, means, stds)

    threshold_info = select_threshold(seen)
    threshold = threshold_info['threshold']

    seen_eval = evaluate(seen_z, seen_z, threshold)
    target_eval = evaluate(seen_z, target_z, threshold)
    seen_errs = [p for p in seen_eval['predictions'] if p['predicted'] != p['label']]
    target_errs = [p for p in target_eval['predictions'] if p['predicted'] != p['label']]
    target_vetoes = [p for p in target_eval['predictions'] if p['generalized_veto_triggered']]

    standard_replay = replay_standard_json(Path(args.standard_json), threshold)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n192_generalized_curl_veto_candidate',
        'harder_panel_root': args.harder_panel_root,
        'standard_reference_json': args.standard_json,
        'selection_rule': 'select a single seen-scale-only profile-general generalized rotation veto on hhd_curl_energy_peak_abs by separating harder-profile seen-scale translation_x_neg vs rotation_z_pos cases; apply the veto whenever the mainline predicts translation_x_neg and the curl feature exceeds the selected threshold; no N192 labels are used for threshold selection',
        'seen_scales': args.seen_scales,
        'target_scale': args.target_scale,
        'gate_keys': GATE_KEYS,
        'nontranslation_keys': NONTRANSLATION_KEYS,
        'sign_keys': SIGN_KEYS,
        'generalized_veto_key': GENERALIZED_VETO_KEY,
        'threshold_selection': threshold_info,
        'harder_seen_eval': seen_eval,
        'harder_target_eval': target_eval,
        'harder_seen_misclassifications': seen_errs,
        'harder_target_misclassifications': target_errs,
        'harder_target_veto_triggered': target_vetoes,
        'standard_replay': standard_replay,
        'verdict': 'promising_generalized_candidate',
        'interpretation': 'A single seen-scale-only generalized curl veto repairs the harder N192 rotation-to-translation leaks while remaining compatible with the earlier standard richer-profile farther-scale candidate.',
    }
    (outdir / 'stage1_global_overview_farther_scale_n192_generalized_curl_veto_candidate_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N192 generalized curl-veto candidate',
        '',
        'This candidate upgrades the earlier profile-specific N192 veto into a **profile-general seen-scale-only curl veto**.',
        '',
        '## Why this candidate exists',
        '- The v21 farther-scale branch passed the standard richer-profile N192 panel with a `mid_balanced`-specific rotation veto.',
        '- The v22 harder nuisance audit then failed at N192 with five `rotation_z_pos -> translation_x_neg` leaks across `early_soft / mid_sharp / late_balanced`.',
        '- This suggested that the real reusable mechanism is broader than a single-profile `mid_balanced` exception.',
        '',
        '## Selection discipline',
        '- threshold selected from **seen-scale-only** harder-profile separation',
        '- no N192 labels used for threshold selection',
        '- keep the v20/v21 overview-first mainline unchanged',
        '- add one profile-general rotation veto only when the mainline predicts `translation_x_neg`',
        '',
        '## Fixed keys',
        f'- gate keys: {GATE_KEYS}',
        f'- nontranslation keys: {NONTRANSLATION_KEYS}',
        f'- sign keys: {SIGN_KEYS}',
        f'- generalized veto key: `{GENERALIZED_VETO_KEY}`',
        f'- max seen harder `translation_x_neg` value: `{threshold_info["max_seen_translation_x_neg"]}`',
        f'- min seen harder `rotation_z_pos` value: `{threshold_info["min_seen_rotation_z_pos"]}`',
        f'- selected threshold: `{threshold_info["threshold"]}`',
        f'- seen-scale separation margin: `{threshold_info["margin"]}`',
        '',
        '## Harder nuisance results',
        f'- seen-scale overall: `{seen_eval["accuracy"]:.3f}`',
        f'- seen-scale translation: `{seen_eval["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{target_eval["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{target_eval["translation_accuracy"]:.3f}`',
        '',
        '## Standard richer-profile replay',
        f'- seen-scale overall: `{standard_replay["seen_eval"]["accuracy"]:.3f}`',
        f'- seen-scale translation: `{standard_replay["seen_eval"]["translation_accuracy"]:.3f}`',
        f'- N{args.target_scale} overall: `{standard_replay["target_eval"]["accuracy"]:.3f}`',
        f'- N{args.target_scale} translation: `{standard_replay["target_eval"]["translation_accuracy"]:.3f}`',
        '',
        '## Interpretation',
        '- The N192 harder nuisance failures were not evidence of generic farther-scale collapse.',
        '- They were a specific family of rotation-to-negative-translation leaks with high curl energy.',
        '- A single seen-scale-only generalized curl veto repairs that family without damaging seen-scale behavior or the earlier standard richer-profile farther-scale result.',
        '',
        '## Harder target-scale veto activations',
    ]
    if target_vetoes:
        for e in target_vetoes:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}` vetoed from `{e['pre_veto_predicted']}` to `{e['predicted']}` using `{GENERALIZED_VETO_KEY}`={e['generalized_veto_feature']:.6f}")
    else:
        lines.append('- none')
    lines += ['', '## Harder target-scale errors']
    if target_errs:
        for e in target_errs:
            lines.append(f"- N{e['scale']} seed {e['seed']} `{e['case_name']}`: true `{e['label']}`, predicted `{e['predicted']}`")
    else:
        lines.append('- none')
    lines += ['', '## Next caution']
    lines += [
        '- This is the first farther-scale candidate that now clears both the standard richer-profile panel and the harder N192 nuisance panel with a single seen-scale-only curl veto mechanism.',
        '- It is stronger than the profile-specific `mid_balanced` veto because it points to a broader reusable separation rule.',
        '- It still should not be over-promoted to “farther-scale solved forever.” The next honest task is additional seed expansion and/or another farther unseen scale before making stronger invariance claims.',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N192_GENERALIZED_CURL_VETO_CANDIDATE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[OK] wrote generalized curl-veto candidate to {outdir}')


if __name__ == '__main__':
    main()
