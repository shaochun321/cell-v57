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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation sign source audit') -> dict:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    analysis = {
        'suite': 'process_summary_translation_sign_source_audit',
        'inferred_primary_source': payload.get('inferred_primary_source', 'undetermined'),
        'secondary_contributors': list(payload.get('secondary_contributors', [])),
        'evidence': dict(payload.get('evidence', {})),
        'contracts': dict(payload.get('contracts', {})),
    }
    (outdir / 'process_summary_translation_sign_source_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    seeds = [row['seed'] for row in payload.get('per_seed', [])]
    pos = [payload['per_seed'][i]['cases']['translation_x_pos']['raw_signal'] for i in range(len(seeds))]
    neg = [payload['per_seed'][i]['cases']['translation_x_neg']['raw_signal'] for i in range(len(seeds))]
    fig, ax = plt.subplots(figsize=(6, 4))
    xs = list(range(len(seeds)))
    ax.bar([x - 0.15 for x in xs], pos, width=0.3, label='translation_x_pos')
    ax.bar([x + 0.15 for x in xs], neg, width=0.3, label='translation_x_neg')
    ax.axhline(0.0, linewidth=1.0)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(s) for s in seeds])
    ax.set_xlabel('seed')
    ax.set_ylabel('active x polarity projection')
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_translation_sign_source_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
