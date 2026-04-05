from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos active polarity amplitude strengthening repair audit.')
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
        'seed7': audit['seed7'],
        'seed8': audit['seed8'],
        'seed8_translation_x_pos_gap_to_seed7': audit['seed8_translation_x_pos_gap_to_seed7'],
    }
    (outdir / 'process_summary_translation_x_pos_active_polarity_amplitude_strengthening_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['seed7 x_pos', 'seed8 x_pos', 'seed7 x_neg', 'seed8 x_neg']
    raw_values = [
        float(audit['seed7']['translation_x_pos']['active_raw_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_raw_mean_polarity_projection']),
        float(audit['seed7']['translation_x_neg']['active_raw_mean_polarity_projection']),
        float(audit['seed8']['translation_x_neg']['active_raw_mean_polarity_projection']),
    ]
    repaired_values = [
        float(audit['seed7']['translation_x_pos']['active_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_mean_polarity_projection']),
        float(audit['seed7']['translation_x_neg']['active_mean_polarity_projection']),
        float(audit['seed8']['translation_x_neg']['active_mean_polarity_projection']),
    ]

    xs = range(len(labels))
    fig = plt.figure(figsize=(8.8, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.bar([x - 0.18 for x in xs], raw_values, width=0.36, label='raw mean polarity')
    ax.bar([x + 0.18 for x in xs], repaired_values, width=0.36, label='repaired mean polarity')
    ax.axhline(0.03, linestyle='--', linewidth=1.0)
    ax.axhline(-0.03, linestyle='--', linewidth=1.0)
    ax.set_xticks(list(xs), labels)
    ax.set_ylabel('active polarity projection')
    ax.set_title('Round37 active polarity amplitude strengthening')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_active_polarity_amplitude_strengthening_repair_audit.png', dpi=160)


if __name__ == '__main__':
    main()
