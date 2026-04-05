from __future__ import annotations

import argparse, json, os, sys
from dataclasses import asdict
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

REQUIRED_OUTPUTS = [
    'summary.json',
    'interface_trace.json',
    'interface_network_trace.json',
    'interface_temporal_trace.json',
    'readout_trace.json',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run seen-scale early_sharp nuisance panel for rescue derivation.')
    p.add_argument('--outdir', type=str, default='outputs/stage1_early_sharp_seen_nuisance_panel_raw')
    p.add_argument('--num-cells', type=int, nargs='+', default=[64, 96, 128])
    p.add_argument('--seeds', type=int, nargs='+', default=[7, 8, 9])
    p.add_argument('--t-end', type=float, default=0.12)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--record-every', type=int, default=10)
    p.add_argument('--sensor-record-every', type=int, default=10)
    return p.parse_args()


def build_cases() -> dict[str, dict]:
    return {
        'baseline': {'disable_gravity': True},
        'translation_x_pos_early_sharp': {
            'disable_gravity': True,
            'vestibular_motion': 'translation',
            'vestibular_linear_axis': 'x',
            'vestibular_linear_sign': 1.0,
            'vestibular_linear_accel': 360.0,
            'vestibular_onset_fraction': 0.25,
            'vestibular_duration_fraction': 0.32,
        },
        'translation_x_neg_early_sharp': {
            'disable_gravity': True,
            'vestibular_motion': 'translation',
            'vestibular_linear_axis': 'x',
            'vestibular_linear_sign': -1.0,
            'vestibular_linear_accel': 360.0,
            'vestibular_onset_fraction': 0.25,
            'vestibular_duration_fraction': 0.32,
        },
        'rotation_z_pos_early_sharp': {
            'disable_gravity': True,
            'vestibular_motion': 'rotation',
            'vestibular_rotation_axis': 'z',
            'vestibular_rotation_sign': 1.0,
            'vestibular_angular_accel': 2200.0,
            'vestibular_onset_fraction': 0.25,
            'vestibular_duration_fraction': 0.32,
        },
    }


def is_complete_run(outdir: Path) -> bool:
    return all((outdir / name).exists() for name in REQUIRED_OUTPUTS)


def run_case(outdir: Path, cfg: GravityConfig) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    result = run_gravity(cfg, outdir)
    return result.summary


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    cases = build_cases()
    manifest: dict[str, object] = {
        'protocol': 'stage1_early_sharp_seen_nuisance_panel',
        'num_cells': args.num_cells,
        'seeds': args.seeds,
        'cases': {},
    }
    for num_cells in args.num_cells:
        for seed in args.seeds:
            for case_name, overrides in cases.items():
                cfg = GravityConfig(
                    num_cells=num_cells,
                    rng_seed=seed,
                    t_end=args.t_end,
                    dt=args.dt,
                    record_every=args.record_every,
                    sensor_record_every=args.sensor_record_every,
                    **overrides,
                )
                case_outdir = outdir / f'N{num_cells}' / f'seed_{seed}' / case_name
                summary_path = case_outdir / 'summary.json'
                try:
                    if summary_path.exists() and is_complete_run(case_outdir):
                        summary = json.loads(summary_path.read_text())
                    else:
                        summary = run_case(case_outdir, cfg)
                    manifest['cases'][f'N{num_cells}/seed_{seed}/{case_name}'] = {
                        'config': asdict(cfg), 'summary': summary,
                    }
                    print(f'[OK] N{num_cells} seed={seed} case={case_name}', flush=True)
                except Exception as exc:
                    manifest['cases'][f'N{num_cells}/seed_{seed}/{case_name}'] = {
                        'config': asdict(cfg), 'error': repr(exc),
                    }
                    print(f'[ERR] N{num_cells} seed={seed} case={case_name}: {exc!r}', flush=True)
    (outdir / 'stage1_early_sharp_seen_nuisance_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'[OK] early_sharp seen nuisance panel written to {outdir}')


if __name__ == '__main__':
    main()
