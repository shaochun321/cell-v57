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
    p = argparse.ArgumentParser(description='Analyze Phase R.2 sensitivity audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--title', type=str, default='Phase R.2 sensitivity audit')
    p.add_argument('--output', type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'phase_r2_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    rows = list(payload.get('scan_rows', []))
    alphas = sorted({float(row['rotation_alpha']) for row in rows})
    gains = sorted({float(row['swirl_gain']) for row in rows})
    if alphas and gains:
        mat = np.zeros((len(alphas), len(gains)), dtype=np.float64)
        for row in rows:
            ai = alphas.index(float(row['rotation_alpha']))
            gi = gains.index(float(row['swirl_gain']))
            mat[ai, gi] = float(row['rotation_score'])
        fig, ax = plt.subplots(figsize=(7.0, 4.8))
        im = ax.imshow(mat, aspect='auto', origin='lower')
        ax.set_xticks(np.arange(len(gains)), [f'{g:.2f}' for g in gains])
        ax.set_yticks(np.arange(len(alphas)), [f'{a:.0f}' for a in alphas])
        ax.set_xlabel('layered swirl gain')
        ax.set_ylabel('rotation alpha')
        ax.set_title(args.title)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('rotation score')
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r2_sensitivity_map.png', dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.0, 4.5))
        ax.plot(list(payload.get('alpha_mean_scores', {}).keys()), list(payload.get('alpha_mean_scores', {}).values()), marker='o', label='mean score by alpha')
        ax.plot(list(payload.get('swirl_mean_scores', {}).keys()), list(payload.get('swirl_mean_scores', {}).values()), marker='o', label='mean score by swirl gain')
        ax.set_ylim(0.0, 1.0)
        ax.set_title(args.title + ' (collapsed means)')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r2_sensitivity_curves.png', dpi=160)
        plt.close(fig)

    local = dict(payload.get('local_robustness', {}))
    if local:
        labels = ['local mean', 'local floor', 'stable region']
        vals = [float(local.get('local_mean', 0.0)), float(local.get('local_floor', 0.0)), float(local.get('stable_region_score', 0.0))]
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        ax.bar(labels, vals)
        ax.set_ylim(0.0, 1.0)
        boundary = 'yes' if local.get('boundary_best', False) else 'no'
        ax.set_title(args.title + f' (local robustness, boundary={boundary})')
        ax.grid(True, axis='y', alpha=0.3)
        fig.tight_layout()
        fig.savefig(outdir / 'phase_r2_local_robustness.png', dpi=160)
        plt.close(fig)


if __name__ == '__main__':
    main()
