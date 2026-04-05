from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 inner-shell x-carrier amplitude source redesign repair audit.')
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
        'seed8_baseline_round52': audit['seed8_baseline_round52']['phase_active_x_summary'],
        'seed8_repaired_round54': audit['seed8_repaired_round54']['phase_active_x_summary'],
        'guardrails': audit['guardrails'],
        'gaps': audit['gaps'],
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['seed7', 'round52', 'round54']
    vals = [
        abs(float(audit['seed7_reference']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_baseline_round52']['phase_active_x_summary']['mean_polarity_projection'])),
        abs(float(audit['seed8_repaired_round54']['phase_active_x_summary']['mean_polarity_projection'])),
    ]
    raw_vals = [
        abs(float(audit['seed7_reference']['phase_active_x_summary'].get('raw_mean_polarity_projection', audit['seed7_reference']['phase_active_x_summary']['mean_polarity_projection']))),
        abs(float(audit['seed8_baseline_round52']['phase_active_x_summary']['raw_mean_polarity_projection'])),
        abs(float(audit['seed8_repaired_round54']['phase_active_x_summary']['raw_mean_polarity_projection'])),
    ]
    fig = plt.figure(figsize=(8.2, 4.8))
    ax = fig.add_subplot(111)
    x = range(len(labels))
    ax.bar([i - 0.18 for i in x], vals, width=0.36, label='final mean')
    ax.bar([i + 0.18 for i in x], raw_vals, width=0.36, label='raw mean')
    ax.set_xticks(list(x), labels)
    ax.set_ylabel('abs(active polarity projection)')
    ax.set_title('seed8 inner-shell amplitude source redesign: round52 vs round54')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_inner_shell_x_carrier_amplitude_source_redesign_repair_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
