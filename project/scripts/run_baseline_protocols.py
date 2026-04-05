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
    p = argparse.ArgumentParser(description='Run a compact reality-alignment baseline suite.')
    p.add_argument('--num-cells', type=int, default=70)
    p.add_argument('--t-end', type=float, default=0.12)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--translation-accel', type=float, default=80.0)
    p.add_argument('--rotation-alpha', type=float, default=420.0)
    p.add_argument('--onset-fraction', type=float, default=0.25)
    p.add_argument('--duration-fraction', type=float, default=0.45)
    p.add_argument('--outdir', type=str, default='outputs/baseline_protocols')
    return p.parse_args()


def _compact_summary(summary: dict, outdir: Path) -> dict:
    interface_diag = summary.get('interface_network_diagnostics', {})
    return {
        'summary_path': str((outdir / 'summary.json').name),
        'near_sphere_score': float(summary.get('near_sphere_score', 0.0)),
        'final_metrics': dict(summary.get('final_metrics', {})),
        'equilibrium_diagnostics': dict(summary.get('equilibrium_diagnostics', {})),
        'interface_network_diagnostics': interface_diag,
        'simulator_status': dict(summary.get('simulator_status', {})),
    }


def _run_case(base_outdir: Path, name: str, *, num_cells: int, t_end: float, dt: float, onset_fraction: float, duration_fraction: float, **kwargs) -> dict:
    cfg = GravityConfig(
        num_cells=num_cells,
        t_end=t_end,
        dt=dt,
        disable_gravity=True,
        sensor_record_every=10,
        record_every=10,
        vestibular_onset_fraction=onset_fraction,
        vestibular_duration_fraction=duration_fraction,
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
        'suite': 'baseline_protocols',
        'config': {
            'num_cells': args.num_cells,
            't_end': args.t_end,
            'dt': args.dt,
            'translation_accel': args.translation_accel,
            'rotation_alpha': args.rotation_alpha,
            'onset_fraction': args.onset_fraction,
            'duration_fraction': args.duration_fraction,
        },
        'cases': {
            'floating_static': _run_case(outdir, 'floating_static', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, onset_fraction=args.onset_fraction, duration_fraction=args.duration_fraction),
            'translation_x_pos': _run_case(outdir, 'translation_x_pos', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, onset_fraction=args.onset_fraction, duration_fraction=args.duration_fraction, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=1.0),
            'translation_x_neg': _run_case(outdir, 'translation_x_neg', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, onset_fraction=args.onset_fraction, duration_fraction=args.duration_fraction, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=-1.0),
            'rotation_z_pos': _run_case(outdir, 'rotation_z_pos', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, onset_fraction=args.onset_fraction, duration_fraction=args.duration_fraction, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=1.0),
            'rotation_z_neg': _run_case(outdir, 'rotation_z_neg', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, onset_fraction=args.onset_fraction, duration_fraction=args.duration_fraction, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=-1.0),
        },
    }
    report_path = outdir / 'baseline_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'协议报告: {report_path}')


if __name__ == '__main__':
    main()
