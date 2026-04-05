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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation atlas pair formation audit') -> dict:
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
    (outdir / 'process_summary_translation_atlas_pair_formation_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [int(r['seed']) for r in rows]
    pos_margin = [float(r['cases']['translation_x_pos']['strongest_pair_translation_margin']) for r in rows]
    neg_margin = [float(r['cases']['translation_x_neg']['strongest_pair_translation_margin']) for r in rows]

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    xs = list(range(len(seeds)))
    ax.plot(xs, pos_margin, marker='o', label='x_pos strongest-pair margin')
    ax.plot(xs, neg_margin, marker='s', label='x_neg strongest-pair margin')
    ax.axhline(0.0, linestyle='--')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(s) for s in seeds])
    ax.set_xlabel('seed')
    ax.set_ylabel('translation - static score')
    ax.set_title(title)
    ax.legend(loc='best')
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_atlas_pair_formation_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
