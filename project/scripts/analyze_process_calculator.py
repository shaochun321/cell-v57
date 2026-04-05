from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from cell_sphere_core.analysis.process_protocol_contract import validate_protocol_analysis

CASES = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze process calculator protocol results.')
    p.add_argument('--input', required=True, type=str)
    p.add_argument('--output', required=True, type=str)
    p.add_argument('--title', type=str, default='Process calculator protocol analysis')
    return p.parse_args()


def build_analysis(report: dict[str, Any]) -> dict[str, Any]:
    cases = report['cases']
    payload: dict[str, Any] = {'suite': 'process_calculator_protocol', 'cases': {}, 'gates': {}, 'contracts': {}}
    for name in CASES:
        case = cases[name]
        summary = case['process_calculator_summary']
        phase_windows = summary.get('phase_windows', {})
        active = summary.get('active_summary', {})
        payload['cases'][name] = {
            'dominant_mode': summary.get('dominant_mode', 'none'),
            'dominant_phase': summary.get('dominant_phase', 'none'),
            'mean_stability_score': float(summary.get('mean_stability_score', 0.0)),
            'mean_recovery_score': float(summary.get('mean_recovery_score', 0.0)),
            'mean_mode_margin': float(summary.get('mean_mode_margin', 0.0)),
            'phase_counts': dict(summary.get('phase_counts', {})),
            'phase_dominant_modes': {k: str(v.get('dominant_mode', 'none')) for k, v in phase_windows.items()},
            'active_dominant_mode': str(active.get('dominant_mode', 'none')),
            'active_mean_mode_margin': float(active.get('mean_mode_margin', 0.0)),
        }

    payload['gates'] = {
        'static_baseline_mode': payload['cases']['floating_static']['dominant_mode'],
        'translation_pos_active_mode': payload['cases']['translation_x_pos']['active_dominant_mode'],
        'translation_neg_active_mode': payload['cases']['translation_x_neg']['active_dominant_mode'],
        'rotation_pos_active_mode': payload['cases']['rotation_z_pos']['active_dominant_mode'],
        'rotation_neg_active_mode': payload['cases']['rotation_z_neg']['active_dominant_mode'],
        'translation_has_baseline': 'baseline' in payload['cases']['translation_x_pos']['phase_counts'],
        'translation_has_active': 'active' in payload['cases']['translation_x_pos']['phase_counts'],
        'translation_has_recovery': 'recovery' in payload['cases']['translation_x_pos']['phase_counts'],
        'rotation_has_baseline': 'baseline' in payload['cases']['rotation_z_pos']['phase_counts'],
        'rotation_has_active': 'active' in payload['cases']['rotation_z_pos']['phase_counts'],
        'rotation_has_recovery': 'recovery' in payload['cases']['rotation_z_pos']['phase_counts'],
    }
    payload['contracts'] = validate_protocol_analysis(payload)
    return payload


def render_png(analysis: dict[str, Any], output_dir: Path, title: str) -> None:
    labels = []
    stabilities = []
    margins = []
    for name in CASES:
        labels.append(name.replace('_', '\n'))
        stabilities.append(float(analysis['cases'][name]['mean_stability_score']))
        margins.append(float(analysis['cases'][name]['mean_mode_margin']))

    xs = list(range(len(labels)))
    plt.figure(figsize=(9, 4.5))
    plt.plot(xs, stabilities, marker='o', label='mean stability')
    plt.plot(xs, margins, marker='o', label='mean mode margin')
    plt.xticks(xs, labels)
    plt.ylim(0.0, 1.05)
    plt.ylabel('score')
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'process_calculator_overview.png', dpi=180)
    plt.close()


def analyze_report_file(*, report_path: str | Path, output_dir: str | Path, title: str = 'Process calculator protocol analysis') -> dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(report)
    (output_dir / 'process_calculator_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, title)
    return analysis


def main() -> None:
    args = parse_args()
    analyze_report_file(report_path=args.input, output_dir=args.output, title=args.title)


if __name__ == '__main__':
    main()
