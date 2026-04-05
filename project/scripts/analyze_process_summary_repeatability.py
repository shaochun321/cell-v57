from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze process summary repeatability audit output.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--output', type=str, required=True)
    p.add_argument('--title', type=str, default='Process summary repeatability audit')
    return p.parse_args()

def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Process summary repeatability audit') -> dict:
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'process_summary_repeatability_analysis.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    case_names = list(audit.get('cases', {}).keys())
    mode_consistency = [float(audit['cases'][name]['mode_consistency']) for name in case_names]
    axis_consistency = [float(audit['cases'][name]['axis_consistency']) for name in case_names]
    signal_consistency = [float(audit['cases'][name]['active_signal_sign_consistency']) for name in case_names]
    xs = np.arange(len(case_names))
    labels = [name.replace('_', '\n') for name in case_names]
    plt.figure(figsize=(10.5, 4.8))
    plt.plot(xs, mode_consistency, marker='o', label='overall mode consistency')
    plt.plot(xs, axis_consistency, marker='o', label='active axis consistency')
    plt.plot(xs, signal_consistency, marker='o', label='active sign consistency')
    plt.xticks(xs, labels)
    plt.ylim(0.0, 1.05)
    plt.ylabel('fraction')
    plt.title(title)
    plt.grid(True, axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_summary_repeatability_consistency.png', dpi=180)
    plt.close()
    paired = dict(audit.get('paired_gates', {}))
    labels2 = list(paired.keys())
    vals = [float(paired[name]['mean_separation']) for name in labels2]
    mins = [float(paired[name]['min_separation']) for name in labels2]
    xs2 = np.arange(len(labels2))
    width = 0.35
    plt.figure(figsize=(7.4, 4.6))
    plt.bar(xs2 - width/2.0, vals, width=width, label='mean separation')
    plt.bar(xs2 + width/2.0, mins, width=width, label='min separation')
    plt.xticks(xs2, [name.replace('_', '\n') for name in labels2])
    plt.title(title)
    plt.ylabel('signal separation')
    plt.grid(True, axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_summary_repeatability_separation.png', dpi=180)
    plt.close()
    return audit

def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.input, output_dir=args.output, title=args.title)

if __name__ == '__main__':
    main()
