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
    p = argparse.ArgumentParser(description='Analyze Phase R.5 repeatability audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--title', type=str, default='Phase R.5 repeatability audit')
    p.add_argument('--output', type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'phase_r5_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    rows = list(payload.get('scan_rows', []))
    alphas = sorted({float(r['rotation_alpha']) for r in rows})
    gains = sorted({float(r['swirl_gain']) for r in rows})
    if alphas and gains:
        mean_mat = np.zeros((len(alphas), len(gains)))
        std_mat = np.zeros((len(alphas), len(gains)))
        for r in rows:
            ai = alphas.index(float(r['rotation_alpha']))
            gi = gains.index(float(r['swirl_gain']))
            mean_mat[ai, gi] = float(r['rotation_score_mean'])
            std_mat[ai, gi] = float(r['rotation_score_std'])
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
        for ax, mat, title, cblabel in [
            (axes[0], mean_mat, 'mean rotation score', 'mean score'),
            (axes[1], std_mat, 'repeat std', 'score std'),
        ]:
            im = ax.imshow(mat, aspect='auto', origin='lower')
            ax.set_xticks(np.arange(len(gains)), [f'{g:.2f}' for g in gains])
            ax.set_yticks(np.arange(len(alphas)), [f'{a:.0f}' for a in alphas])
            ax.set_xlabel('layered swirl gain')
            ax.set_ylabel('rotation alpha')
            ax.set_title(title)
            cb = fig.colorbar(im, ax=ax)
            cb.set_label(cblabel)
        fig.suptitle(args.title)
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r5_repeatability_map.png', dpi=160)
        plt.close(fig)

    plateau = dict(payload.get('local_repeatability_plateau', {}))
    vals = [
        float(plateau.get('mean_repeatability', 0.0)),
        float(plateau.get('floor_repeatability', 0.0)),
        float(plateau.get('plateau_score', 0.0)),
        float(payload.get('translation_guard', {}).get('translation_guard_score', 0.0)),
    ]
    labels = ['plateau mean', 'plateau floor', 'plateau score', 'translation guard']
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, vals)
    ax.set_ylim(0.0, 1.0)
    ax.set_title(args.title)
    ax.grid(True, axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / 'phase_r5_plateau_summary.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
