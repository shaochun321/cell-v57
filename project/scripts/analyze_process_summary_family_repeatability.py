from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze process summary family repeatability audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--output', type=str, required=True)
    p.add_argument('--title', type=str, default='Process summary family repeatability audit')
    return p.parse_args()


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Process summary family repeatability audit') -> dict:
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'process_summary_family_repeatability_analysis.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    families = list(audit.get('families', {}).keys())
    xs = np.arange(len(families))
    axis_consistency = [float(audit['families'][name]['axis_consistency']) for name in families]
    mode_consistency = [float(audit['families'][name]['mode_consistency']) for name in families]
    flip_fraction = [float(audit['families'][name]['flip_fraction']) for name in families]
    plt.figure(figsize=(8.2, 4.8))
    plt.plot(xs, axis_consistency, marker='o', label='axis consistency')
    plt.plot(xs, mode_consistency, marker='o', label='mode consistency')
    plt.plot(xs, flip_fraction, marker='o', label='flip fraction')
    plt.xticks(xs, families)
    plt.ylim(0.0, 1.05)
    plt.ylabel('fraction')
    plt.title(title)
    plt.grid(True, axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_summary_family_repeatability_consistency.png', dpi=180)
    plt.close()

    mean_sep = [float(audit['families'][name]['mean_separation']) for name in families]
    min_sep = [float(audit['families'][name]['min_separation']) for name in families]
    width = 0.35
    plt.figure(figsize=(7.4, 4.6))
    plt.bar(xs - width/2.0, mean_sep, width=width, label='mean separation')
    plt.bar(xs + width/2.0, min_sep, width=width, label='min separation')
    plt.xticks(xs, families)
    plt.ylabel('signal separation')
    plt.title(title)
    plt.grid(True, axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_summary_family_repeatability_separation.png', dpi=180)
    plt.close()
    return audit


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.input, output_dir=args.output, title=args.title)


if __name__ == '__main__':
    main()
