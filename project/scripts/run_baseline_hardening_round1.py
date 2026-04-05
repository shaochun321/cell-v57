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
    p = argparse.ArgumentParser(description='Run baseline hardening round 1 protocols.')
    p.add_argument('--num-cells', type=int, default=50)
    p.add_argument('--t-end', type=float, default=0.08)
    p.add_argument('--dt', type=float, default=0.0012)
    p.add_argument('--translation-accel', type=float, default=75.0)
    p.add_argument('--rotation-alpha', type=float, default=380.0)
    p.add_argument('--onset-fraction', type=float, default=0.25)
    p.add_argument('--duration-fraction', type=float, default=0.40)
    p.add_argument('--floating-support-center-k', type=float, default=18.0)
    p.add_argument('--floating-support-com-damping-c', type=float, default=8.0)
    p.add_argument('--floating-support-radial-k', type=float, default=30.0)
    p.add_argument('--floating-support-radial-shell-bias', type=float, default=0.60)
    p.add_argument('--floating-support-internal-drag-c', type=float, default=7.0)
    p.add_argument('--floating-support-center-scale-active', type=float, default=0.15)
    p.add_argument('--floating-support-radial-scale-active', type=float, default=0.95)
    p.add_argument('--outdir', type=str, default='outputs/baseline_hardening_round1')
    return p.parse_args()


def _compact_summary(summary: dict, outdir: Path) -> dict:
    return {
        'summary_path': 'summary.json',
        'near_sphere_score': float(summary.get('near_sphere_score', 0.0)),
        'final_metrics': dict(summary.get('final_metrics', {})),
        'equilibrium_diagnostics': dict(summary.get('equilibrium_diagnostics', {})),
        'interface_network_diagnostics': dict(summary.get('interface_network_diagnostics', {})),
        'simulator_status': dict(summary.get('simulator_status', {})),
    }


def _run_case(base_outdir: Path, name: str, *, args: argparse.Namespace, **kwargs) -> dict:
    cfg = GravityConfig(
        num_cells=args.num_cells,
        t_end=args.t_end,
        dt=args.dt,
        disable_gravity=True,
        sensor_record_every=max(1, int((args.t_end / args.dt) / 12)),
        record_every=max(1, int((args.t_end / args.dt) / 12)),
        vestibular_onset_fraction=args.onset_fraction,
        vestibular_duration_fraction=args.duration_fraction,
        floating_support_center_k=args.floating_support_center_k,
        floating_support_com_damping_c=args.floating_support_com_damping_c,
        floating_support_radial_k=args.floating_support_radial_k,
        floating_support_radial_shell_bias=args.floating_support_radial_shell_bias,
        floating_support_internal_drag_c=args.floating_support_internal_drag_c,
        floating_support_center_scale_active=args.floating_support_center_scale_active,
        floating_support_radial_scale_active=args.floating_support_radial_scale_active,
        **kwargs,
    )
    outdir = base_outdir / name
    result = run_gravity(cfg, outdir=outdir, save_outputs=True)
    return _compact_summary(result.summary, outdir)


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report = {
        'suite': 'baseline_hardening_round1',
        'config': vars(args),
        'cases': {
            'floating_static': _run_case(outdir, 'floating_static', args=args),
            'translation_x_pos': _run_case(outdir, 'translation_x_pos', args=args, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=1.0),
            'translation_x_neg': _run_case(outdir, 'translation_x_neg', args=args, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=-1.0),
            'rotation_z_pos': _run_case(outdir, 'rotation_z_pos', args=args, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=1.0),
            'rotation_z_neg': _run_case(outdir, 'rotation_z_neg', args=args, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=-1.0),
        },
    }
    report_path = outdir / 'baseline_hardening_round1_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'硬化报告: {report_path}')


if __name__ == '__main__':
    main()
