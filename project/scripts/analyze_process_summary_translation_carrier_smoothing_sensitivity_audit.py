from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


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
    x_pos_vals = [payload['per_track'][t]['x_pos_axial_minus_swirl'] for t in tracks]
    x_neg_vals = [payload['per_track'][t]['x_neg_axial_minus_swirl'] for t in tracks]

    fig, ax = plt.subplots(figsize=(7, 4))
    xs = range(len(tracks))
    width = 0.35
    ax.bar([x - width/2 for x in xs], x_pos_vals, width=width, label='x_pos axial-swirl')
    ax.bar([x + width/2 for x in xs], x_neg_vals, width=width, label='x_neg axial-swirl')
    ax.set_xticks(list(xs))
    ax.set_xticklabels(['discrete', 'local', 'layered'])
    ax.set_ylabel('axial_minus_swirl')
    ax.set_title('Translation carrier smoothing sensitivity')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_carrier_smoothing_sensitivity_audit.png', dpi=160)
    plt.close(fig)

    (outdir / 'process_summary_translation_carrier_smoothing_sensitivity_audit_analysis.json').write_text(
        json.dumps({
            'contracts_passed': payload['contracts']['passed'],
            'inferred_primary_source': payload['inferred_primary_source'],
            'secondary_contributors': payload['secondary_contributors'],
        }, indent=2),
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
