from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from cell_sphere_core.analysis.mirror_channel_atlas_contract import validate_mirror_channel_atlas_analysis

CASES = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze mirrored multi-channel atlas protocol results.')
    p.add_argument('--input', required=True, type=str)
    p.add_argument('--output', required=True, type=str)
    p.add_argument('--title', type=str, default='Mirror channel atlas protocol analysis')
    return p.parse_args()


def build_analysis(report: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {'suite': 'mirror_channel_atlas_protocol', 'cases': {}, 'gates': {}, 'contracts': {}}
    for name in CASES:
        summary = report['cases'][name]['mirror_channel_atlas_summary']
        active = summary.get('active_summary', {})
        payload['cases'][name] = {
            'dominant_mode': str(summary.get('dominant_mode', 'none')),
            'dominant_axis': str(summary.get('dominant_axis', 'none')),
            'dominant_phase': str(summary.get('dominant_phase', 'none')),
            'phase_counts': dict(summary.get('phase_counts', {})),
            'phase_dominant_modes': dict(summary.get('phase_dominant_modes', {})),
            'active_dominant_mode': str(active.get('dominant_mode', 'none')),
            'active_dominant_axis': str(active.get('dominant_axis', 'none')),
            'mean_pair_strength': float(summary.get('mean_pair_strength', 0.0)),
            'max_shell_index': int(summary.get('max_shell_index', -1)),
            'strongest_pair': dict(active.get('strongest_pair', {})),
        }
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
        'translation_pair_pos': float(payload['cases']['translation_x_pos']['strongest_pair'].get('differential_channels', {}).get('polarity_projection', 0.0)),
        'translation_pair_neg': float(payload['cases']['translation_x_neg']['strongest_pair'].get('differential_channels', {}).get('polarity_projection', 0.0)),
        'rotation_pair_pos': float(payload['cases']['rotation_z_pos']['strongest_pair'].get('differential_channels', {}).get('circulation_projection', 0.0)),
        'rotation_pair_neg': float(payload['cases']['rotation_z_neg']['strongest_pair'].get('differential_channels', {}).get('circulation_projection', 0.0)),
    }
    payload['contracts'] = validate_mirror_channel_atlas_analysis(payload)
    return payload


def render_png(analysis: dict[str, Any], output_dir: Path, title: str) -> None:
    labels = [name.replace('_', '\n') for name in CASES]
    strengths = [float(analysis['cases'][name]['mean_pair_strength']) for name in CASES]
    trans = [float(analysis['cases'][name]['strongest_pair'].get('differential_channels', {}).get('polarity_projection', 0.0)) for name in CASES]
    rot = [float(analysis['cases'][name]['strongest_pair'].get('differential_channels', {}).get('circulation_projection', 0.0)) for name in CASES]
    xs = list(range(len(labels)))
    plt.figure(figsize=(10, 4.8))
    plt.plot(xs, strengths, marker='o', label='mean pair strength')
    plt.plot(xs, trans, marker='o', label='atlas polarity differential')
    plt.plot(xs, rot, marker='o', label='atlas circulation differential')
    plt.xticks(xs, labels)
    plt.title(title)
    plt.ylabel('score')
    plt.axhline(0.0, linewidth=1.0)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'mirror_channel_atlas_overview.png', dpi=180)
    plt.close()


def analyze_report_file(*, report_path: str | Path, output_dir: str | Path, title: str = 'Mirror channel atlas protocol analysis') -> dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(report)
    (output_dir / 'mirror_channel_atlas_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, title)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_report_file(report_path=args.input, output_dir=args.output, title=args.title)


if __name__ == '__main__':
    main()
