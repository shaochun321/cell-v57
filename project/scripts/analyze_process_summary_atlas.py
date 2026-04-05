from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from cell_sphere_core.analysis.process_summary_atlas_contract import validate_process_summary_atlas_analysis

CASES = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze process summary atlas protocol results.')
    p.add_argument('--input', type=str, required=True)
    p.add_argument('--output', type=str, required=True)
    p.add_argument('--title', type=str, default='Process summary atlas protocol analysis')
    return p.parse_args()


def _case_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        'dominant_mode': str(summary.get('dominant_mode', 'none')),
        'dominant_axis': str(summary.get('dominant_axis', 'none')),
        'phase_coverage': dict(summary.get('phase_coverage', {})),
        'overall_scores': dict(summary.get('overall_scores', {})),
        'active_dominant_mode': str(summary.get('active_dominant_mode', 'none')),
        'active_dominant_axis': str(summary.get('active_dominant_axis', 'none')),
        'phase_summaries': dict(summary.get('phase_summaries', {})),
        'active_signature': dict(summary.get('active_signature', {})),
    }


def build_analysis(report: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'suite': str(report.get('suite', 'process_summary_atlas_protocol')),
        'cases': {},
        'gates': {},
    }
    for case_name in CASES:
        summary = dict(report['cases'][case_name]['process_summary_atlas_summary'])
        payload['cases'][case_name] = _case_payload(summary)
    payload['gates'] = {
        'static_mode': payload['cases']['floating_static']['dominant_mode'],
        'translation_pos_active_mode': payload['cases']['translation_x_pos']['active_dominant_mode'],
        'translation_neg_active_mode': payload['cases']['translation_x_neg']['active_dominant_mode'],
        'translation_pos_active_axis': payload['cases']['translation_x_pos']['active_dominant_axis'],
        'translation_neg_active_axis': payload['cases']['translation_x_neg']['active_dominant_axis'],
        'rotation_pos_active_mode': payload['cases']['rotation_z_pos']['active_dominant_mode'],
        'rotation_neg_active_mode': payload['cases']['rotation_z_neg']['active_dominant_mode'],
        'rotation_pos_active_axis': payload['cases']['rotation_z_pos']['active_dominant_axis'],
        'rotation_neg_active_axis': payload['cases']['rotation_z_neg']['active_dominant_axis'],
        'translation_active_pos_signal': float(payload['cases']['translation_x_pos']['active_signature'].get('mean_polarity_projection', 0.0)),
        'translation_active_neg_signal': float(payload['cases']['translation_x_neg']['active_signature'].get('mean_polarity_projection', 0.0)),
        'rotation_active_pos_signal': float(payload['cases']['rotation_z_pos']['active_signature'].get('mean_circulation_projection', 0.0)),
        'rotation_active_neg_signal': float(payload['cases']['rotation_z_neg']['active_signature'].get('mean_circulation_projection', 0.0)),
    }
    payload['contracts'] = validate_process_summary_atlas_analysis(payload)
    return payload


def render_png(analysis: dict[str, Any], output_dir: Path, title: str) -> None:
    labels = [name.replace('_', '\n') for name in CASES]
    overall = [float(max(analysis['cases'][name]['overall_scores'].values())) for name in CASES]
    active = [float(max(analysis['cases'][name]['phase_summaries']['active']['phase_scores'].values())) for name in CASES]
    tx = [float(analysis['cases'][name]['active_signature'].get('mean_polarity_projection', 0.0)) for name in CASES]
    rz = [float(analysis['cases'][name]['active_signature'].get('mean_circulation_projection', 0.0)) for name in CASES]
    xs = list(range(len(labels)))
    plt.figure(figsize=(10.5, 4.8))
    plt.plot(xs, overall, marker='o', label='overall max support')
    plt.plot(xs, active, marker='o', label='active max support')
    plt.plot(xs, tx, marker='o', label='active polarity projection')
    plt.plot(xs, rz, marker='o', label='active circulation projection')
    plt.xticks(xs, labels)
    plt.title(title)
    plt.ylabel('score')
    plt.axhline(0.0, linewidth=1.0)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_summary_atlas_overview.png', dpi=180)
    plt.close()


def analyze_report_file(*, report_path: str | Path, output_dir: str | Path, title: str = 'Process summary atlas protocol analysis') -> dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(report)
    (output_dir / 'process_summary_atlas_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, title)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_report_file(report_path=args.input, output_dir=args.output, title=args.title)


if __name__ == '__main__':
    main()
