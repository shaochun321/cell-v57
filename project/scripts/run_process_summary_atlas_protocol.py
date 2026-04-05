from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.process_summary_atlas import build_process_summary_atlas_from_files
try:
    from scripts.run_mirror_temporal_bundle_protocol import CASE_ORDER, run_protocol as run_temporal_bundle_protocol
except ModuleNotFoundError:  # pragma: no cover
    from run_mirror_temporal_bundle_protocol import CASE_ORDER, run_protocol as run_temporal_bundle_protocol


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run the process summary atlas protocol from mirrored temporal bundle outputs.')
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
    p.add_argument('--outdir', type=str, default='outputs/process_summary_atlas_protocol_r1')
    p.add_argument('--reuse-existing', action='store_true', help='reuse existing mirror temporal bundle traces under outdir instead of rerunning upstream protocol')
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    reuse_existing = bool(getattr(args, "reuse_existing", False))
    temporal_report = None if reuse_existing else run_temporal_bundle_protocol(args)
    report = {
        'suite': 'process_summary_atlas_protocol',
        'config': vars(args),
        'case_order': list(CASE_ORDER),
        'temporal_report_path': str(temporal_report['report_path']) if temporal_report is not None else '',
        'cases': {},
    }
    for case_name in CASE_ORDER:
        case_dir = outdir / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        atlas_trace_path = case_dir / 'mirror_channel_atlas_trace.json'
        if reuse_existing and not atlas_trace_path.exists():
            raise FileNotFoundError(f'missing existing atlas trace: {atlas_trace_path}')
        summary = build_process_summary_atlas_from_files(atlas_trace_path=atlas_trace_path)
        summary_path = case_dir / 'process_summary_atlas.json'
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        report['cases'][case_name] = {
            'mirror_channel_atlas_trace_file': atlas_trace_path.name,
            'process_summary_atlas_file': summary_path.name,
            'process_summary_atlas_summary': summary,
        }
    report_path = outdir / 'process_summary_atlas_protocol_report.json'
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
