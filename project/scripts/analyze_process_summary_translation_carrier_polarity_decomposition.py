from __future__ import annotations

import argparse
import json
from pathlib import Path
import os


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--decomposition-json', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def analyze_decomposition_file(*, decomposition_path: str | Path, output_dir: str | Path, title: str = 'Translation carrier polarity decomposition') -> dict:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(decomposition_path).read_text(encoding='utf-8'))
    analysis = {
        'suite': payload.get('suite'),
        'inferred_primary_source': payload.get('inferred_primary_source', 'undetermined'),
        'secondary_contributors': list(payload.get('secondary_contributors', [])),
        'evidence': dict(payload.get('evidence', {})),
        'classification_counts': dict(payload.get('classification_counts', {})),
        'contracts': dict(payload.get('contracts', {})),
    }
    (outdir / 'process_summary_translation_carrier_polarity_decomposition_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    rows = payload.get('per_seed', [])
    seeds = [int(r['seed']) for r in rows]
    xs = list(range(len(seeds)))
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))

    for case_name, marker in [('translation_x_pos', 'o'), ('translation_x_neg', 's')]:
        x_bal = []
        y_bal = []
        for row in rows:
            track = row['cases'][case_name]['tracks']['discrete_channel_track']
            x_bal.append(float(track['x_balance']))
            y_bal.append(float(track['y_balance']))
        axes[0].plot(xs, x_bal, marker=marker, label=f'{case_name}: x')
        axes[0].plot(xs, y_bal, marker=marker, linestyle='--', label=f'{case_name}: y')
    axes[0].axhline(0.0, linestyle=':')
    axes[0].set_xticks(xs)
    axes[0].set_xticklabels([str(s) for s in seeds])
    axes[0].set_xlabel('seed')
    axes[0].set_ylabel('discrete balance')
    axes[0].set_title('x vs y competition')

    class_order = ['x_axis_competition_override', 'polarity_projection_inversion', 'carrier_ok']
    class_counts = [int(payload.get('classification_counts', {}).get(c, 0)) for c in class_order]
    axes[1].bar(range(len(class_order)), class_counts)
    axes[1].set_xticks(range(len(class_order)))
    axes[1].set_xticklabels(['axis_comp', 'polarity_inv', 'ok'], rotation=15)
    axes[1].set_ylabel('track count')
    axes[1].set_title('dominant failure ingredients')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(outdir / 'process_summary_translation_carrier_polarity_decomposition.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_decomposition_file(decomposition_path=args.decomposition_json, output_dir=args.outdir)


if __name__ == '__main__':
    main()
