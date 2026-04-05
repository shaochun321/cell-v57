from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--audit-json', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(args.audit_json).read_text(encoding='utf-8'))

    tracks = list(payload['per_track'].keys())
    x_vals = [abs(payload['per_track'][t]['current_x_balance']) for t in tracks]
    y_vals = [abs(payload['per_track'][t]['current_y_balance']) for t in tracks]

    fig, ax = plt.subplots(figsize=(7, 4))
    xs = range(len(tracks))
    width = 0.35
    ax.bar([x - width/2 for x in xs], x_vals, width=width, label='|x balance|')
    ax.bar([x + width/2 for x in xs], y_vals, width=width, label='|y balance|')
    ax.set_xticks(list(xs))
    ax.set_xticklabels(['discrete', 'local', 'layered'])
    ax.set_ylabel('seed 8 magnitude')
    ax.set_title('x_neg sign-limited polarity-basis audit')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_x_neg_sign_limited_polarity_basis_audit.png', dpi=160)
    plt.close(fig)

    (outdir / 'process_summary_translation_x_neg_sign_limited_polarity_basis_audit_analysis.json').write_text(
        json.dumps({
            'contracts_passed': payload['contracts']['passed'],
            'inferred_primary_source': payload['inferred_primary_source'],
            'secondary_contributors': payload['secondary_contributors'],
        }, indent=2),
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
