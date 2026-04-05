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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation interface-family carrier audit') -> dict:
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
    (outdir / 'process_summary_translation_interface_family_carrier_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [int(r['seed']) for r in rows]
    tracks = ('discrete_channel_track', 'local_propagation_track', 'layered_coupling_track')
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    xs = list(range(len(seeds)))

    for track in tracks:
        pos_x = [float(r['cases']['translation_x_pos']['tracks'][track]['x_balance']) for r in rows]
        neg_x = [float(r['cases']['translation_x_neg']['tracks'][track]['x_balance']) for r in rows]
        axes[0].plot(xs, pos_x, marker='o', label=f'{track}: x_pos')
        axes[0].plot(xs, neg_x, marker='s', linestyle='--', label=f'{track}: x_neg')
    axes[0].axhline(0.0, linestyle=':')
    axes[0].set_xticks(xs)
    axes[0].set_xticklabels([str(s) for s in seeds])
    axes[0].set_xlabel('seed')
    axes[0].set_ylabel('active x-axis balance')
    axes[0].set_title('carrier polarity by track')

    for track in tracks:
        pos_ax = [float(r['cases']['translation_x_pos']['tracks'][track]['axial_minus_swirl']) for r in rows]
        neg_ax = [float(r['cases']['translation_x_neg']['tracks'][track]['axial_minus_swirl']) for r in rows]
        axes[1].plot(xs, pos_ax, marker='o', label=f'{track}: x_pos')
        axes[1].plot(xs, neg_ax, marker='s', linestyle='--', label=f'{track}: x_neg')
    axes[1].axhline(0.08, linestyle=':')
    axes[1].set_xticks(xs)
    axes[1].set_xticklabels([str(s) for s in seeds])
    axes[1].set_xlabel('seed')
    axes[1].set_ylabel('axial minus swirl')
    axes[1].set_title('translation family survives per carrier')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(outdir / 'process_summary_translation_interface_family_carrier_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
