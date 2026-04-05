from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _shell_rows(audit: dict, seed_key: str, window_index: int) -> list[dict]:
    for window in audit[seed_key]['active_shell_balance_rows']:
        if int(window['window_index']) == int(window_index):
            return list(window['shell_rows'])
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze translation_x_pos upstream candidate anatomy audit.')
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
        'seed7_active_windows': audit['seed7']['active_windows'],
        'seed8_active_windows': audit['seed8']['active_windows'],
    }
    (outdir / 'process_summary_translation_x_pos_upstream_candidate_anatomy_audit_analysis.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    seed8_window6 = _shell_rows(audit, 'seed8', 6)
    shell_labels = [f"shell_{row['shell_index']}" for row in seed8_window6]
    x_vals = [abs(float(row['x_balance'])) for row in seed8_window6]
    y_vals = [abs(float(row['y_balance'])) for row in seed8_window6]

    fig = plt.figure(figsize=(8.4, 4.8))
    ax = fig.add_subplot(111)
    xs = list(range(len(shell_labels)))
    ax.plot(xs, x_vals, marker='o', label='|x balance|')
    ax.plot(xs, y_vals, marker='o', label='|y balance|')
    ax.set_xticks(xs, shell_labels)
    ax.set_ylabel('balance magnitude')
    ax.set_title('seed8 active-window shell balances (window 6)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_pos_upstream_candidate_anatomy_audit.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
