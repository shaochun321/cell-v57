from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_mirrored_readout_audit import (
    summarize_active_x_shell_profiles_from_file,
    audit_translation_mirrored_readout,
)
try:
    from scripts.run_mirror_channel_atlas_protocol import run_protocol as run_atlas_protocol
except ModuleNotFoundError:  # pragma: no cover
    from run_mirror_channel_atlas_protocol import run_protocol as run_atlas_protocol

TRANSLATION_CASES = ('translation_x_pos', 'translation_x_neg')


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--seeds', type=str, default='7,8')
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
    p.add_argument('--outdir', required=True)
    p.add_argument('--keep-scratch', action='store_true')
    return p.parse_args()


def _int_list(value: str) -> list[int]:
    return [int(float(part.strip())) for part in value.split(',') if part.strip()]


def run_protocol(args: argparse.Namespace) -> dict[str, str | dict]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    scratch_root = outdir / '_seed_scratch'
    scratch_root.mkdir(parents=True, exist_ok=True)
    seeds = _int_list(args.seeds)
    seed_profiles = {
        'suite': 'process_summary_translation_mirrored_readout_seed_profiles',
        'seeds': seeds,
        'reference_seed': seeds[0] if seeds else 0,
        'cases': {},
    }
    for case in TRANSLATION_CASES:
        seed_profiles['cases'][case] = {}

    for seed in seeds:
        seed_dir = scratch_root / f'seed_{seed}'
        report = run_atlas_protocol(argparse.Namespace(
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
            outdir=str(seed_dir),
            rng_seed=int(seed),
        ))
        for case in TRANSLATION_CASES:
            trace_path = seed_dir / case / 'mirror_channel_atlas_trace.json'
            case_profile = summarize_active_x_shell_profiles_from_file(trace_path)
            case_profile['mean_polarity_projection'] = float(
                case_profile['shell_profiles'].get(str(case_profile['strongest_shell_by_translation_mass']), {}).get('polarity_signed', 0.0)
            )
            seed_profiles['cases'][case][str(seed)] = case_profile

    seed_profiles_path = outdir / 'process_summary_translation_mirrored_readout_seed_profiles.json'
    seed_profiles_path.write_text(json.dumps(seed_profiles, indent=2), encoding='utf-8')
    audit = audit_translation_mirrored_readout(seed_profiles)
    audit_path = outdir / 'process_summary_translation_mirrored_readout_audit.json'
    audit_path.write_text(json.dumps(audit, indent=2), encoding='utf-8')

    if not getattr(args, 'keep_scratch', False):
        shutil.rmtree(scratch_root, ignore_errors=True)

    return {
        'seed_profiles_path': str(seed_profiles_path),
        'audit_path': str(audit_path),
        'audit': audit,
    }


def main() -> None:
    args = parse_args()
    result = run_protocol(args)
    print(result['audit_path'])


if __name__ == '__main__':
    main()
