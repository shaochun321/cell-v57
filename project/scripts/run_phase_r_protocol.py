from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import os

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / 'src'
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.phase_r import summarize_phase_r_audit
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run Phase R robustness audit with rotation repair focus.')
    p.add_argument('--num-cells', type=int, default=100)
    p.add_argument('--t-end', type=float, default=0.16)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--translation-accel', type=float, default=80.0)
    p.add_argument('--rotation-alpha', type=float, default=500.0)
    p.add_argument('--outdir', type=str, default='outputs/phase_r_sample')
    return p.parse_args()


def _extract_report(summary: dict) -> dict:
    return dict(summary.get('channel_motif_diagnostics', {}))


def _run_one(base_outdir: Path, name: str, *, num_cells: int, t_end: float, dt: float, translation_accel: float, rotation_alpha: float, onset_fraction: float = 0.2, duration_fraction: float = 0.6, **kwargs) -> dict:
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
    return {'summary': result.summary, 'motif_report': _extract_report(result.summary)}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    soft_cells = max(80, args.num_cells - 20)
    soft_translation = 0.8 * args.translation_accel
    soft_rotation = 0.8 * args.rotation_alpha

    report = {
        'floating_static_base': _run_one(outdir, 'floating_static_base', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, translation_accel=args.translation_accel, rotation_alpha=args.rotation_alpha),
        'floating_static_soft': _run_one(outdir, 'floating_static_soft', num_cells=soft_cells, t_end=args.t_end, dt=args.dt, translation_accel=soft_translation, rotation_alpha=soft_rotation),
        'translation_x_pos_base': _run_one(outdir, 'translation_x_pos_base', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, translation_accel=args.translation_accel, rotation_alpha=args.rotation_alpha, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=1.0),
        'translation_x_neg_base': _run_one(outdir, 'translation_x_neg_base', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, translation_accel=args.translation_accel, rotation_alpha=args.rotation_alpha, vestibular_motion='translation', vestibular_linear_accel=args.translation_accel, vestibular_linear_axis='x', vestibular_linear_sign=-1.0),
        'rotation_z_pos_base': _run_one(outdir, 'rotation_z_pos_base', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, translation_accel=args.translation_accel, rotation_alpha=args.rotation_alpha, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=1.0),
        'rotation_z_neg_base': _run_one(outdir, 'rotation_z_neg_base', num_cells=args.num_cells, t_end=args.t_end, dt=args.dt, translation_accel=args.translation_accel, rotation_alpha=args.rotation_alpha, vestibular_motion='rotation', vestibular_angular_accel=args.rotation_alpha, vestibular_rotation_axis='z', vestibular_rotation_sign=-1.0),
        'translation_x_pos_soft': _run_one(outdir, 'translation_x_pos_soft', num_cells=soft_cells, t_end=args.t_end, dt=args.dt, translation_accel=soft_translation, rotation_alpha=soft_rotation, vestibular_motion='translation', vestibular_linear_accel=soft_translation, vestibular_linear_axis='x', vestibular_linear_sign=1.0),
        'translation_x_neg_soft': _run_one(outdir, 'translation_x_neg_soft', num_cells=soft_cells, t_end=args.t_end, dt=args.dt, translation_accel=soft_translation, rotation_alpha=soft_rotation, vestibular_motion='translation', vestibular_linear_accel=soft_translation, vestibular_linear_axis='x', vestibular_linear_sign=-1.0),
        'rotation_z_pos_soft': _run_one(outdir, 'rotation_z_pos_soft', num_cells=soft_cells, t_end=args.t_end, dt=args.dt, translation_accel=soft_translation, rotation_alpha=soft_rotation, vestibular_motion='rotation', vestibular_angular_accel=soft_rotation, vestibular_rotation_axis='z', vestibular_rotation_sign=1.0),
        'rotation_z_neg_soft': _run_one(outdir, 'rotation_z_neg_soft', num_cells=soft_cells, t_end=args.t_end, dt=args.dt, translation_accel=soft_translation, rotation_alpha=soft_rotation, vestibular_motion='rotation', vestibular_angular_accel=soft_rotation, vestibular_rotation_axis='z', vestibular_rotation_sign=-1.0),
    }
    report_path = outdir / 'phase_r_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = summarize_phase_r_audit(report)
    audit_path = outdir / 'phase_r_audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'协议报告: {report_path}')
    print(f'Phase R 审计: {audit_path}')


if __name__ == '__main__':
    main()
