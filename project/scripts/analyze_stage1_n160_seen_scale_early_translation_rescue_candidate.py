from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import extract_features
from scripts.analyze_stage1_translation_richer_profile_scale_audit import load_panel as load_translation_panel
from scripts.analyze_stage1_translation_richer_profile_scale_audit import zscore_against_n64 as zscore_translation_panel
from scripts.analyze_stage1_hierarchical_stress_audit import accuracy

ROUTE_KEYS = [
    'local_propagation_track_dissipation_load',
    'discrete_channel_track_bandwidth_shell_3',
]
RESCUE_KEYS = [
    'layered_coupling_track_circulation_span',
]
EARLY_SIGN_KEYS = [
    'discrete_channel_track_circulation_strength',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate a clean seen-scale-derived early translation rescue candidate on N160 richer nuisance.')
    p.add_argument('--translation-richer-profile-root', type=str, default='outputs/stage1_translation_richer_profile_scale_panel_raw')
    p.add_argument('--seen-early-sharp-nuisance-root', type=str, default='outputs/stage1_early_sharp_seen_nuisance_panel_raw')
    p.add_argument('--n160-stress-dir', type=str, default='outputs/stage1_n160_richer_nuisance_panel_raw/N160')
    p.add_argument('--baseline-json', type=str, default='outputs/stage1_n160_seen_scale_early_translation_rescue_candidate/baseline_hybrid_predictions_reference.json')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_seen_scale_early_translation_rescue_candidate')
    return p.parse_args()


def radius_coord(num_cells: int) -> float:
    return num_cells ** (1.0 / 3.0)


def fit_linear_centers(rows: list[dict[str, Any]], keys: list[str], predicate, scales=(64, 96, 128)) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for key in keys:
        xs, ys = [], []
        for scale in scales:
            vals = [r['z_features'][key] for r in rows if r['scale'] == scale and predicate(r)]
            xs.append(radius_coord(scale))
            ys.append(mean(vals))
        xbar = mean(xs)
        ybar = mean(ys)
        den = sum((x - xbar) ** 2 for x in xs) or 1.0
        a = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / den
        b = ybar - a * xbar
        out[key] = (a, b)
    return out


def center_from_linear(params: dict[str, tuple[float, float]], scale: int) -> dict[str, float]:
    r = radius_coord(scale)
    return {k: a * r + b for k, (a, b) in params.items()}


def load_early_sharp_seen_panel(panel_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                name = case_dir.name
                if name.startswith('translation_x_pos'):
                    label = 'translation_x_pos'
                elif name.startswith('translation_x_neg'):
                    label = 'translation_x_neg'
                elif name.startswith('rotation_z_pos'):
                    label = 'rotation_z_pos'
                else:
                    label = 'baseline'
                rows.append({
                    'scale': scale,
                    'seed': seed,
                    'case_name': name,
                    'label': label,
                    'features': extract_features(case_dir),
                })
    return rows


def zscore_against_n64(rows: list[dict[str, Any]]) -> list[str]:
    feature_names = list(rows[0]['features'].keys())
    ref = [r for r in rows if r['scale'] == 64]
    means = {k: mean(r['features'][k] for r in ref) for k in feature_names}
    stds = {k: (pstdev([r['features'][k] for r in ref]) or 1.0) for k in feature_names}
    for row in rows:
        row['z_features'] = {k: (row['features'][k] - means[k]) / stds[k] for k in feature_names}
    return feature_names


def load_n160_panel(panel_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            name = case_dir.name
            if name.startswith('translation_x_pos'):
                label = 'translation_x_pos'
            elif name.startswith('translation_x_neg'):
                label = 'translation_x_neg'
            elif name.startswith('rotation_z_pos'):
                label = 'rotation_z_pos'
            else:
                label = 'baseline'
            rows.append({
                'seed': seed,
                'case_name': name,
                'label': label,
                'features': extract_features(case_dir),
            })
    return rows


def per_case_accuracy(preds: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, list[dict[str, Any]]] = {}
    for p in preds:
        out.setdefault(p['case_name'], []).append(p)
    return {k: accuracy(v) for k, v in sorted(out.items())}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    translation_rows = load_translation_panel(Path(args.translation_richer_profile_root))
    zscore_translation_panel(translation_rows)
    translation_rows = [r for r in translation_rows if r['scale'] in (64, 96, 128)]

    early_rows = load_early_sharp_seen_panel(Path(args.seen_early_sharp_nuisance_root))
    early_feature_names = zscore_against_n64(early_rows)

    n160_rows = load_n160_panel(Path(args.n160_stress_dir))
    # route/sign normalization from translation richer profile panel
    tr_feature_names = list(translation_rows[0]['features'].keys())
    tr_ref = [r for r in translation_rows if r['scale'] == 64]
    tr_means = {k: mean(r['features'][k] for r in tr_ref) for k in tr_feature_names}
    tr_stds = {k: (pstdev([r['features'][k] for r in tr_ref]) or 1.0) for k in tr_feature_names}
    # rescue normalization from seen early sharp nuisance panel
    early_ref = [r for r in early_rows if r['scale'] == 64]
    early_means = {k: mean(r['features'][k] for r in early_ref) for k in early_feature_names}
    early_stds = {k: (pstdev([r['features'][k] for r in early_ref]) or 1.0) for k in early_feature_names}
    for row in n160_rows:
        row['z_route'] = {k: (row['features'][k] - tr_means[k]) / tr_stds[k] for k in tr_feature_names}
        row['z_rescue'] = {k: (row['features'][k] - early_means[k]) / early_stds[k] for k in early_feature_names}

    baseline_ref = json.loads(Path(args.baseline_json).read_text())['baseline_hybrid_predictions']
    baseline_map = {(p['seed'], p['case_name']): p for p in baseline_ref}

    early_route_params = fit_linear_centers(translation_rows, ROUTE_KEYS, lambda r: r['profile'] == 'early_sharp')
    nonearly_route_params = fit_linear_centers(translation_rows, ROUTE_KEYS, lambda r: r['profile'] != 'early_sharp')
    translation_rescue_params = fit_linear_centers(early_rows, RESCUE_KEYS, lambda r: r['label'].startswith('translation'))
    rotation_rescue_params = fit_linear_centers(early_rows, RESCUE_KEYS, lambda r: r['label'] == 'rotation_z_pos')
    pos_sign_params = fit_linear_centers(translation_rows, EARLY_SIGN_KEYS, lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_pos')
    neg_sign_params = fit_linear_centers(translation_rows, EARLY_SIGN_KEYS, lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_neg')

    route_early_center = center_from_linear(early_route_params, 160)
    route_nonearly_center = center_from_linear(nonearly_route_params, 160)
    rescue_translation_center = center_from_linear(translation_rescue_params, 160)
    rescue_rotation_center = center_from_linear(rotation_rescue_params, 160)
    pos_sign_center = center_from_linear(pos_sign_params, 160)
    neg_sign_center = center_from_linear(neg_sign_params, 160)

    candidate_predictions: list[dict[str, Any]] = []
    for sample in n160_rows:
        baseline = baseline_map[(sample['seed'], sample['case_name'])]
        predicted = baseline['predicted']
        route_pred = None
        rescue_applied = False
        rescue_translation_like = None

        if baseline.get('rerouted_by_veto'):
            d_early = sum((sample['z_route'][k] - route_early_center[k]) ** 2 for k in ROUTE_KEYS)
            d_nonearly = sum((sample['z_route'][k] - route_nonearly_center[k]) ** 2 for k in ROUTE_KEYS)
            route_pred = 'early_sharp' if d_early < d_nonearly else 'not_early_sharp'
            if route_pred == 'early_sharp':
                d_tr = sum((sample['z_rescue'][k] - rescue_translation_center[k]) ** 2 for k in RESCUE_KEYS)
                d_rot = sum((sample['z_rescue'][k] - rescue_rotation_center[k]) ** 2 for k in RESCUE_KEYS)
                rescue_translation_like = d_tr < d_rot
                if rescue_translation_like:
                    d_pos = sum((sample['z_route'][k] - pos_sign_center[k]) ** 2 for k in EARLY_SIGN_KEYS)
                    d_neg = sum((sample['z_route'][k] - neg_sign_center[k]) ** 2 for k in EARLY_SIGN_KEYS)
                    predicted = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
                    rescue_applied = True
                else:
                    d_pos = d_neg = None
            else:
                d_tr = d_rot = d_pos = d_neg = None
        else:
            d_early = d_nonearly = d_tr = d_rot = d_pos = d_neg = None

        candidate_predictions.append({
            'seed': sample['seed'],
            'case_name': sample['case_name'],
            'label': sample['label'],
            'predicted': predicted,
            'baseline_predicted': baseline['predicted'],
            'rerouted_by_veto': baseline.get('rerouted_by_veto', False),
            'route_predicted': route_pred,
            'rescue_translation_like': rescue_translation_like,
            'rescue_applied': rescue_applied,
            'route_d_early': d_early,
            'route_d_nonearly': d_nonearly,
            'rescue_d_translation': d_tr,
            'rescue_d_rotation': d_rot,
            'sign_d_pos': d_pos,
            'sign_d_neg': d_neg,
        })

    result = {
        'protocol': 'stage1_n160_seen_scale_early_translation_rescue_candidate',
        'status': 'candidate_only_not_promoted',
        'reason': 'clean seen-scale-derived rescue underperforms the probe-informed rescue branch on N160 richer nuisance',
        'route_keys': ROUTE_KEYS,
        'rescue_keys': RESCUE_KEYS,
        'early_sign_keys': EARLY_SIGN_KEYS,
        'baseline_hybrid_accuracy': accuracy(baseline_ref),
        'baseline_hybrid_translation_accuracy': accuracy([p for p in baseline_ref if p['label'].startswith('translation')]),
        'candidate_accuracy': accuracy(candidate_predictions),
        'candidate_translation_accuracy': accuracy([p for p in candidate_predictions if p['label'].startswith('translation')]),
        'baseline_hybrid_per_case_accuracy': per_case_accuracy(baseline_ref),
        'candidate_per_case_accuracy': per_case_accuracy(candidate_predictions),
        'candidate_predictions': candidate_predictions,
    }

    (outdir / 'stage1_n160_seen_scale_early_translation_rescue_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 SEEN-SCALE EARLY-TRANSLATION RESCUE CANDIDATE',
        '',
        '## Goal',
        'Replace the earlier probe-informed early-translation rescue with a clean rule derived only from seen scales (64/96/128), then test it on N160 richer nuisance.',
        '',
        '## Clean derivation inputs',
        f"- route keys (seen-scale richer-profile): {ROUTE_KEYS}",
        f"- rescue keys (seen-scale early_sharp translation-vs-rotation): {RESCUE_KEYS}",
        f"- early_sharp sign keys (seen-scale translation-only): {EARLY_SIGN_KEYS}",
        '',
        '## N160 richer nuisance comparison',
        '',
        f"- baseline hybrid overall accuracy: {result['baseline_hybrid_accuracy']:.3f}",
        f"- baseline hybrid translation accuracy: {result['baseline_hybrid_translation_accuracy']:.3f}",
        f"- clean seen-scale candidate overall accuracy: {result['candidate_accuracy']:.3f}",
        f"- clean seen-scale candidate translation accuracy: {result['candidate_translation_accuracy']:.3f}",
        '',
        '## Candidate per-case accuracy',
        '',
    ]
    for case_name, acc in result['candidate_per_case_accuracy'].items():
        lines.append(f'- `{case_name}`: {acc:.3f}')
    lines.extend([
        '', '## Hard conclusion', '',
        '- A clean seen-scale-derived rescue rule is possible and does improve some vetoed early_sharp translation samples.',
        '- However, on the current N160 richer-nuisance panel it remains materially weaker than the earlier probe-informed rescue branch.',
        '- This means the project still lacks a clean cross-scale derivation of the early-translation rescue rule.',
        '- The probe-informed rescue remains a useful emergency branch, but not a promotable mainline mechanism.',
    ])
    (outdir / 'STAGE1_N160_SEEN_SCALE_EARLY_TRANSLATION_RESCUE_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote seen-scale early-translation rescue candidate audit to {outdir}')


if __name__ == '__main__':
    main()
