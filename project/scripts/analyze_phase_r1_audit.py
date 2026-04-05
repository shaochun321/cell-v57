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

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze Phase R.1 focused audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--title', type=str, default='Phase R.1 focused audit')
    p.add_argument('--output', type=str, required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    rankings = payload.get('rotation_track_ranking', [])
    focused = payload.get('focused_metrics', {})
    analysis = {
        'title': args.title,
        'rotation_track_ranking': rankings,
        'focused_metrics': focused,
        'repair_status': payload.get('repair_status', {}),
        'cautions': payload.get('cautions', []),
    }
    (outdir / 'phase_r1_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')

    x = np.arange(len(TRACK_NAMES), dtype=np.float64)
    rotation_scores = []
    translation_scores = []
    by_name = {item['track_name']: item for item in rankings}
    for name in TRACK_NAMES:
        item = by_name.get(name, {'rotation_score': 0.0, 'translation_score': 0.0})
        rotation_scores.append(float(item.get('rotation_score', 0.0)))
        translation_scores.append(float(item.get('translation_score', 0.0)))

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(x, rotation_scores, marker='o', label='rotation robustness')
    ax.plot(x, translation_scores, marker='o', label='translation robustness')
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks(x, TRACK_NAMES, rotation=15)
    ax.set_ylabel('score')
    ax.set_title(args.title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    fig.tight_layout()
    fig.savefig(outdir / 'phase_r1_overview.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
