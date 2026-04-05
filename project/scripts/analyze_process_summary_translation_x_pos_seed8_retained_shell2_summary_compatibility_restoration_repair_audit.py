from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 retained-shell2 summary compatibility restoration repair audit.')
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
        'seed8_round49_baseline': audit['seed8_round49_baseline']['phase_active_x_summary'],
        'seed8_round50_repaired': audit['seed8_round50_repaired']['phase_active_x_summary'],
        'seed8_round48_reference': audit['seed8_round48_reference']['phase_active_x_summary'],
        'guardrails': audit['guardrails'],
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_retained_shell2_summary_compatibility_restoration_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['round48', 'round49', 'round50']
    vals = [
        abs(float(audit['seed8_round48_reference']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_round49_baseline']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_round50_repaired']['phase_active_x_summary']['mean_polarity_projection'])),
    ]
    fig = plt.figure(figsize=(7.6, 4.6))
    ax = fig.add_subplot(111)
    ax.bar(labels, vals)
    ax.set_ylabel('abs(active mean polarity projection)')
    ax.set_title('seed8 translation_x_pos active summary compatibility: round48 vs round49 vs round50')
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_retained_shell2_summary_compatibility_restoration_repair_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
