from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.mirror_channel_atlas import (
    build_mirror_channel_atlas_trace_from_files,
    summarize_mirror_channel_atlas_trace,
)
try:
    from scripts.run_mirror_shell_interface_protocol import CASE_ORDER, run_protocol as run_shell_protocol
except ModuleNotFoundError:  # pragma: no cover - CLI fallback
    from run_mirror_shell_interface_protocol import CASE_ORDER, run_protocol as run_shell_protocol


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run the mirrored multi-channel atlas protocol on the current hardened baseline.')
    p.add_argument('--num-cells', type=int, default=55)
    p.add_argument('--t-end', type=float, default=0.09)
    p.add_argument('--dt', type=float, default=0.0011)
    p.add_argument('--translation-accel', type=float, default=85.0)
    p.add_argument('--rotation-alpha', type=float, default=400.0)
    p.add_argument('--onset-fraction', type=float, default=0.24)
    p.add_argument('--duration-fraction', type=float, default=0.42)
    p.add_argument('--floating-com-damping', type=float, default=9.9)
    p.add_argument('--floating-internal-drag', type=float, default=8.7)
    p.add_argument('--radial-band-damping', type=float, default=7.35)
    p.add_argument('--translation-center-scale-active', type=float, default=0.12)
    p.add_argument('--translation-radial-scale-active', type=float, default=0.88)
    p.add_argument('--window-size', type=int, default=3)
    p.add_argument('--stride', type=int, default=1)
    p.add_argument('--outdir', type=str, default='outputs/mirror_channel_atlas_protocol_r1')
    return p.parse_args()




def _expected_translation_signs(case_name: str) -> dict[str, float]:
    if case_name == 'translation_x_pos':
        return {'x': 1.0}
    if case_name == 'translation_x_neg':
        return {'x': -1.0}
    return {}

def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    shell_report = run_shell_protocol(args)
    report = {
        'suite': 'mirror_channel_atlas_protocol',
        'config': vars(args),
        'case_order': list(CASE_ORDER),
        'shell_report_path': str(shell_report['report_path']),
        'cases': {},
    }
    for case_name in CASE_ORDER:
        case_dir = outdir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        shell_trace_path = case_dir / 'mirror_shell_interface_trace.json'
        atlas_trace = build_mirror_channel_atlas_trace_from_files(
            shell_trace_path=shell_trace_path,
            expected_translation_signs=_expected_translation_signs(case_name),
        )
        atlas_trace_path = case_dir / 'mirror_channel_atlas_trace.json'
        atlas_trace_path.write_text(json.dumps(atlas_trace, ensure_ascii=False, indent=2), encoding='utf-8')
        atlas_summary = summarize_mirror_channel_atlas_trace(atlas_trace)
        report['cases'][case_name] = {
            'mirror_shell_interface_trace_file': shell_trace_path.name,
            'mirror_channel_atlas_trace_file': atlas_trace_path.name,
            'mirror_channel_atlas_summary': atlas_summary,
        }
    report_path = outdir / 'mirror_channel_atlas_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    report['report_path'] = str(report_path)
    return report


def main() -> None:
    args = parse_args()
    report = run_protocol(args)
    print(f'输出目录: {args.outdir}')
    print(f'协议报告: {report["report_path"]}')


if __name__ == '__main__':
    main()
