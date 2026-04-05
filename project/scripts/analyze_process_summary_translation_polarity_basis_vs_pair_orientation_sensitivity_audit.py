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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation carrier sensitivity audit') -> dict:
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
    (outdir / 'process_summary_translation_polarity_basis_vs_pair_orientation_sensitivity_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    track_order = ['discrete_channel_track', 'local_propagation_track', 'layered_coupling_track']
    labels = ['discrete', 'local', 'layered']
    orientation_scores = [float(payload['per_track'][t]['x_pos_orientation_override_score']) for t in track_order]
    polarity_scores = [float(payload['per_track'][t]['x_neg_polarity_inversion_score']) for t in track_order]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    xs = range(len(track_order))
    axes[0].bar(xs, orientation_scores)
    axes[0].set_xticks(list(xs))
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel('orientation override score')
    axes[0].set_title('x_pos: x-vs-y competition severity')

    axes[1].bar(xs, polarity_scores)
    axes[1].set_xticks(list(xs))
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel('polarity inversion score')
    axes[1].set_title('x_neg: polarity inversion severity')

    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(outdir / 'process_summary_translation_polarity_basis_vs_pair_orientation_sensitivity_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
