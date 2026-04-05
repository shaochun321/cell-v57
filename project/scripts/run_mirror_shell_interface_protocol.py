from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.mirror_shell_interface import (
    build_mirror_shell_interface_trace_from_files,
    summarize_mirror_shell_interface_trace,
)
try:
    from scripts.run_process_calculator_protocol import CASE_ORDER, run_protocol_suite
except ModuleNotFoundError:  # pragma: no cover - CLI fallback
    from run_process_calculator_protocol import CASE_ORDER, run_protocol_suite


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run the mirrored multi-channel interface shell protocol on the current hardened baseline.')
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
    p.add_argument('--outdir', type=str, default='outputs/mirror_shell_interface_protocol_r1')
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base_report = run_protocol_suite(args)
    report = {
        'suite': 'mirror_shell_interface_protocol',
        'config': vars(args),
        'case_order': list(CASE_ORDER),
        'base_report_path': str(base_report['report_path']),
        'cases': {},
    }
    for case_name in CASE_ORDER:
        case_dir = outdir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        process_case_dir = outdir / case_name
        process_trace_path = process_case_dir / 'process_calculator_trace.json'
        interface_network_path = process_case_dir / 'interface_network_trace.json'
        shell_trace = build_mirror_shell_interface_trace_from_files(
            process_calculator_path=process_trace_path,
            interface_network_path=interface_network_path,
        )
        shell_trace_path = process_case_dir / 'mirror_shell_interface_trace.json'
        shell_trace_path.write_text(json.dumps(shell_trace, ensure_ascii=False, indent=2), encoding='utf-8')
        shell_summary = summarize_mirror_shell_interface_trace(shell_trace)
        report['cases'][case_name] = {
            'process_calculator_trace_file': process_trace_path.name,
            'interface_network_trace_file': interface_network_path.name,
            'mirror_shell_interface_trace_file': shell_trace_path.name,
            'mirror_shell_summary': shell_summary,
        }
    report_path = outdir / 'mirror_shell_interface_protocol_report.json'
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
