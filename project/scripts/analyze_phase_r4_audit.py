from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / 'src'
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze Phase R.4 directional extension audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--title', type=str, default='Phase R.4 directional extension audit')
    p.add_argument('--output', type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'phase_r4_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    rows = list(payload.get('scan_rows', []))
    alphas = sorted({float(row['rotation_alpha']) for row in rows})
    gains = sorted({float(row['swirl_gain']) for row in rows})
    if alphas and gains:
        mat = np.zeros((len(alphas), len(gains)), dtype=np.float64)
        for row in rows:
            ai = alphas.index(float(row['rotation_alpha']))
            gi = gains.index(float(row['swirl_gain']))
            mat[ai, gi] = float(row['rotation_score'])
        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        im = ax.imshow(mat, aspect='auto', origin='lower')
        ax.set_xticks(np.arange(len(gains)), [f'{g:.2f}' for g in gains])
        ax.set_yticks(np.arange(len(alphas)), [f'{a:.0f}' for a in alphas])
        ax.set_xlabel('layered swirl gain')
        ax.set_ylabel('rotation alpha')
        ax.set_title(args.title)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('rotation score')
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r4_extension_map.png', dpi=160)
        plt.close(fig)

    directional = dict(payload.get('directional_extension', {}))
    vals = [
        float(directional.get('anchor_mean', 0.0)),
        float(directional.get('frontier_mean', 0.0)),
        float(directional.get('edge_stable_fraction', 0.0)),
        float(directional.get('directional_score', 0.0)),
    ]
    labels = ['anchor mean', 'frontier mean', 'edge stable frac', 'directional score']
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, vals)
    ax.set_ylim(0.0, 1.0)
    ax.set_title(args.title + f" ({directional.get('status', 'unknown')})")
    ax.grid(True, axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / 'phase_r4_directional_summary.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
