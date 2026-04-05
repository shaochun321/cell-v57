from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze x_pos active-window rescue audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    summary = {
        'suite': audit['suite'],
        'contracts': audit['contracts'],
        'inferred_primary_source': audit['inferred_primary_source'],
        'secondary_contributors': audit['secondary_contributors'],
        'seed7': {
            'active_axis': audit['seed7']['active_axis'],
            'upstream_axis_match_fraction': audit['seed7']['upstream_axis_match_fraction'],
            'strongest_pair_mode': audit['seed7']['strongest_pair_mode'],
            'strongest_pair_upstream_mode': audit['seed7']['strongest_pair_upstream_mode'],
        },
        'seed8': {
            'active_axis': audit['seed8']['active_axis'],
            'upstream_axis_match_fraction': audit['seed8']['upstream_axis_match_fraction'],
            'strongest_pair_mode': audit['seed8']['strongest_pair_mode'],
            'strongest_pair_upstream_mode': audit['seed8']['strongest_pair_upstream_mode'],
        },
        'evidence': audit['evidence'],
    }
    (outdir / 'process_summary_translation_x_pos_active_window_rescue_audit_analysis.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    fig = plt.figure(figsize=(8, 4.8))
    ax = fig.add_subplot(111)
    categories = ['upstream_axis_match_fraction', 'mean_handoff_gate_score_x', 'mean_handoff_gate_score_y']
    seed7_vals = [
        audit['seed7']['upstream_axis_match_fraction'],
        audit['seed7']['active_axis_summaries']['x']['mean_handoff_gate_score'],
        audit['seed7']['active_axis_summaries']['y']['mean_handoff_gate_score'],
    ]
    seed8_vals = [
        audit['seed8']['upstream_axis_match_fraction'],
        audit['seed8']['active_axis_summaries']['x']['mean_handoff_gate_score'],
        audit['seed8']['active_axis_summaries']['y']['mean_handoff_gate_score'],
    ]
    xs = range(len(categories))
    ax.plot(xs, seed7_vals, marker='o', label='seed7')
    ax.plot(xs, seed8_vals, marker='o', label='seed8')
    ax.set_xticks(list(xs), categories, rotation=15)
    ax.set_ylim(0.0, max(seed7_vals + seed8_vals + [1.0]) * 1.1)
    ax.set_title('translation_x_pos active-window rescue audit')
    ax.set_ylabel('score')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_active_window_rescue_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
