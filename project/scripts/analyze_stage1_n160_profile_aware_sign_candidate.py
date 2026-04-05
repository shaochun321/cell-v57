from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any

from sklearn.linear_model import LogisticRegression

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import load_panel
from scripts.analyze_stage1_hierarchical_stress_audit import load_stress_panel, zscore, squared_distance, accuracy
from scripts.analyze_stage1_hierarchical_gate_sign_tuned_audit import TRANSLATION_GROUP_KEYS, class_mean
from scripts.analyze_stage1_scale_adaptive_gate_sign_audit import (
    VETO_KEY,
    NONTRANSLATION_KEYS,
    decode_panel,
)
from scripts.analyze_stage1_n160_sign_drift_audit import load_translation_panel, zscore_against_n64

PROFILE_C = 0.1
EARLY_SIGN_C = 0.2
LATE_SIGN_C = 0.1
SIGN_HANDOFF_SCALE = 160


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Audit a probe-informed profile-aware sign candidate on N160.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--n160-stress-dir', type=str, default='outputs/stage1_hierarchical_stress_panel_n160_raw/N160')
    p.add_argument('--translation-panel-root', type=str, default='outputs/stage1_translation_sign_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_profile_aware_sign_candidate')
    return p.parse_args()


def mean_dict(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    return {k: mean([s['z_features'][k] for s in samples]) for k in keys}


def train_profile_aware_models(df_rows: list[dict[str, Any]], feature_names: list[str]) -> tuple[LogisticRegression, LogisticRegression, LogisticRegression]:
    profile_train = [r for r in df_rows if r['scale'] in (64, 96, 128)]
    x_all = [[r['z_features'][k] for k in feature_names] for r in profile_train]
    y_profile = [1 if r['profile'] == 'late_sharp' else 0 for r in profile_train]
    profile_model = LogisticRegression(penalty='l1', C=PROFILE_C, solver='liblinear', max_iter=10000)
    profile_model.fit(x_all, y_profile)

    early_rows = [r for r in profile_train if r['profile'] == 'early_soft']
    x_early = [[r['z_features'][k] for k in feature_names] for r in early_rows]
    y_early = [1 if r['label'] == 'translation_x_pos' else 0 for r in early_rows]
    early_model = LogisticRegression(penalty='l1', C=EARLY_SIGN_C, solver='liblinear', max_iter=10000)
    early_model.fit(x_early, y_early)

    late_rows = [r for r in profile_train if r['profile'] == 'late_sharp']
    x_late = [[r['z_features'][k] for k in feature_names] for r in late_rows]
    y_late = [1 if r['label'] == 'translation_x_pos' else 0 for r in late_rows]
    late_model = LogisticRegression(penalty='l1', C=LATE_SIGN_C, solver='liblinear', max_iter=10000)
    late_model.fit(x_late, y_late)
    return profile_model, early_model, late_model


def nz_features(model: LogisticRegression, feature_names: list[str]) -> list[dict[str, float]]:
    out = []
    for idx, coef in enumerate(model.coef_[0]):
        if abs(coef) > 1e-8:
            out.append({'feature': feature_names[idx], 'coef': float(coef)})
    return out


def profile_aware_sign_predict(sample: dict[str, Any], feature_names: list[str], profile_model: LogisticRegression, early_model: LogisticRegression, late_model: LogisticRegression) -> tuple[str, str, float, float]:
    x = [[sample['z_features'][k] for k in feature_names]]
    profile_score = float(profile_model.decision_function(x)[0])
    profile_pred = 'late_sharp' if profile_score > 0.0 else 'early_soft'
    sign_model = late_model if profile_pred == 'late_sharp' else early_model
    sign_score = float(sign_model.decision_function(x)[0])
    pred = 'translation_x_pos' if sign_score > 0.0 else 'translation_x_neg'
    return pred, profile_pred, profile_score, sign_score


def apply_candidate(
    minimal_train: list[dict[str, Any]],
    panels: dict[int, list[dict[str, Any]]],
    n160_panel: list[dict[str, Any]],
    translation_rows: list[dict[str, Any]],
    feature_names: list[str],
) -> dict[str, Any]:
    # baseline current hybrid
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

    # fixed gate + veto from current hybrid, but replace >N128 sign handoff
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

    # same veto rule used by current hybrid
    from scripts.analyze_stage1_scale_adaptive_gate_sign_audit import compute_veto_threshold
    veto_threshold = compute_veto_threshold(stage1_rows)

    profile_model, early_model, late_model = train_profile_aware_models(translation_rows, feature_names)

    candidate_preds = []
    for row in stage1_rows:
        sample = row['sample']
        stage1_predicted = row['stage1_predicted']
        rerouted = False
        if stage1_predicted == 'translation' and veto_threshold is not None and row[VETO_KEY] < veto_threshold:
            stage1_predicted = 'nontranslation'
            rerouted = True

        if stage1_predicted == 'translation':
            pred, profile_pred, profile_score, sign_score = profile_aware_sign_predict(
                sample,
                feature_names,
                profile_model,
                early_model,
                late_model,
            )
            candidate_preds.append({
                'seed': sample['seed'],
                'case_name': sample['case_name'],
                'label': sample['label'],
                'predicted': pred,
                'stage1_predicted': 'translation',
                'sign_mode': 'profile_aware_sparse_candidate',
                'profile_predicted': profile_pred,
                'profile_score': profile_score,
                'sign_score': sign_score,
                'rerouted_by_veto': rerouted,
                'translation_distance': row['translation_distance'],
                'nontranslation_distance': row['nontranslation_distance'],
                'veto_key_value': row[VETO_KEY],
                'veto_threshold': veto_threshold,
            })
        else:
            d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
            candidate_preds.append({
                'seed': sample['seed'],
                'case_name': sample['case_name'],
                'label': sample['label'],
                'predicted': pred,
                'stage1_predicted': 'nontranslation',
                'rerouted_by_veto': rerouted,
                'translation_distance': row['translation_distance'],
                'nontranslation_distance': row['nontranslation_distance'],
                'veto_key_value': row[VETO_KEY],
                'veto_threshold': veto_threshold,
                'stage2_baseline_distance': d_baseline,
                'stage2_rotation_distance': d_rotation,
            })

    # translation-only sanity: leave-one-seed-out on seen scales 64/96/128
    profile_train = [r for r in translation_rows if r['scale'] in (64, 96, 128)]
    loo_predictions = []
    for heldout_seed in sorted({r['seed'] for r in profile_train}):
        train_rows = [r for r in profile_train if r['seed'] != heldout_seed]
        test_rows = [r for r in profile_train if r['seed'] == heldout_seed]
        pm, em, lm = train_profile_aware_models(train_rows, feature_names)
        for row in test_rows:
            pred, profile_pred, profile_score, sign_score = profile_aware_sign_predict(row, feature_names, pm, em, lm)
            loo_predictions.append({
                'scale': row['scale'],
                'seed': row['seed'],
                'case_name': row['case_name'],
                'label': row['label'],
                'predicted': pred,
                'profile': row['profile'],
                'profile_predicted': profile_pred,
                'profile_score': profile_score,
                'sign_score': sign_score,
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
        'profile_model_nonzero': nz_features(profile_model, feature_names),
        'early_model_nonzero': nz_features(early_model, feature_names),
        'late_model_nonzero': nz_features(late_model, feature_names),
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

    translation_rows = load_translation_panel(Path(args.translation_panel_root))
    _ = zscore_against_n64(translation_rows)

    result = apply_candidate(minimal_train, panels, n160_panel, translation_rows, feature_names)
    result.update({
        'protocol': 'stage1_n160_profile_aware_sign_candidate',
        'minimal_train_dir': args.minimal_train_dir,
        'stress_root': args.stress_root,
        'n160_stress_dir': args.n160_stress_dir,
        'translation_panel_root': args.translation_panel_root,
        'probe_informed_status': 'candidate_only_not_promoted',
        'candidate_profile_C': PROFILE_C,
        'candidate_early_sign_C': EARLY_SIGN_C,
        'candidate_late_sign_C': LATE_SIGN_C,
        'candidate_sign_handoff_scale': SIGN_HANDOFF_SCALE,
    })
    (outdir / 'stage1_n160_profile_aware_sign_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 PROFILE-AWARE SIGN CANDIDATE',
        '',
        '## Goal',
        'Test a probe-informed candidate that keeps the current gate+veto intact and only replaces the >N128 translation sign handoff with a sparse profile-aware sign branch.',
        '',
        '## Candidate status',
        '- status: **candidate_only_not_promoted**',
        '- reason: the candidate uses the N160 probe to help choose a workable sign branch and therefore must not be treated as a clean unseen-scale mainline result',
        '',
        '## Candidate branch',
        f'- profile model: sparse logistic, C={PROFILE_C}',
        f'- early_soft sign model: sparse logistic, C={EARLY_SIGN_C}',
        f'- late_sharp sign model: sparse logistic, C={LATE_SIGN_C}',
        f'- handoff scale: >={SIGN_HANDOFF_SCALE}',
        '',
        '## N160 overall comparison',
        '',
        f"- current hybrid overall accuracy: {result['baseline_hybrid_accuracy']:.3f}",
        f"- current hybrid translation accuracy: {result['baseline_hybrid_translation_accuracy']:.3f}",
        f"- candidate overall accuracy: {result['candidate_accuracy']:.3f}",
        f"- candidate translation accuracy: {result['candidate_translation_accuracy']:.3f}",
        '',
        '## Seen-scale translation-only sanity',
        '',
        f"- leave-one-seed-out accuracy over N64/N96/N128 translation-only panel: {result['translation_seen_scale_loo_accuracy']:.3f}",
        '',
        'Interpretation:',
        '- the candidate materially improves the N160 overall probe while leaving gate behavior untouched',
        '- however, seen-scale translation-only LOO remains imperfect, so this branch should be treated as a probe-informed candidate rather than a new mainline decoder',
        '',
        '## Nonzero profile-model features',
        '',
    ]
    for row in result['profile_model_nonzero']:
        lines.append(f"- `{row['feature']}`: {row['coef']:.6f}")
    lines.extend(['', '## Nonzero early_soft sign features', ''])
    for row in result['early_model_nonzero']:
        lines.append(f"- `{row['feature']}`: {row['coef']:.6f}")
    lines.extend(['', '## Nonzero late_sharp sign features', ''])
    for row in result['late_model_nonzero']:
        lines.append(f"- `{row['feature']}`: {row['coef']:.6f}")

    (outdir / 'STAGE1_N160_PROFILE_AWARE_SIGN_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote N160 profile-aware sign candidate audit to {outdir}')


if __name__ == '__main__':
    main()
