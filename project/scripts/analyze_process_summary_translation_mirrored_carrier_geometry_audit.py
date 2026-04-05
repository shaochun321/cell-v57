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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation mirrored carrier geometry audit') -> dict:
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
    (outdir / 'process_summary_translation_mirrored_carrier_geometry_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    cases = ['translation_x_pos', 'translation_x_neg']
    ref_margin = [float(payload['per_case'][c]['reference_pair_translation_minus_static']) for c in cases]
    cmp_margin = [float(payload['per_case'][c]['comparison_pair_translation_minus_static']) for c in cases]
    cmp_pol = [float(payload['per_case'][c]['comparison_pair_polarity_signed']) for c in cases]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    xs = range(len(cases))
    axes[0].bar([x - 0.15 for x in xs], ref_margin, width=0.3, label='seed7 pair margin')
    axes[0].bar([x + 0.15 for x in xs], cmp_margin, width=0.3, label='seed8 pair margin')
    axes[0].set_xticks(list(xs))
    axes[0].set_xticklabels(['x_pos', 'x_neg'])
    axes[0].set_ylabel('translation - static')
    axes[0].set_title('outer strongest-pair margin')

    axes[1].bar(xs, cmp_pol)
    axes[1].set_xticks(list(xs))
    axes[1].set_xticklabels(['x_pos', 'x_neg'])
    axes[1].set_ylabel('seed8 outer pair polarity')
    axes[1].set_title('post-shift polarity asymmetry')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    fig.savefig(outdir / 'process_summary_translation_mirrored_carrier_geometry_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
