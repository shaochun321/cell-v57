from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.process_summary_repeatability import summarize_process_summary_repeatability
try:
    from scripts.run_process_summary_atlas_protocol import run_protocol as run_process_summary_protocol
    from scripts.analyze_process_summary_atlas import analyze_report_file
except ModuleNotFoundError:  # pragma: no cover
    from run_process_summary_atlas_protocol import run_protocol as run_process_summary_protocol
    from analyze_process_summary_atlas import analyze_report_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run small-seed repeatability audit for the process summary atlas stack.')
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
    p.add_argument('--outdir', type=str, default='outputs/process_summary_repeatability_r1')
    p.add_argument('--reuse-existing', action='store_true', help='reuse existing per-seed process summary atlas reports when present')
    return p.parse_args()

def _int_list(value: str) -> list[int]:
    return [int(float(part.strip())) for part in value.split(',') if part.strip()]

def _seed_namespace(args: argparse.Namespace, *, seed: int, outdir: Path, reuse_existing: bool) -> argparse.Namespace:
    return argparse.Namespace(
        num_cells=args.num_cells,
        t_end=args.t_end,
        dt=args.dt,
        translation_accel=args.translation_accel,
        rotation_alpha=args.rotation_alpha,
        onset_fraction=args.onset_fraction,
        duration_fraction=args.duration_fraction,
        floating_com_damping=args.floating_com_damping,
        floating_internal_drag=args.floating_internal_drag,
        radial_band_damping=args.radial_band_damping,
        translation_center_scale_active=args.translation_center_scale_active,
        translation_radial_scale_active=args.translation_radial_scale_active,
        window_size=args.window_size,
        stride=args.stride,
        outdir=str(outdir),
        reuse_existing=bool(reuse_existing),
        rng_seed=int(seed),
    )

def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seeds = _int_list(args.seeds)
    report: dict[str, Any] = {
        'suite': 'process_summary_repeatability_protocol',
        'metadata': {
            'seeds': seeds,
            'num_cells': int(args.num_cells),
            't_end': float(args.t_end),
            'dt': float(args.dt),
            'translation_accel': float(args.translation_accel),
            'rotation_alpha': float(args.rotation_alpha),
        },
        'seed_runs': [],
    }
    for seed in seeds:
        seed_dir = outdir / f'seed_{seed}'
        seed_dir.mkdir(parents=True, exist_ok=True)
        protocol_report_path = seed_dir / 'process_summary_atlas_protocol_report.json'
        can_reuse = bool(getattr(args, 'reuse_existing', False)) and protocol_report_path.exists()
        seed_args = _seed_namespace(args, seed=seed, outdir=seed_dir, reuse_existing=can_reuse)
        if can_reuse:
            protocol_report = json.loads(protocol_report_path.read_text(encoding='utf-8'))
            protocol_report['report_path'] = str(protocol_report_path)
        else:
            protocol_report = run_process_summary_protocol(seed_args)
        analysis = analyze_report_file(
            report_path=protocol_report['report_path'],
            output_dir=seed_dir / 'analysis',
            title=f'Process summary atlas repeatability seed {seed}',
        )
        report['seed_runs'].append({
            'seed': seed,
            'report_path': str(protocol_report['report_path']),
            'analysis_path': str(seed_dir / 'analysis' / 'process_summary_atlas_analysis.json'),
            'analysis': analysis,
        })
    report_path = outdir / 'process_summary_repeatability_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = summarize_process_summary_repeatability(report)
    audit_path = outdir / 'process_summary_repeatability_audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'report_path': str(report_path), 'audit_path': str(audit_path), 'audit': audit}

def main() -> None:
    args = parse_args()
    payload = run_protocol(args)
    print(f'输出目录: {args.outdir}')
    print(f'协议报告: {payload["report_path"]}')
    print(f'重复性审计: {payload["audit_path"]}')

if __name__ == '__main__':
    main()
