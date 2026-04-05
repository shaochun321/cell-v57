from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from cell_sphere_core.analysis.mirror_shell_contract import validate_mirror_shell_analysis

CASES = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze mirrored multi-channel interface shell protocol results.')
    p.add_argument('--input', required=True, type=str)
    p.add_argument('--output', required=True, type=str)
    p.add_argument('--title', type=str, default='Mirror shell interface protocol analysis')
    return p.parse_args()


def build_analysis(report: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {'suite': 'mirror_shell_interface_protocol', 'cases': {}, 'gates': {}, 'contracts': {}}
    for name in CASES:
        summary = report['cases'][name]['mirror_shell_summary']
        active = summary.get('active_summary', {})
        payload['cases'][name] = {
            'dominant_mode': str(summary.get('dominant_mode', 'none')),
            'dominant_phase': str(summary.get('dominant_phase', 'none')),
            'phase_counts': dict(summary.get('phase_counts', {})),
            'phase_dominant_modes': dict(summary.get('phase_dominant_modes', {})),
            'active_dominant_mode': str(active.get('dominant_mode', 'none')),
            'mean_shell_strength': float(summary.get('mean_shell_strength', 0.0)),
            'max_shell_index': int(summary.get('max_shell_index', -1)),
            'outermost_shell': dict(active.get('outermost_shell', {})),
        }

    payload['gates'] = {
        'static_mode': payload['cases']['floating_static']['dominant_mode'],
        'translation_pos_active_mode': payload['cases']['translation_x_pos']['active_dominant_mode'],
        'translation_neg_active_mode': payload['cases']['translation_x_neg']['active_dominant_mode'],
        'rotation_pos_active_mode': payload['cases']['rotation_z_pos']['active_dominant_mode'],
        'rotation_neg_active_mode': payload['cases']['rotation_z_neg']['active_dominant_mode'],
        'translation_outer_x_pos': float(payload['cases']['translation_x_pos']['outermost_shell'].get('axis_polarity_balance', {}).get('x', 0.0)),
        'translation_outer_x_neg': float(payload['cases']['translation_x_neg']['outermost_shell'].get('axis_polarity_balance', {}).get('x', 0.0)),
        'rotation_outer_z_pos': float(payload['cases']['rotation_z_pos']['outermost_shell'].get('circulation_axis_balance', {}).get('z', 0.0)),
        'rotation_outer_z_neg': float(payload['cases']['rotation_z_neg']['outermost_shell'].get('circulation_axis_balance', {}).get('z', 0.0)),
    }
    payload['contracts'] = validate_mirror_shell_analysis(payload)
    return payload


def render_png(analysis: dict[str, Any], output_dir: Path, title: str) -> None:
    labels = [name.replace('_', '\n') for name in CASES]
    strengths = [float(analysis['cases'][name]['mean_shell_strength']) for name in CASES]
    outer_x = [float(analysis['cases'][name]['outermost_shell'].get('axis_polarity_balance', {}).get('x', 0.0)) for name in CASES]
    outer_z = [float(analysis['cases'][name]['outermost_shell'].get('circulation_axis_balance', {}).get('z', 0.0)) for name in CASES]
    xs = list(range(len(labels)))
    plt.figure(figsize=(10, 4.8))
    plt.plot(xs, strengths, marker='o', label='mean shell strength')
    plt.plot(xs, outer_x, marker='o', label='outer shell x polarity balance')
    plt.plot(xs, outer_z, marker='o', label='outer shell z circulation balance')
    plt.xticks(xs, labels)
    plt.title(title)
    plt.ylabel('score')
    plt.axhline(0.0, linewidth=1.0)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'mirror_shell_interface_overview.png', dpi=180)
    plt.close()


def analyze_report_file(*, report_path: str | Path, output_dir: str | Path, title: str = 'Mirror shell interface protocol analysis') -> dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(report)
    (output_dir / 'mirror_shell_interface_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, title)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_report_file(report_path=args.input, output_dir=args.output, title=args.title)


if __name__ == '__main__':
    main()
