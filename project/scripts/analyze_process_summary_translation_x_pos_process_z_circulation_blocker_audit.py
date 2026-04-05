from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos process z-circulation blocker audit.')
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
        'evidence': audit['evidence'],
        'seed7_active_process_windows': audit['seed7']['active_process_windows'],
        'seed8_active_process_windows': audit['seed8']['active_process_windows'],
    }
    (outdir / 'process_summary_translation_x_pos_process_z_circulation_blocker_audit_analysis.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    labels = [f"w{row['window_index']}" for row in audit['seed8']['active_process_windows']]
    x_direction = [float(row['mean_x_direction']) for row in audit['seed8']['active_process_windows']]
    z_circulation = [float(row['mean_z_circulation']) for row in audit['seed8']['active_process_windows']]
    translation = [float(row['translation_like']) for row in audit['seed8']['active_process_windows']]
    rotation = [float(row['rotation_like']) for row in audit['seed8']['active_process_windows']]

    fig = plt.figure(figsize=(8.6, 4.8))
    ax = fig.add_subplot(111)
    xs = list(range(len(labels)))
    ax.plot(xs, x_direction, marker='o', label='mean_x_direction')
    ax.plot(xs, z_circulation, marker='o', label='mean_z_circulation')
    ax.plot(xs, translation, marker='o', label='translation_like')
    ax.plot(xs, rotation, marker='o', label='rotation_like')
    ax.set_xticks(xs, labels)
    ax.set_ylabel('score / magnitude')
    ax.set_title('seed8 process-level blocker anatomy')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_process_z_circulation_blocker_audit.png', dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
