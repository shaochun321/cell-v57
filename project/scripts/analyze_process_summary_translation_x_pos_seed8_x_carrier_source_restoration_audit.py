from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 x-carrier source restoration audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    analysis = {
        'suite': audit['suite'],
        'contracts': audit['contracts'],
        'inferred_primary_source': audit['inferred_primary_source'],
        'secondary_contributors': audit['secondary_contributors'],
        'seed7_active_translation_carrier_counts': audit['seed7']['active_translation_carrier_counts'],
        'seed8_active_translation_carrier_counts': audit['seed8']['active_translation_carrier_counts'],
        'seed7_phase_active_x_summary': audit['seed7']['phase_active_x_summary'],
        'seed8_phase_active_x_summary': audit['seed8']['phase_active_x_summary'],
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_x_carrier_source_restoration_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    shell_labels = ['shell_0', 'shell_1', 'shell_2', 'shell_3']
    seed7_counts = audit['seed7']['active_translation_carrier_counts']['per_shell']
    seed8_counts = audit['seed8']['active_translation_carrier_counts']['per_shell']
    seed7_vals = [int(seed7_counts.get(str(i), 0)) for i in range(4)]
    seed8_vals = [int(seed8_counts.get(str(i), 0)) for i in range(4)]

    fig = plt.figure(figsize=(8.4, 4.8))
    ax = fig.add_subplot(111)
    xs = list(range(len(shell_labels)))
    width = 0.34
    ax.bar([x - width / 2 for x in xs], seed7_vals, width=width, label='seed7 carriers')
    ax.bar([x + width / 2 for x in xs], seed8_vals, width=width, label='seed8 carriers')
    ax.set_xticks(xs, shell_labels)
    ax.set_ylabel('active translation carriers')
    ax.set_title('translation_x_pos active x-carrier shell inventory')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_x_carrier_source_restoration_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
