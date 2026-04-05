from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

REQUIRED = ['summary.json', 'interface_trace.json', 'interface_network_trace.json', 'interface_temporal_trace.json']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run a harder unseen-nuisance cross-scale panel including farther unseen scale N192 for overview-first validation.')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n192_harder_nuisance_panel_raw')
    p.add_argument('--num-cells', type=int, nargs='+', default=[64, 96, 128, 192])
    p.add_argument('--seeds', type=int, nargs='+', default=[7, 8])
    p.add_argument('--t-end', type=float, default=0.12)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--record-every', type=int, default=10)
    p.add_argument('--sensor-record-every', type=int, default=10)
    return p.parse_args()


def build_cases() -> dict[str, dict]:
    # unseen combinations relative to the earlier early_sharp/mid_balanced/late_soft panel
    return {
        'baseline': {'disable_gravity': True},
        'translation_x_pos_early_soft': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': 1.0,
            'vestibular_linear_accel': 240.0, 'vestibular_onset_fraction': 0.25, 'vestibular_duration_fraction': 0.50,
        },
        'translation_x_pos_mid_sharp': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': 1.0,
            'vestibular_linear_accel': 360.0, 'vestibular_onset_fraction': 0.44, 'vestibular_duration_fraction': 0.32,
        },
        'translation_x_pos_late_balanced': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': 1.0,
            'vestibular_linear_accel': 300.0, 'vestibular_onset_fraction': 0.58, 'vestibular_duration_fraction': 0.46,
        },
        'translation_x_neg_early_soft': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': -1.0,
            'vestibular_linear_accel': 240.0, 'vestibular_onset_fraction': 0.25, 'vestibular_duration_fraction': 0.50,
        },
        'translation_x_neg_mid_sharp': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': -1.0,
            'vestibular_linear_accel': 360.0, 'vestibular_onset_fraction': 0.44, 'vestibular_duration_fraction': 0.32,
        },
        'translation_x_neg_late_balanced': {
            'disable_gravity': True, 'vestibular_motion': 'translation', 'vestibular_linear_axis': 'x', 'vestibular_linear_sign': -1.0,
            'vestibular_linear_accel': 300.0, 'vestibular_onset_fraction': 0.58, 'vestibular_duration_fraction': 0.46,
        },
        'rotation_z_pos_early_soft': {
            'disable_gravity': True, 'vestibular_motion': 'rotation', 'vestibular_rotation_axis': 'z', 'vestibular_rotation_sign': 1.0,
            'vestibular_angular_accel': 2400.0, 'vestibular_onset_fraction': 0.25, 'vestibular_duration_fraction': 0.50,
        },
        'rotation_z_pos_mid_sharp': {
            'disable_gravity': True, 'vestibular_motion': 'rotation', 'vestibular_rotation_axis': 'z', 'vestibular_rotation_sign': 1.0,
            'vestibular_angular_accel': 3600.0, 'vestibular_onset_fraction': 0.44, 'vestibular_duration_fraction': 0.32,
        },
        'rotation_z_pos_late_balanced': {
            'disable_gravity': True, 'vestibular_motion': 'rotation', 'vestibular_rotation_axis': 'z', 'vestibular_rotation_sign': 1.0,
            'vestibular_angular_accel': 3000.0, 'vestibular_onset_fraction': 0.58, 'vestibular_duration_fraction': 0.46,
        },
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    cases = build_cases()
    for n in args.num_cells:
        for seed in args.seeds:
            seed_dir = outdir / f'N{n}' / f'seed_{seed}'
            seed_dir.mkdir(parents=True, exist_ok=True)
            for case_name, params in cases.items():
                case_dir = seed_dir / case_name
                if case_dir.exists() and all((case_dir / r).exists() for r in REQUIRED):
                    continue
                case_dir.mkdir(parents=True, exist_ok=True)
                cfg = GravityConfig(
                    num_cells=n,
                    rng_seed=seed,
                    t_end=args.t_end,
                    dt=args.dt,
                    record_every=args.record_every,
                    sensor_record_every=args.sensor_record_every,
                    **params,
                )
                run_gravity(cfg, outdir=case_dir, save_outputs=True)


if __name__ == '__main__':
    main()
