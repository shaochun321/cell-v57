from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze the M2 inner-core source continuity redesign audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    payload = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    baseline = payload['seed8_baseline_round54']['phase_active_x_summary']
    repaired = payload['seed8_repaired_m2']['phase_active_x_summary']
    analysis = {
        'headline': payload['headline'],
        'decision': payload['decision'],
        'baseline_final_mean': float(baseline['mean_polarity_projection']),
        'repaired_final_mean': float(repaired['mean_polarity_projection']),
        'baseline_raw_mean': float(baseline['raw_mean_polarity_projection']),
        'repaired_raw_mean': float(repaired['raw_mean_polarity_projection']),
        'baseline_carrier_total': int(payload['seed8_baseline_round54']['active_translation_carrier_counts']['total']),
        'repaired_carrier_total': int(payload['seed8_repaired_m2']['active_translation_carrier_counts']['total']),
        'evidence': payload['evidence'],
        'residual_issue': payload['residual_issue'],
    }
    (outdir / 'process_summary_translation_x_pos_m2_inner_core_source_continuity_redesign_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    labels = ['raw mean', 'final mean', 'carrier total']
    baseline_vals = [analysis['baseline_raw_mean'], analysis['baseline_final_mean'], analysis['baseline_carrier_total']]
    repaired_vals = [analysis['repaired_raw_mean'], analysis['repaired_final_mean'], analysis['repaired_carrier_total']]
    x = range(len(labels))
    plt.figure(figsize=(8, 4.8))
    plt.plot(list(x), baseline_vals, marker='o', label='round54 baseline')
    plt.plot(list(x), repaired_vals, marker='o', label='m2 redesign')
    plt.xticks(list(x), labels)
    plt.ylabel('value')
    plt.title('M2 inner-core source continuity redesign audit')
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / 'process_summary_translation_x_pos_m2_inner_core_source_continuity_redesign_audit.png', dpi=160)


if __name__ == '__main__':
    main()
