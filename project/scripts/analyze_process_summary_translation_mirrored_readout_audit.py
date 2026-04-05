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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation mirrored readout audit') -> dict:
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
    (outdir / 'process_summary_translation_mirrored_readout_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [int(r['seed']) for r in rows]
    pos_inner = [float(r['cases']['translation_x_pos']['inner_translation_share']) for r in rows]
    pos_outer = [float(r['cases']['translation_x_pos']['outer_translation_share']) for r in rows]
    neg_inner = [float(r['cases']['translation_x_neg']['inner_translation_share']) for r in rows]
    neg_outer = [float(r['cases']['translation_x_neg']['outer_translation_share']) for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    xs = list(range(len(seeds)))
    ax.plot(xs, pos_inner, marker='o', label='x_pos inner share')
    ax.plot(xs, pos_outer, marker='o', linestyle='--', label='x_pos outer share')
    ax.plot(xs, neg_inner, marker='s', label='x_neg inner share')
    ax.plot(xs, neg_outer, marker='s', linestyle='--', label='x_neg outer share')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(s) for s in seeds])
    ax.set_xlabel('seed')
    ax.set_ylabel('translation mass share')
    ax.set_ylim(0.0, 1.05)
    ax.set_title(title)
    ax.legend(loc='best')
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_mirrored_readout_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
