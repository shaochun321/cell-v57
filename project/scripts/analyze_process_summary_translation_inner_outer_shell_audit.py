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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation inner-vs-outer shell audit') -> dict:
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
    (outdir / 'process_summary_translation_inner_outer_shell_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [r['seed'] for r in rows]
    pos_shells = [r['cases']['translation_x_pos']['strongest_shell'] for r in rows]
    neg_shells = [r['cases']['translation_x_neg']['strongest_shell'] for r in rows]
    pos_pair = [r['cases']['translation_x_pos']['strongest_pair_polarity_projection'] for r in rows]
    neg_pair = [r['cases']['translation_x_neg']['strongest_pair_polarity_projection'] for r in rows]

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    xs = list(range(len(seeds)))
    ax.bar([x - 0.15 for x in xs], pos_pair, width=0.3, label='x_pos strongest pair polarity')
    ax.bar([x + 0.15 for x in xs], neg_pair, width=0.3, label='x_neg strongest pair polarity')
    ax2 = ax.twinx()
    ax2.plot(xs, pos_shells, marker='o', label='x_pos strongest shell')
    ax2.plot(xs, neg_shells, marker='s', label='x_neg strongest shell')
    ax.axhline(0.0, linewidth=1.0)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(s) for s in seeds])
    ax.set_xlabel('seed')
    ax.set_ylabel('strongest-pair polarity projection')
    ax2.set_ylabel('strongest shell index')
    ax.set_title(title)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='best')
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_inner_outer_shell_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
