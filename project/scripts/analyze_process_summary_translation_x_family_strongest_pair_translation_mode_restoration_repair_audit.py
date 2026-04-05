from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x family strongest-pair translation-mode restoration repair audit.')
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
    }
    (outdir / 'process_summary_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = ['seed7 x_pos', 'seed8 x_pos', 'seed7 x_neg', 'seed8 x_neg']
    translation_scores = [
        float(audit['seed7']['translation_x_pos']['strongest_pair_mode_scores']['translation_like']),
        float(audit['seed8']['translation_x_pos']['strongest_pair_mode_scores']['translation_like']),
        float(audit['seed7']['translation_x_neg']['strongest_pair_mode_scores']['translation_like']),
        float(audit['seed8']['translation_x_neg']['strongest_pair_mode_scores']['translation_like']),
    ]
    static_scores = [
        float(audit['seed7']['translation_x_pos']['strongest_pair_mode_scores']['static_like']),
        float(audit['seed8']['translation_x_pos']['strongest_pair_mode_scores']['static_like']),
        float(audit['seed7']['translation_x_neg']['strongest_pair_mode_scores']['static_like']),
        float(audit['seed8']['translation_x_neg']['strongest_pair_mode_scores']['static_like']),
    ]

    xs = range(len(labels))
    fig = plt.figure(figsize=(8.4, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.bar([x - 0.18 for x in xs], translation_scores, width=0.36, label='translation_like')
    ax.bar([x + 0.18 for x in xs], static_scores, width=0.36, label='static_like')
    ax.set_xticks(list(xs), labels)
    ax.set_ylabel('strongest-pair mode score')
    ax.set_title('Round36 strongest x-pair mode restoration')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit.png', dpi=160)


if __name__ == '__main__':
    main()
