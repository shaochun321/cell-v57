from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import load_panel
from scripts.analyze_stage1_hierarchical_stress_audit import load_stress_panel, zscore, squared_distance, accuracy
from scripts.analyze_stage1_hierarchical_gate_sign_tuned_audit import TRANSLATION_GROUP_KEYS, class_mean
from scripts.analyze_stage1_scale_adaptive_gate_sign_audit import compute_veto_threshold, VETO_KEY, NONTRANSLATION_KEYS, decode_panel
from scripts.analyze_stage1_n160_profile_aware_sign_candidate import train_profile_aware_models, profile_aware_sign_predict, nz_features
from scripts.analyze_stage1_translation_richer_profile_scale_audit import load_panel as load_translation_richer_panel, zscore_against_n64 as zscore_translation_richer

EARLY_ROUTE_KEYS = [
    'local_propagation_track_dissipation_load',
    'discrete_channel_track_bandwidth_shell_3',
]
EARLY_SIGN_KEYS = ['layered_coupling_track_axisbal_x']
PROFILE_C = 0.1
EARLY_SIGN_C = 0.2
LATE_SIGN_C = 0.1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate an early-routed N160 sign candidate on richer nuisance panel.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--n160-stress-dir', type=str, default='outputs/stage1_n160_richer_nuisance_panel_raw/N160')
    p.add_argument('--translation-panel-root', type=str, default='outputs/stage1_translation_sign_scale_panel_raw')
    p.add_argument('--translation-richer-profile-root', type=str, default='outputs/stage1_translation_richer_profile_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_early_routed_sign_candidate')
    return p.parse_args()


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def fit_linear_centers(rows: list[dict[str, Any]], keys: list[str], predicate) -> dict[str, tuple[float, float]]:
    def radius_coord(num_cells: int) -> float:
        return num_cells ** (1.0 / 3.0)
    out = {}
    for key in keys:
        xs, ys = [], []
        for scale in [64, 96, 128]:
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
    r = scale ** (1.0 / 3.0)
    return {k: a * r + b for k, (a, b) in params.items()}


def early_route_predict(sample: dict[str, Any], early_rows: list[dict[str, Any]]) -> tuple[str, float, float]:
    early_params = fit_linear_centers(early_rows, EARLY_ROUTE_KEYS, lambda r: r['profile'] == 'early_sharp')
    nonearly_params = fit_linear_centers(early_rows, EARLY_ROUTE_KEYS, lambda r: r['profile'] != 'early_sharp')
    scale = int(sample.get('scale', 160))
    early_center = center_from_linear(early_params, scale)
    nonearly_center = center_from_linear(nonearly_params, scale)
    d_early = sum((sample['z_features'][k] - early_center[k]) ** 2 for k in EARLY_ROUTE_KEYS)
    d_nonearly = sum((sample['z_features'][k] - nonearly_center[k]) ** 2 for k in EARLY_ROUTE_KEYS)
    pred = 'early_sharp' if d_early < d_nonearly else 'not_early_sharp'
    return pred, d_early, d_nonearly


def early_sign_predict(sample: dict[str, Any], early_rows: list[dict[str, Any]]) -> tuple[str, float, float]:
    pos_params = fit_linear_centers(early_rows, EARLY_SIGN_KEYS, lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_pos')
    neg_params = fit_linear_centers(early_rows, EARLY_SIGN_KEYS, lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_neg')
    scale = int(sample.get('scale', 160))
    pos_center = center_from_linear(pos_params, scale)
    neg_center = center_from_linear(neg_params, scale)
    d_pos = sum((sample['z_features'][k] - pos_center[k]) ** 2 for k in EARLY_SIGN_KEYS)
    d_neg = sum((sample['z_features'][k] - neg_center[k]) ** 2 for k in EARLY_SIGN_KEYS)
    pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
    return pred, d_pos, d_neg


def per_case_accuracy(preds: list[dict[str, Any]]) -> dict[str, float]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in preds:
        groups.setdefault(p['case_name'], []).append(p)
    return {k: accuracy(v) for k, v in sorted(groups.items())}


def apply_candidate(minimal_train, panels, n160_panel, translation_rows_old, translation_rows_richer, feature_names):
    sign_calibration = {
        64: [s for s in panels[64] if s['label'].startswith('translation')],
        96: [s for s in panels[96] if s['label'].startswith('translation')],
    }
    baseline_preds, baseline_veto = decode_panel(
        panels[64],
        panels[64] + panels[96],
        sign_calibration,
        minimal_train,
        n160_panel,
        160,
    )

    translation_center = class_mean(panels[64], lambda s: s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    nontranslation_center = class_mean(panels[64], lambda s: not s['label'].startswith('translation'), TRANSLATION_GROUP_KEYS)
    baseline_center = mean_dict([s for s in panels[64] + panels[96] if s['label'] == 'baseline'], NONTRANSLATION_KEYS)
    rotation_center = mean_dict([s for s in panels[64] + panels[96] if s['label'] == 'rotation_z_pos'], NONTRANSLATION_KEYS)

    stage1_rows = []
    for sample in n160_panel:
        d_translation = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
        d_nontranslation = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
        stage1_rows.append({
            'sample': sample,
            'translation_distance': d_translation,
            'nontranslation_distance': d_nontranslation,
            'stage1_predicted': 'translation' if d_translation < d_nontranslation else 'nontranslation',
            VETO_KEY: sample['z_features'][VETO_KEY],
        })
    veto_threshold = compute_veto_threshold(stage1_rows)

    # fallback non-early sign models from old panel
    old_feature_names = list(translation_rows_old[0]['z_features'].keys())
    profile_model, early_model, late_model = train_profile_aware_models(translation_rows_old, old_feature_names)

    candidate_preds = []
    for row in stage1_rows:
        sample = row['sample']
        stage1_predicted = row['stage1_predicted']
        rerouted = False
        if stage1_predicted == 'translation' and veto_threshold is not None and row[VETO_KEY] < veto_threshold:
            stage1_predicted = 'nontranslation'
            rerouted = True
        if stage1_predicted == 'translation':
            route_pred, d_early, d_nonearly = early_route_predict(sample, translation_rows_richer)
            if route_pred == 'early_sharp':
                pred, d_pos, d_neg = early_sign_predict(sample, translation_rows_richer)
                candidate_preds.append({
                    'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                    'stage1_predicted': 'translation', 'sign_mode': 'early_routed_sign_candidate',
                    'profile_predicted': route_pred, 'route_d_early': d_early, 'route_d_nonearly': d_nonearly,
                    'sign_d_pos': d_pos, 'sign_d_neg': d_neg, 'rerouted_by_veto': rerouted,
                    'translation_distance': row['translation_distance'], 'nontranslation_distance': row['nontranslation_distance'],
                })
            else:
                pred, profile_pred, profile_score, sign_score = profile_aware_sign_predict(sample, old_feature_names, profile_model, early_model, late_model)
                candidate_preds.append({
                    'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                    'stage1_predicted': 'translation', 'sign_mode': 'fallback_profile_sparse_candidate',
                    'profile_predicted': profile_pred, 'profile_score': profile_score, 'sign_score': sign_score,
                    'route_d_early': d_early, 'route_d_nonearly': d_nonearly,
                    'rerouted_by_veto': rerouted,
                    'translation_distance': row['translation_distance'], 'nontranslation_distance': row['nontranslation_distance'],
                })
        else:
            d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
            candidate_preds.append({
                'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                'stage1_predicted': 'nontranslation', 'rerouted_by_veto': rerouted,
                'translation_distance': row['translation_distance'], 'nontranslation_distance': row['nontranslation_distance'],
                'stage2_baseline_distance': d_baseline, 'stage2_rotation_distance': d_rotation,
            })

    # sanity on seen scales using richer translation panel only
    loo_predictions=[]
    all_rows = [r for r in translation_rows_richer if r['scale'] in (64,96,128)]
    for heldout_seed in sorted({r['seed'] for r in all_rows}):
        train_rows = [r for r in all_rows if r['seed'] != heldout_seed]
        test_rows = [r for r in all_rows if r['seed'] == heldout_seed]
        old_train = [r for r in translation_rows_old if r['scale'] in (64,96,128) and r['seed'] != heldout_seed]
        pm, em, lm = train_profile_aware_models(old_train, old_feature_names)
        for sample in test_rows:
            route_pred, d_early, d_nonearly = early_route_predict(sample, train_rows)
            if route_pred == 'early_sharp':
                pred, d_pos, d_neg = early_sign_predict(sample, train_rows)
            else:
                pred, profile_pred, profile_score, sign_score = profile_aware_sign_predict(sample, old_feature_names, pm, em, lm)
            loo_predictions.append({
                'scale': sample['scale'], 'seed': sample['seed'], 'case_name': sample['case_name'],
                'label': sample['label'], 'predicted': pred, 'profile': sample['profile'], 'route_predicted': route_pred,
            })

    return {
        'baseline_hybrid_predictions': baseline_preds,
        'baseline_hybrid_accuracy': accuracy(baseline_preds),
        'baseline_hybrid_translation_accuracy': accuracy([p for p in baseline_preds if p['label'].startswith('translation')]),
        'candidate_predictions': candidate_preds,
        'candidate_accuracy': accuracy(candidate_preds),
        'candidate_translation_accuracy': accuracy([p for p in candidate_preds if p['label'].startswith('translation')]),
        'candidate_veto_threshold': veto_threshold,
        'translation_seen_scale_loo_predictions': loo_predictions,
        'translation_seen_scale_loo_accuracy': accuracy(loo_predictions),
        'route_keys': EARLY_ROUTE_KEYS,
        'early_sign_keys': EARLY_SIGN_KEYS,
        'fallback_profile_model_nonzero': nz_features(profile_model, old_feature_names),
        'fallback_early_model_nonzero': nz_features(early_model, old_feature_names),
        'fallback_late_model_nonzero': nz_features(late_model, old_feature_names),
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    minimal_train = load_panel(Path(args.minimal_train_dir))
    feature_names = list(minimal_train[0]['features'].keys())
    means = {k: mean([s['features'][k] for s in minimal_train]) for k in feature_names}
    stds: dict[str, float] = {}
    for k in feature_names:
        var = mean([(s['features'][k] - means[k]) ** 2 for s in minimal_train])
        stds[k] = math.sqrt(var) if var > 0.0 else 1.0
    for sample in minimal_train:
        sample['z_features'] = {k: (sample['features'][k] - means[k]) / stds[k] for k in feature_names}

    panels: dict[int, list[dict[str, Any]]] = {}
    for scale in [64, 96]:
        panel = load_stress_panel(Path(args.stress_root) / f'N{scale}')
        zscore(panel, feature_names, means, stds)
        panels[scale] = panel
    n160_panel = load_stress_panel(Path(args.n160_stress_dir))
    zscore(n160_panel, feature_names, means, stds)

    from scripts.analyze_stage1_n160_sign_drift_audit import load_translation_panel, zscore_against_n64
    translation_rows_old = load_translation_panel(Path(args.translation_panel_root))
    _ = zscore_against_n64(translation_rows_old)
    translation_rows_richer = load_translation_richer_panel(Path(args.translation_richer_profile_root))
    _ = zscore_translation_richer(translation_rows_richer)

    result = apply_candidate(minimal_train, panels, n160_panel, translation_rows_old, translation_rows_richer, feature_names)
    result.update({
        'protocol': 'stage1_n160_early_routed_sign_candidate',
        'n160_stress_dir': args.n160_stress_dir,
        'translation_richer_profile_root': args.translation_richer_profile_root,
    })
    result['baseline_hybrid_per_case_accuracy'] = per_case_accuracy(result['baseline_hybrid_predictions'])
    result['candidate_per_case_accuracy'] = per_case_accuracy(result['candidate_predictions'])

    (outdir / 'stage1_n160_early_routed_sign_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 EARLY-ROUTED SIGN CANDIDATE', '',
        '## Goal',
        'Inject an explicit early_sharp routing branch into the N160 richer nuisance decoder, using clean early_sharp cross-scale observables, while keeping gate/veto fixed and using the previous sparse candidate as fallback for non-early translation.', '',
        '## Comparison on N160 richer nuisance panel', '',
        f"- current hybrid overall accuracy: {result['baseline_hybrid_accuracy']:.3f}",
        f"- current hybrid translation accuracy: {result['baseline_hybrid_translation_accuracy']:.3f}",
        f"- early-routed candidate overall accuracy: {result['candidate_accuracy']:.3f}",
        f"- early-routed candidate translation accuracy: {result['candidate_translation_accuracy']:.3f}", '',
        '## Seen-scale richer translation sanity', '',
        f"- leave-one-seed-out accuracy over N64/N96/N128 richer translation panel: {result['translation_seen_scale_loo_accuracy']:.3f}", '',
        '## Route/sign keys', '',
        f"- early route keys: {EARLY_ROUTE_KEYS}",
        f"- early sign keys: {EARLY_SIGN_KEYS}", '',
        '## Candidate per-case accuracy', '',
    ]
    for case_name, acc in result['candidate_per_case_accuracy'].items():
        lines.append(f'- `{case_name}`: {acc:.3f}')
    lines.extend(['', '## Hard conclusion', ''])
    if result['candidate_accuracy'] > result['baseline_hybrid_accuracy']:
        lines.append('- Explicit early_sharp routing improves the richer N160 nuisance probe over the current hybrid baseline.')
    else:
        lines.append('- Explicit early_sharp routing does not improve the richer N160 nuisance probe over the current hybrid baseline.')
    lines.extend([
        '- This candidate is still a readout-side experiment; it does not reopen the physical core.',
        '- Promotion would require both better N160 nuisance performance and acceptable seen-scale richer-translation sanity.',
    ])
    (outdir / 'STAGE1_N160_EARLY_ROUTED_SIGN_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote early-routed sign candidate audit to {outdir}')


if __name__ == '__main__':
    main()
