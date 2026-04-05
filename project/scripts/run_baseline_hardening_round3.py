from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / 'src'
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run baseline hardening round 3 protocols.')
    p.add_argument('--num-cells', type=int, default=55)
    p.add_argument('--t-end', type=float, default=0.09)
    p.add_argument('--dt', type=float, default=0.0011)
    p.add_argument('--translation-accel', type=float, default=85.0)
    p.add_argument('--rotation-alpha', type=float, default=400.0)
    p.add_argument('--onset-fraction', type=float, default=0.24)
    p.add_argument('--duration-fraction', type=float, default=0.42)
    p.add_argument('--translation-center-scale-active', type=float, default=0.12)
    p.add_argument('--translation-radial-scale-active', type=float, default=0.88)
    p.add_argument('--outdir', type=str, default='outputs/baseline_hardening_round3')
    return p.parse_args()


def _compact_summary(summary: dict) -> dict:
    return {
        'summary_path': 'summary.json',
        'near_sphere_score': float(summary.get('near_sphere_score', 0.0)),
        'final_metrics': dict(summary.get('final_metrics', {})),
        'equilibrium_diagnostics': dict(summary.get('equilibrium_diagnostics', {})),
        'interface_network_diagnostics': dict(summary.get('interface_network_diagnostics', {})),
        'simulator_status': dict(summary.get('simulator_status', {})),
        'tissue_config': dict(summary.get('tissue_config', {})),
    }


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
        'floating_support_com_damping_c': 9.5,
        'floating_support_radial_k': 34.0,
        'floating_support_radial_shell_bias': 0.70,
        'floating_support_internal_drag_c': 8.5,
        'floating_support_center_scale_active': 0.14,
        'floating_support_radial_scale_active': 0.92,
        'tissue_inner_damping_scale': 1.75,
        'tissue_outer_damping_scale': 0.82,
        'tissue_outer_shear_scale': 1.60,
        'tissue_band_radial_damping_c': 7.2,
        'tissue_band_tangential_damping_c': 2.0,
        'tissue_radial_rate_damping_c': 3.6,
        'tissue_shell_tangential_damping_c': 1.6,
        'tissue_shell_neighbor_support_k': 12.0,
    }
    params.update(overrides)
    return GravityConfig(**params)


def _run_case(base_outdir: Path, name: str, cfg: GravityConfig) -> dict:
    outdir = base_outdir / name
    result = run_gravity(cfg, outdir=outdir, save_outputs=True)
    return _compact_summary(result.summary)


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    static_cfg = _base_config(args)
    translation_cfg_pos = _base_config(
        args,
        vestibular_motion='translation',
        vestibular_linear_accel=args.translation_accel,
        vestibular_linear_axis='x',
        vestibular_linear_sign=1.0,
        floating_support_center_scale_active=args.translation_center_scale_active,
        floating_support_radial_scale_active=args.translation_radial_scale_active,
    )
    translation_cfg_neg = _base_config(
        args,
        vestibular_motion='translation',
        vestibular_linear_accel=args.translation_accel,
        vestibular_linear_axis='x',
        vestibular_linear_sign=-1.0,
        floating_support_center_scale_active=args.translation_center_scale_active,
        floating_support_radial_scale_active=args.translation_radial_scale_active,
    )
    rotation_cfg_pos = _base_config(
        args,
        vestibular_motion='rotation',
        vestibular_angular_accel=args.rotation_alpha,
        vestibular_rotation_axis='z',
        vestibular_rotation_sign=1.0,
    )
    rotation_cfg_neg = _base_config(
        args,
        vestibular_motion='rotation',
        vestibular_angular_accel=args.rotation_alpha,
        vestibular_rotation_axis='z',
        vestibular_rotation_sign=-1.0,
    )

    report = {
        'suite': 'baseline_hardening_round3',
        'config': vars(args),
        'cases': {
            'floating_static': _run_case(outdir, 'floating_static', static_cfg),
            'translation_x_pos': _run_case(outdir, 'translation_x_pos', translation_cfg_pos),
            'translation_x_neg': _run_case(outdir, 'translation_x_neg', translation_cfg_neg),
            'rotation_z_pos': _run_case(outdir, 'rotation_z_pos', rotation_cfg_pos),
            'rotation_z_neg': _run_case(outdir, 'rotation_z_neg', rotation_cfg_neg),
        },
    }
    report_path = outdir / 'baseline_hardening_round3_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'硬化报告: {report_path}')


if __name__ == '__main__':
    main()
