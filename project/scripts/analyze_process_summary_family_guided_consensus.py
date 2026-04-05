from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def analyze_consensus_file(*, consensus_path: str | Path, output_dir: str | Path, title: str) -> dict[str, Any]:
    consensus = json.loads(Path(consensus_path).read_text(encoding='utf-8'))
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    cases = dict(consensus.get('cases', {}))
    labels = list(cases.keys())
    sign_fracs = [float(cases[k].get('active_signal_expected_sign_fraction', 0.0)) for k in labels]
    support = [float(cases[k].get('mean_expected_mode_support_at_expected_axis', 0.0)) for k in labels]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(labels))
    ax.bar(x - 0.18, sign_fracs, width=0.36, label='sign fraction')
    ax.bar(x + 0.18, support, width=0.36, label='mode support')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha='right')
    ax.set_ylim(0.0, 1.05)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    png = outdir / 'process_summary_family_guided_case_consensus.png'
    fig.savefig(png, dpi=160)
    plt.close(fig)

    analysis = {
        'title': title,
        'consensus_path': str(consensus_path),
        'contracts': dict(consensus.get('contracts', {})),
        'families': dict(consensus.get('families', {})),
        'cases': cases,
        'chart_path': str(png),
    }
    json_path = outdir / 'process_summary_family_guided_case_consensus_analysis.json'
    json_path.write_text(json.dumps(analysis, indent=2), encoding='utf-8')
    return analysis


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Analyze family-guided case consensus outputs.')
    p.add_argument('--consensus-path', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--title', default='Process summary family-guided case consensus')
    return p


def main() -> None:
    args = build_argparser().parse_args()
    analysis = analyze_consensus_file(consensus_path=args.consensus_path, output_dir=args.output_dir, title=args.title)
    print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    main()
