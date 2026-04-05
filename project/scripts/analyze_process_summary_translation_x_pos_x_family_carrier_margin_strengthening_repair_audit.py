from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos x-family carrier margin strengthening repair audit.')
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
        'previous_round_seed8_translation_x_pos_gap_to_seed7': audit['previous_round_seed8_translation_x_pos_gap_to_seed7'],
        'seed8_translation_x_pos_gap_to_seed7': audit['seed8_translation_x_pos_gap_to_seed7'],
        'seed7': audit['seed7'],
        'seed8': audit['seed8'],
    }
    (outdir / 'process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['seed7 x_pos', 'seed8 x_pos', 'seed8 x_pos raw', 'seed8 x_pos carrier', 'seed8 x_pos margin-carrier']
    values = [
        float(audit['seed7']['translation_x_pos']['active_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_raw_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_carrier_mean_polarity_projection']),
        float(audit['seed8']['translation_x_pos']['active_margin_weighted_carrier_polarity_projection']),
    ]

    fig = plt.figure(figsize=(8.6, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.bar(range(len(labels)), values)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel('active polarity projection')
    ax.set_title('Round39 residual seed8 x-family carrier margin strengthening')
    ax.axhline(0.03, linestyle='--', linewidth=1.0)
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit.png', dpi=160)


if __name__ == '__main__':
    main()
