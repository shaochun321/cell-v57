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
    p = argparse.ArgumentParser(description='Analyze Phase R.3 closure audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--title', type=str, default='Phase R.3 closure audit')
    p.add_argument('--output', type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'phase_r3_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    rows = list(payload.get('scan_rows', []))
    alphas = sorted({float(row['rotation_alpha']) for row in rows})
    gains = sorted({float(row['swirl_gain']) for row in rows})
    stable_points = {(float(p['rotation_alpha']), float(p['swirl_gain'])) for p in payload.get('closure', {}).get('stable_points', [])}
    if alphas and gains:
        mat = np.zeros((len(alphas), len(gains)), dtype=np.float64)
        mask = np.zeros_like(mat)
        for row in rows:
            ai = alphas.index(float(row['rotation_alpha']))
            gi = gains.index(float(row['swirl_gain']))
            mat[ai, gi] = float(row['rotation_score'])
            if (float(row['rotation_alpha']), float(row['swirl_gain'])) in stable_points:
                mask[ai, gi] = 1.0
        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        im = ax.imshow(mat, aspect='auto', origin='lower')
        yy, xx = np.where(mask > 0.5)
        if len(xx):
            ax.scatter(xx, yy, marker='s', s=90, facecolors='none', edgecolors='white', linewidths=1.5)
        ax.set_xticks(np.arange(len(gains)), [f'{g:.2f}' for g in gains])
        ax.set_yticks(np.arange(len(alphas)), [f'{a:.0f}' for a in alphas])
        ax.set_xlabel('layered swirl gain')
        ax.set_ylabel('rotation alpha')
        ax.set_title(args.title)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('rotation score')
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r3_closure_map.png', dpi=160)
        plt.close(fig)

    closure = dict(payload.get('closure', {}))
    vals = [
        float(closure.get('mean_score', 0.0)),
        float(closure.get('floor_score', 0.0)),
        float(closure.get('closure_score', 0.0)),
    ]
    labels = ['component mean', 'component floor', 'closure score']
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.bar(labels, vals)
    ax.set_ylim(0.0, 1.0)
    boundary = 'yes' if closure.get('boundary_touch', True) else 'no'
    ax.set_title(args.title + f' (boundary touch={boundary})')
    ax.grid(True, axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / 'phase_r3_closure_summary.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
