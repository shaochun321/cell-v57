from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 residual x-carrier amplitude restoration repair audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    analysis = {
        'suite': audit['suite'],
        'contracts': audit['contracts'],
        'inferred_outcome': audit['inferred_outcome'],
        'residual_issue': audit['residual_issue'],
        'repeatability_failures': audit['repeatability_failures'],
        'seed7_reference': audit['seed7_reference']['phase_active_x_summary'],
        'seed8_round50_baseline': audit['seed8_round50_baseline']['phase_active_x_summary'],
        'seed8_round52_repaired': audit['seed8_round52_repaired']['phase_active_x_summary'],
        'guardrails': audit['guardrails'],
        'gaps': audit['gaps'],
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_residual_x_carrier_amplitude_restoration_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['seed7', 'round50', 'round52']
    vals = [
        abs(float(audit['seed7_reference']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_round50_baseline']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_round52_repaired']['phase_active_x_summary']['mean_polarity_projection'])),
    ]
    fig = plt.figure(figsize=(7.6, 4.6))
    ax = fig.add_subplot(111)
    ax.bar(labels, vals)
    ax.set_ylabel('abs(active mean polarity projection)')
    ax.set_title('seed8 translation_x_pos residual x-carrier amplitude restoration: round50 vs round52')
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_residual_x_carrier_amplitude_restoration_repair_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
