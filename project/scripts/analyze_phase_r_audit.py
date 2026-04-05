from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import os

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.phase_r import summarize_phase_r_audit
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Externally analyze Phase R robustness audit.')
    p.add_argument('--input', type=str, required=True, help='Path to phase_r_protocol_report.json or phase_r_audit.json')
    p.add_argument('--title', type=str, default='Phase R robustness audit')
    p.add_argument('--output', type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    if 'tracks' in payload and 'overall' in payload and 'recommendations' in payload:
        audit = payload
    else:
        audit = summarize_phase_r_audit(payload)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    report_path = outdir / 'phase_r_analysis.json'
    report_path.write_text(json.dumps({'title': args.title, 'audit': audit}, ensure_ascii=False, indent=2), encoding='utf-8')

    x = np.arange(len(TRACK_NAMES), dtype=np.float64)
    translation_scores = [audit['tracks'][name]['translation_score'] for name in TRACK_NAMES]
    rotation_scores = [audit['tracks'][name]['rotation_score'] for name in TRACK_NAMES]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, translation_scores, marker='o', label='translation robustness')
    ax.plot(x, rotation_scores, marker='o', label='rotation robustness')
    ax.set_xticks(x, TRACK_NAMES, rotation=15)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel('robustness score')
    ax.set_title(args.title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / 'phase_r_overview.png'
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
    print(f'分析报告: {report_path}')
    print(f'概览图: {fig_path}')


if __name__ == '__main__':
    main()
