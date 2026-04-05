from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from cell_sphere_core.analysis.process_calculator import build_process_calculator_trace_from_files, summarize_process_calculator_trace

CASE_ORDER = (
    'floating_static',
    'translation_x_pos',
    'translation_x_neg',
    'rotation_z_pos',
    'rotation_z_neg',
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run the process calculator protocol suite on the current hardened baseline.')
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
    p.add_argument('--outdir', type=str, default='outputs/process_calculator_protocol')
    p.add_argument('--rng-seed', type=int, default=7)
    return p.parse_args()


def _base_config(args: argparse.Namespace, **overrides: float) -> GravityConfig:
    params = {
        'num_cells': args.num_cells,
        't_end': args.t_end,
        'dt': args.dt,
        'disable_gravity': True,
        'sensor_record_every': max(1, int((args.t_end / args.dt) / 12)),
        'record_every': max(1, int((args.t_end / args.dt) / 12)),
        'vestibular_onset_fraction': args.onset_fraction,
        'vestibular_duration_fraction': args.duration_fraction,
        'floating_support_center_k': 22.0,
        'floating_support_com_damping_c': args.floating_com_damping,
        'floating_support_radial_k': 34.0,
        'floating_support_radial_shell_bias': 0.70,
        'floating_support_internal_drag_c': args.floating_internal_drag,
        'floating_support_center_scale_active': 0.14,
        'floating_support_radial_scale_active': 0.92,
        'tissue_inner_damping_scale': 1.75,
        'tissue_outer_damping_scale': 0.82,
        'tissue_outer_shear_scale': 1.60,
        'tissue_band_radial_damping_c': args.radial_band_damping,
        'tissue_band_tangential_damping_c': 2.0,
        'tissue_radial_rate_damping_c': 3.6,
        'tissue_shell_tangential_damping_c': 1.6,
        'tissue_shell_neighbor_support_k': 12.0,
        'rng_seed': int(getattr(args, 'rng_seed', 7)),
    }
    params.update(overrides)
    return GravityConfig(**params)


def build_case_configs(args: argparse.Namespace) -> dict[str, GravityConfig]:
    return {
        'floating_static': _base_config(args),
        'translation_x_pos': _base_config(
            args,
            vestibular_motion='translation',
            vestibular_linear_accel=args.translation_accel,
            vestibular_linear_axis='x',
            vestibular_linear_sign=1.0,
            floating_support_center_scale_active=args.translation_center_scale_active,
            floating_support_radial_scale_active=args.translation_radial_scale_active,
        ),
        'translation_x_neg': _base_config(
            args,
            vestibular_motion='translation',
            vestibular_linear_accel=args.translation_accel,
            vestibular_linear_axis='x',
            vestibular_linear_sign=-1.0,
            floating_support_center_scale_active=args.translation_center_scale_active,
            floating_support_radial_scale_active=args.translation_radial_scale_active,
        ),
        'rotation_z_pos': _base_config(
            args,
            vestibular_motion='rotation',
            vestibular_angular_accel=args.rotation_alpha,
            vestibular_rotation_axis='z',
            vestibular_rotation_sign=1.0,
        ),
        'rotation_z_neg': _base_config(
            args,
            vestibular_motion='rotation',
            vestibular_angular_accel=args.rotation_alpha,
            vestibular_rotation_axis='z',
            vestibular_rotation_sign=-1.0,
        ),
    }


def _run_case(base_outdir: Path, name: str, cfg: GravityConfig, *, window_size: int, stride: int) -> dict[str, Any]:
    outdir = base_outdir / name
    result = run_gravity(cfg, outdir=outdir, save_outputs=True)
    calc_trace = build_process_calculator_trace_from_files(
        motion_state_path=outdir / 'motion_state_trace.json',
        readout_path=outdir / 'readout_trace.json',
        interface_network_path=outdir / 'interface_network_trace.json',
        window_size=window_size,
        stride=stride,
    )
    calc_path = outdir / 'process_calculator_trace.json'
    calc_path.write_text(json.dumps(calc_trace, ensure_ascii=False, indent=2), encoding='utf-8')
    calc_summary = summarize_process_calculator_trace(calc_trace)
    return {
        'summary_path': 'summary.json',
        'process_calculator_trace_file': calc_path.name,
        'process_calculator_summary': calc_summary,
        'near_sphere_score': float(result.summary.get('near_sphere_score', 0.0)),
        'equilibrium_diagnostics': dict(result.summary.get('equilibrium_diagnostics', {})),
        'interface_network_diagnostics': dict(result.summary.get('interface_network_diagnostics', {})),
    }


def run_protocol_suite(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    case_configs = build_case_configs(args)
    report = {
        'suite': 'process_calculator_protocol',
        'config': vars(args),
        'case_order': list(CASE_ORDER),
        'cases': {},
    }
    for case_name in CASE_ORDER:
        report['cases'][case_name] = _run_case(
            outdir,
            case_name,
            case_configs[case_name],
            window_size=args.window_size,
            stride=args.stride,
        )
    report_path = outdir / 'process_calculator_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    report['report_path'] = str(report_path)
    return report


def main() -> None:
    args = parse_args()
    report = run_protocol_suite(args)
    print(f"输出目录: {args.outdir}")
    print(f"协议报告: {report['report_path']}")


if __name__ == '__main__':
    main()
