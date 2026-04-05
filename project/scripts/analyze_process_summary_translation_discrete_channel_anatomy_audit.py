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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation discrete-channel anatomy audit') -> dict:
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
    (outdir / 'process_summary_translation_discrete_channel_anatomy_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    order = ['discrete_channel_track', 'local_propagation_track', 'layered_coupling_track']
    labels = ['discrete', 'local', 'layered']
    orientation = [float(payload['per_track'][t]['x_pos_orientation_override_score']) for t in order]
    polarity = [float(payload['per_track'][t]['x_neg_polarity_inversion_score']) for t in order]
    energy = [float(payload['per_track'][t]['mean_axis_energy']) for t in order]
    family = [float(payload['per_track'][t]['mean_family_support']) for t in order]

    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.2))
    xs = range(len(order))
    panels = [
        (orientation, 'x_pos orientation override', axes[0][0]),
        (polarity, 'x_neg polarity inversion', axes[0][1]),
        (energy, 'mean axis energy', axes[1][0]),
        (family, 'mean family support', axes[1][1]),
    ]
    for values, ttl, ax in panels:
        ax.bar(xs, values)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels)
        ax.set_title(ttl)

    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(outdir / 'process_summary_translation_discrete_channel_anatomy_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
