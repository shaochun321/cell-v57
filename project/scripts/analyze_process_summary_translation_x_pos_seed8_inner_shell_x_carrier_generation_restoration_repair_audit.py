from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 inner-shell x-carrier generation restoration repair audit.')
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
        'seed7_active_translation_carrier_counts': audit['seed7']['active_translation_carrier_counts'],
        'seed8_baseline_active_translation_carrier_counts': audit['seed8_baseline']['active_translation_carrier_counts'],
        'seed8_repaired_active_translation_carrier_counts': audit['seed8_repaired']['active_translation_carrier_counts'],
        'seed8_baseline_phase_active_x_summary': audit['seed8_baseline']['phase_active_x_summary'],
        'seed8_repaired_phase_active_x_summary': audit['seed8_repaired']['phase_active_x_summary'],
        'guardrails': audit['guardrails'],
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    shell_labels = ['shell_0', 'shell_1', 'shell_2', 'shell_3']
    baseline_counts = audit['seed8_baseline']['active_translation_carrier_counts']['per_shell']
    repaired_counts = audit['seed8_repaired']['active_translation_carrier_counts']['per_shell']
    baseline_vals = [int(baseline_counts.get(str(i), 0)) for i in range(4)]
    repaired_vals = [int(repaired_counts.get(str(i), 0)) for i in range(4)]

    fig = plt.figure(figsize=(8.8, 4.8))
    ax = fig.add_subplot(111)
    xs = list(range(len(shell_labels)))
    width = 0.34
    ax.bar([x - width / 2 for x in xs], baseline_vals, width=width, label='seed8 baseline')
    ax.bar([x + width / 2 for x in xs], repaired_vals, width=width, label='seed8 repaired')
    ax.set_xticks(xs, shell_labels)
    ax.set_ylabel('active translation carriers')
    ax.set_title('seed8 active x-carrier shell inventory: baseline vs repaired')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
