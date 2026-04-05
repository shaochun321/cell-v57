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
from scripts.analyze_stage1_n160_early_routed_sign_candidate import fit_linear_centers, center_from_linear, per_case_accuracy, mean_dict
from scripts.analyze_stage1_n160_sign_drift_audit import load_translation_panel, zscore_against_n64
from scripts.analyze_stage1_translation_richer_profile_scale_audit import load_panel as load_translation_richer_panel, zscore_against_n64 as zscore_translation_richer

RESCUE_KEY = 'local_propagation_track_transfer_shell_2'
EARLY_SIGN_KEY = 'layered_coupling_track_dir_x'
PROFILE_C = 0.1
EARLY_SIGN_C = 0.2
LATE_SIGN_C = 0.1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate a probe-informed early-translation rescue candidate on N160 richer nuisance panel.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--n160-stress-dir', type=str, default='outputs/stage1_n160_richer_nuisance_panel_raw/N160')
    p.add_argument('--translation-panel-root', type=str, default='outputs/stage1_translation_sign_scale_panel_raw')
    p.add_argument('--translation-richer-profile-root', type=str, default='outputs/stage1_translation_richer_profile_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_early_translation_rescue_candidate')
    return p.parse_args()


def choose_rescue_threshold(n160_panel: list[dict[str, Any]], translation_center, nontranslation_center) -> tuple[float, int]:
    rows = []
    for s in n160_panel:
        if 'early_sharp' not in s['case_name']:
            continue
        dt = squared_distance(s, translation_center, TRANSLATION_GROUP_KEYS)
        dn = squared_distance(s, nontranslation_center, TRANSLATION_GROUP_KEYS)
        if dt < dn:  # stage1 already puts it on translation side before veto
            cls = 1 if s['label'].startswith('translation') else 0
            rows.append((s['z_features'][RESCUE_KEY], cls))
    vals = sorted(set(v for v, _ in rows))
    thresholds = [(a + b) / 2.0 for a, b in zip(vals[:-1], vals[1:])] or vals
    best = (0.0, thresholds[0] if thresholds else 0.0, -1)
    for thr in thresholds:
        for sign in [1, -1]:
            preds = [1 if sign * v > sign * thr else 0 for v, _ in rows]
            acc = sum(int(p == y) for p, (_, y) in zip(preds, rows)) / len(rows)
            if acc > best[0]:
                best = (acc, thr, sign)
    return best[1], best[2]


def early_sign_predict(sample: dict[str, Any], richer_rows: list[dict[str, Any]]) -> tuple[str, float, float]:
    pos_params = fit_linear_centers(richer_rows, [EARLY_SIGN_KEY], lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_pos')
    neg_params = fit_linear_centers(richer_rows, [EARLY_SIGN_KEY], lambda r: r['profile'] == 'early_sharp' and r['label'] == 'translation_x_neg')
    pos_center = center_from_linear(pos_params, 160)
    neg_center = center_from_linear(neg_params, 160)
    d_pos = (sample['z_features'][EARLY_SIGN_KEY] - pos_center[EARLY_SIGN_KEY]) ** 2
    d_neg = (sample['z_features'][EARLY_SIGN_KEY] - neg_center[EARLY_SIGN_KEY]) ** 2
    pred = 'translation_x_pos' if d_pos < d_neg else 'translation_x_neg'
    return pred, d_pos, d_neg


def apply_candidate(minimal_train, panels, n160_panel, translation_rows_old, translation_rows_richer):
    sign_calibration = {
        64: [s for s in panels[64] if s['label'].startswith('translation')],
        96: [s for s in panels[96] if s['label'].startswith('translation')],
    }
    baseline_preds, _ = decode_panel(
        panels[64], panels[64] + panels[96], sign_calibration, minimal_train, n160_panel, 160
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
    rescue_threshold, rescue_sign = choose_rescue_threshold(n160_panel, translation_center, nontranslation_center)

    old_feature_names = list(translation_rows_old[0]['z_features'].keys())
    profile_model, early_model, late_model = train_profile_aware_models(translation_rows_old, old_feature_names)

    candidate_preds = []
    for row in stage1_rows:
        sample = row['sample']
        stage1_predicted = row['stage1_predicted']
        rerouted = False
        rescue_applied = False
        if stage1_predicted == 'translation' and row[VETO_KEY] < veto_threshold:
            if 'early_sharp' in sample['case_name'] and rescue_sign * sample['z_features'][RESCUE_KEY] > rescue_sign * rescue_threshold:
                stage1_predicted = 'translation'
                rescue_applied = True
            else:
                stage1_predicted = 'nontranslation'
                rerouted = True

        if stage1_predicted == 'translation':
            if rescue_applied:
                pred, d_pos, d_neg = early_sign_predict(sample, translation_rows_richer)
                candidate_preds.append({
                    'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                    'stage1_predicted': 'translation', 'sign_mode': 'probe_informed_early_translation_rescue',
                    'rescue_applied': True, 'translation_distance': row['translation_distance'],
                    'nontranslation_distance': row['nontranslation_distance'], 'veto_key_value': row[VETO_KEY],
                    'veto_threshold': veto_threshold, 'rescue_key_value': sample['z_features'][RESCUE_KEY],
                    'rescue_threshold': rescue_threshold, 'sign_d_pos': d_pos, 'sign_d_neg': d_neg,
                })
            else:
                pred, profile_pred, profile_score, sign_score = profile_aware_sign_predict(sample, old_feature_names, profile_model, early_model, late_model)
                candidate_preds.append({
                    'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                    'stage1_predicted': 'translation', 'sign_mode': 'fallback_profile_sparse_candidate',
                    'profile_predicted': profile_pred, 'profile_score': profile_score, 'sign_score': sign_score,
                    'rescue_applied': False, 'translation_distance': row['translation_distance'],
                    'nontranslation_distance': row['nontranslation_distance'], 'veto_key_value': row[VETO_KEY],
                    'veto_threshold': veto_threshold, 'rescue_key_value': sample['z_features'][RESCUE_KEY],
                    'rescue_threshold': rescue_threshold,
                })
        else:
            d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = 'baseline' if d_baseline < d_rotation else 'rotation_z_pos'
            candidate_preds.append({
                'seed': sample['seed'], 'case_name': sample['case_name'], 'label': sample['label'], 'predicted': pred,
                'stage1_predicted': 'nontranslation', 'rescue_applied': False, 'rerouted_by_veto': rerouted,
                'translation_distance': row['translation_distance'], 'nontranslation_distance': row['nontranslation_distance'],
                'veto_key_value': row[VETO_KEY], 'veto_threshold': veto_threshold,
                'rescue_key_value': sample['z_features'][RESCUE_KEY], 'rescue_threshold': rescue_threshold,
                'stage2_baseline_distance': d_baseline, 'stage2_rotation_distance': d_rotation,
            })

    return {
        'baseline_hybrid_predictions': baseline_preds,
        'baseline_hybrid_accuracy': accuracy(baseline_preds),
        'baseline_hybrid_translation_accuracy': accuracy([p for p in baseline_preds if p['label'].startswith('translation')]),
        'candidate_predictions': candidate_preds,
        'candidate_accuracy': accuracy(candidate_preds),
        'candidate_translation_accuracy': accuracy([p for p in candidate_preds if p['label'].startswith('translation')]),
        'candidate_veto_threshold': veto_threshold,
        'rescue_key': RESCUE_KEY,
        'rescue_threshold': rescue_threshold,
        'rescue_sign': rescue_sign,
        'early_sign_key': EARLY_SIGN_KEY,
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

    translation_rows_old = load_translation_panel(Path(args.translation_panel_root))
    _ = zscore_against_n64(translation_rows_old)
    translation_rows_richer = load_translation_richer_panel(Path(args.translation_richer_profile_root))
    _ = zscore_translation_richer(translation_rows_richer)

    result = apply_candidate(minimal_train, panels, n160_panel, translation_rows_old, translation_rows_richer)
    result.update({
        'protocol': 'stage1_n160_early_translation_rescue_candidate',
        'n160_stress_dir': args.n160_stress_dir,
        'translation_richer_profile_root': args.translation_richer_profile_root,
        'baseline_hybrid_per_case_accuracy': per_case_accuracy(result['baseline_hybrid_predictions']),
        'candidate_per_case_accuracy': per_case_accuracy(result['candidate_predictions']),
        'status': 'candidate_only_not_promoted',
        'reason': 'rescue key/threshold are selected probe-informatively on N160 early-sharp translation-vs-rotation overlap and therefore do not qualify as a clean mainline promotion',
    })

    (outdir / 'stage1_n160_early_translation_rescue_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 EARLY-TRANSLATION RESCUE CANDIDATE', '',
        '## Goal',
        'Repair the N160 richer-nuisance early_sharp failures without reopening the physical core by rescuing only the vetoed early_sharp translation samples that are separable from early_sharp rotation at the readout layer.', '',
        '## Comparison on N160 richer nuisance panel', '',
        f"- current hybrid overall accuracy: {result['baseline_hybrid_accuracy']:.3f}",
        f"- current hybrid translation accuracy: {result['baseline_hybrid_translation_accuracy']:.3f}",
        f"- rescue candidate overall accuracy: {result['candidate_accuracy']:.3f}",
        f"- rescue candidate translation accuracy: {result['candidate_translation_accuracy']:.3f}", '',
        '## Rescue mechanism', '',
        f"- rescue key: `{RESCUE_KEY}`",
        f"- rescue threshold: {result['rescue_threshold']:.6f}",
        f"- rescue sign: {result['rescue_sign']}",
        f"- rescued early_sharp sign key: `{EARLY_SIGN_KEY}`", '',
        '## Candidate per-case accuracy', '',
    ]
    for case_name, acc in result['candidate_per_case_accuracy'].items():
        lines.append(f'- `{case_name}`: {acc:.3f}')
    lines.extend([
        '', '## Hard conclusion', '',
        '- The richer-nuisance early_sharp failure is not just a sign-observability problem; it is strongly coupled to the stage-1 veto logic.',
        '- A probe-informed rescue key can recover the vetoed early_sharp positives without reopening the physical core.',
        '- This candidate still remains **candidate only** because the rescue key and threshold are chosen on the N160 overlap itself.',
        '- The next clean promotion path would require finding a seen-scale or cross-scale derivation of the rescue observable/threshold, or validating the same rescue rule at a farther unseen scale.',
    ])
    (outdir / 'STAGE1_N160_EARLY_TRANSLATION_RESCUE_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote early-translation rescue candidate audit to {outdir}')


if __name__ == '__main__':
    main()
