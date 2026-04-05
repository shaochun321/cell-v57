from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos process x-direction recovery repair audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    tx7 = audit['seed7']['translation_x_pos']
    tx8 = audit['seed8']['translation_x_pos']
    rz8 = audit['seed8']['rotation_z_pos']

    analysis = {
        'suite': audit['suite'],
        'contracts': audit['contracts'],
        'inferred_outcome': audit['inferred_outcome'],
        'residual_issue': audit['residual_issue'],
        'seed7_translation_active_summary': tx7['summary'],
        'seed8_translation_active_summary': tx8['summary'],
        'seed8_rotation_guardrail_summary': rz8['summary'],
        'seed8_translation_active_process_windows': tx8['active_process_windows'],
    }
    (outdir / 'process_summary_translation_x_pos_process_x_direction_recovery_repair_audit_analysis.json').write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    xs = list(range(len(tx8['active_process_windows'])))
    tx_vals = [row['translation_like'] for row in tx8['active_process_windows']]
    rot_vals = [row['rotation_like'] for row in tx8['active_process_windows']]
    xdir_vals = [row['mean_x_direction'] for row in tx8['active_process_windows']]
    zcir_vals = [row['mean_z_circulation'] for row in tx8['active_process_windows']]

    fig = plt.figure(figsize=(8, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, tx_vals, marker='o', label='translation_like')
    ax.plot(xs, rot_vals, marker='o', label='rotation_like')
    ax.plot(xs, xdir_vals, marker='o', label='mean_x_direction')
    ax.plot(xs, zcir_vals, marker='o', label='mean_z_circulation')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(row['window_index']) for row in tx8['active_process_windows']])
    ax.set_xlabel('seed8 active windows')
    ax.set_ylabel('score')
    ax.set_title('Round34 seed8 translation_x_pos repair profile')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_process_x_direction_recovery_repair_audit.png', dpi=160)


if __name__ == "__main__":
    main()
