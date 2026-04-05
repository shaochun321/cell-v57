from __future__ import annotations

import argparse
import json
from pathlib import Path
import os


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--audit-json', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation shell-to-atlas handoff audit') -> dict:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    analysis = {
        'suite': payload.get('suite'),
        'inferred_primary_source': payload.get('inferred_primary_source', 'undetermined'),
        'secondary_contributors': list(payload.get('secondary_contributors', [])),
        'evidence': dict(payload.get('evidence', {})),
        'contracts': dict(payload.get('contracts', {})),
    }
    (outdir / 'process_summary_translation_shell_to_atlas_handoff_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [int(r['seed']) for r in rows]
    pos_ratio = [float(r['cases']['translation_x_pos']['axial_family_outer_inner_ratio']) for r in rows]
    neg_ratio = [float(r['cases']['translation_x_neg']['axial_family_outer_inner_ratio']) for r in rows]
    pos_margin = [float(r['cases']['translation_x_pos']['atlas_translation_margin']) for r in rows]
    neg_margin = [float(r['cases']['translation_x_neg']['atlas_translation_margin']) for r in rows]

    fig, ax1 = plt.subplots(figsize=(7.2, 4.4))
    xs = list(range(len(seeds)))
    ax1.plot(xs, pos_ratio, marker='o', label='x_pos outer/inner ratio')
    ax1.plot(xs, neg_ratio, marker='s', label='x_neg outer/inner ratio')
    ax1.set_xticks(xs)
    ax1.set_xticklabels([str(s) for s in seeds])
    ax1.set_xlabel('seed')
    ax1.set_ylabel('axial-family outer/inner ratio')

    ax2 = ax1.twinx()
    ax2.plot(xs, pos_margin, marker='^', linestyle='--', label='x_pos atlas margin')
    ax2.plot(xs, neg_margin, marker='v', linestyle='--', label='x_neg atlas margin')
    ax2.axhline(0.0, linestyle=':')
    ax2.set_ylabel('atlas translation - static score')

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='best')
    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_shell_to_atlas_handoff_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
