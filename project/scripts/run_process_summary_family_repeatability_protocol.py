from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.process_summary_family_repeatability import summarize_process_summary_family_repeatability
try:
    from scripts.run_process_summary_repeatability_protocol import run_protocol as run_repeatability_protocol
except ModuleNotFoundError:  # pragma: no cover
    from run_process_summary_repeatability_protocol import run_protocol as run_repeatability_protocol


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Build family-level repeatability audit from process summary repeatability outputs.')
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
    p.add_argument('--seeds', type=str, default='7,8')
    p.add_argument('--outdir', type=str, default='outputs/process_summary_family_repeatability_r1')
    p.add_argument('--reuse-existing', action='store_true')
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    repeatability_report_path = outdir / 'process_summary_repeatability_protocol_report.json'
    can_reuse = bool(getattr(args, 'reuse_existing', False)) and repeatability_report_path.exists()
    if can_reuse:
        report = json.loads(repeatability_report_path.read_text(encoding='utf-8'))
    else:
        report_payload = run_repeatability_protocol(args)
        report = json.loads(Path(report_payload['report_path']).read_text(encoding='utf-8'))
        if Path(report_payload['report_path']) != repeatability_report_path:
            repeatability_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            audit_src = Path(report_payload['audit_path'])
            audit_dst = outdir / 'process_summary_repeatability_audit.json'
            if audit_src.exists() and audit_src != audit_dst:
                audit_dst.write_text(audit_src.read_text(encoding='utf-8'), encoding='utf-8')
    family_audit = summarize_process_summary_family_repeatability(report)
    family_audit_path = outdir / 'process_summary_family_repeatability_audit.json'
    family_audit_path.write_text(json.dumps(family_audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return {
        'report_path': str(repeatability_report_path),
        'family_audit_path': str(family_audit_path),
        'family_audit': family_audit,
    }


def main() -> None:
    args = parse_args()
    payload = run_protocol(args)
    print(f'输出目录: {args.outdir}')
    print(f'复用/协议报告: {payload["report_path"]}')
    print(f'家族重复性审计: {payload["family_audit_path"]}')


if __name__ == '__main__':
    main()
