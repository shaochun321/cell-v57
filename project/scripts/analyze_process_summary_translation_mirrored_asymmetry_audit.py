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


def analyze_audit_file(*, audit_path: str | Path, output_dir: str | Path, title: str = 'Translation mirrored asymmetry audit') -> dict:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    analysis = {
        'suite': payload.get('suite'),
        'inferred_primary_source': payload.get('inferred_primary_source', 'undetermined'),
        'secondary_contributors': list(payload.get('secondary_contributors', [])),
        'evidence': dict(payload.get('evidence', {})),
        'summary': dict(payload.get('summary', {})),
        'contracts': dict(payload.get('contracts', {})),
    }
    (outdir / 'process_summary_translation_mirrored_asymmetry_audit_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cases = ['translation_x_pos', 'translation_x_neg']
    inner = [float(payload['per_case'][c]['inner_collapse']) for c in cases]
    outer = [float(payload['per_case'][c]['outer_increase']) for c in cases]
    pair_shift = [int(payload['per_case'][c]['pair_strength_shell_shift']) for c in cases]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    xs = range(len(cases))
    axes[0].bar([x - 0.15 for x in xs], inner, width=0.3, label='inner collapse')
    axes[0].bar([x + 0.15 for x in xs], outer, width=0.3, label='outer increase')
    axes[0].set_xticks(list(xs))
    axes[0].set_xticklabels(['x_pos', 'x_neg'])
    axes[0].set_ylabel('share delta')
    axes[0].set_title('shared outer shift symmetry')
    axes[1].bar(xs, pair_shift)
    axes[1].set_xticks(list(xs))
    axes[1].set_xticklabels(['x_pos', 'x_neg'])
    axes[1].set_ylabel('shell shift')
    axes[1].set_title('pair-strength shell shift')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    fig.savefig(outdir / 'process_summary_translation_mirrored_asymmetry_audit.png', dpi=180)
    plt.close(fig)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_audit_file(audit_path=args.audit_json, output_dir=args.outdir)

if __name__ == '__main__':
    main()
