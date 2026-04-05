from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos seed8 shell2 second active-window retention restoration repair audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    baseline = audit['seed8_baseline']['phase_active_x_summary']
    repaired = audit['seed8_repaired']['phase_active_x_summary']
    baseline_shell2 = audit['seed8_baseline']['second_active_shell2_row']
    repaired_shell2 = audit['seed8_repaired']['second_active_shell2_row']

    summary = {
        'suite': audit['suite'],
        'contracts': audit['contracts'],
        'inferred_outcome': audit['inferred_outcome'],
        'residual_issue': audit['residual_issue'],
        'baseline_seed8_active_translation_carriers': audit['seed8_baseline']['active_translation_carrier_counts'],
        'repaired_seed8_active_translation_carriers': audit['seed8_repaired']['active_translation_carrier_counts'],
        'baseline_seed8_second_active_shell2': baseline_shell2,
        'repaired_seed8_second_active_shell2': repaired_shell2,
        'baseline_seed8_translation_x_pos_active_mean_polarity_projection': baseline['mean_polarity_projection'],
        'repaired_seed8_translation_x_pos_active_mean_polarity_projection': repaired['mean_polarity_projection'],
        'repeatability_failures': audit['repeatability_failures'],
    }
    (outdir / 'process_summary_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit_analysis.json').write_text(
        json.dumps(summary, indent=2),
        encoding='utf-8',
    )

    labels = ['baseline_shell2\nsecond_active', 'repaired_shell2\nsecond_active', 'baseline_xpos\nactive_mean', 'repaired_xpos\nactive_mean']
    values = [
        float(baseline_shell2.get('translation_like', 0.0) - baseline_shell2.get('static_like', 0.0)),
        float(repaired_shell2.get('translation_like', 0.0) - repaired_shell2.get('static_like', 0.0)),
        float(baseline['mean_polarity_projection']),
        float(repaired['mean_polarity_projection']),
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, values)
    ax.set_ylabel('value')
    ax.set_title('Round49 translation_x_pos seed8 shell2 second active-window retention restoration')
    ax.axhline(0.0, linewidth=1.0)
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_seed8_shell2_second_active_window_retention_restoration_repair_audit.png', dpi=160)


if __name__ == '__main__':
    main()
