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
from scripts.analyze_stage1_hierarchical_stress_audit import load_stress_panel, zscore, accuracy
from scripts.analyze_stage1_n160_profile_aware_sign_candidate import apply_candidate
from scripts.analyze_stage1_n160_sign_drift_audit import load_translation_panel, zscore_against_n64


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Evaluate the N160 profile-aware sign candidate on a richer nuisance panel.')
    p.add_argument('--minimal-train-dir', type=str, default='outputs/stage1_scale_sign_audit_raw/N64')
    p.add_argument('--stress-root', type=str, default='outputs/stage1_hierarchical_stress_panel_raw')
    p.add_argument('--n160-stress-dir', type=str, default='outputs/stage1_n160_richer_nuisance_panel_raw/N160')
    p.add_argument('--translation-panel-root', type=str, default='outputs/stage1_translation_sign_scale_panel_raw')
    p.add_argument('--outdir', type=str, default='outputs/stage1_n160_richer_nuisance_candidate')
    return p.parse_args()


def per_case_accuracy(preds: list[dict[str, Any]]) -> dict[str, float]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in preds:
        groups.setdefault(p['case_name'], []).append(p)
    return {k: accuracy(v) for k, v in sorted(groups.items())}


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
        'protocol': 'stage1_n160_richer_nuisance_candidate',
        'n160_stress_dir': args.n160_stress_dir,
        'baseline_hybrid_per_case_accuracy': per_case_accuracy(result['baseline_hybrid_predictions']),
        'candidate_per_case_accuracy': per_case_accuracy(result['candidate_predictions']),
    })

    (outdir / 'stage1_n160_richer_nuisance_candidate_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        '# STAGE1 N160 RICHER NUISANCE CANDIDATE AUDIT',
        '',
        '## Goal',
        'Test whether the current N160 probe-informed profile-aware sparse sign candidate survives a richer nuisance panel at the same unseen scale without retuning gate behavior.',
        '',
        '## Status',
        '- candidate remains **candidate_only_not_promoted**',
        '- this audit checks whether the candidate is only memorizing the original N160 panel or can handle unseen nuisance profiles at the same scale',
        '',
        '## Overall comparison on richer N160 nuisance panel',
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
        '## Current hybrid per-case accuracy',
        '',
    ]
    for case_name, acc in result['baseline_hybrid_per_case_accuracy'].items():
        lines.append(f'- `{case_name}`: {acc:.3f}')
    lines.extend(['', '## Candidate per-case accuracy', ''])
    for case_name, acc in result['candidate_per_case_accuracy'].items():
        lines.append(f'- `{case_name}`: {acc:.3f}')

    if result['candidate_accuracy'] > result['baseline_hybrid_accuracy']:
        interp = 'candidate improves the richer nuisance probe at N160'
    elif result['candidate_accuracy'] < result['baseline_hybrid_accuracy']:
        interp = 'candidate does not survive the richer nuisance probe better than the current hybrid'
    else:
        interp = 'candidate ties the current hybrid on the richer nuisance probe'

    lines.extend([
        '',
        'Interpretation:',
        f'- {interp}',
        '- the result should still be treated as validation of a probe-informed branch, not as automatic promotion to mainline',
        '- promotion would require success on farther unseen scale or a cleaner derivation without using the N160 probe for branch selection',
    ])

    (outdir / 'STAGE1_N160_RICHER_NUISANCE_CANDIDATE_REPORT.md').write_text('\n'.join(lines))
    print(f'[OK] wrote richer nuisance candidate audit to {outdir}')


if __name__ == '__main__':
    main()
