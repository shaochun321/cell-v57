from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json
import os
import sys

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def build_cases(translation_accel: float, rotation_accel: float) -> dict[str, dict]:
    return {
        "baseline": {"disable_gravity": True},
        "translation_x_pos": {
            "disable_gravity": True,
            "vestibular_motion": "translation",
            "vestibular_linear_axis": "x",
            "vestibular_linear_sign": 1.0,
            "vestibular_linear_accel": translation_accel,
        },
        "translation_x_neg": {
            "disable_gravity": True,
            "vestibular_motion": "translation",
            "vestibular_linear_axis": "x",
            "vestibular_linear_sign": -1.0,
            "vestibular_linear_accel": translation_accel,
        },
        "rotation_z_pos": {
            "disable_gravity": True,
            "vestibular_motion": "rotation",
            "vestibular_rotation_axis": "z",
            "vestibular_rotation_sign": 1.0,
            "vestibular_angular_accel": rotation_accel,
        },
    }


def is_complete_run(outdir: Path) -> bool:
    return all((outdir / name).exists() for name in REQUIRED_OUTPUTS)


PROFILES: dict[str, dict[str, float]] = {
    "baseline": {},
    "medium_balanced": {
        "global_damping": 1.2,
        "tissue_inner_damping_scale": 1.75,
        "tissue_outer_damping_scale": 1.25,
        "tissue_band_damping_c": 7.0,
        "tissue_pressure_rate_damping_c": 24.0,
        "tissue_radial_rate_damping_c": 4.0,
        "tissue_shell_tangential_damping_c": 3.0,
    },
    "medium_outer_shell": {
        "global_damping": 1.0,
        "tissue_inner_damping_scale": 1.55,
        "tissue_outer_damping_scale": 1.6,
        "tissue_band_damping_c": 8.5,
        "tissue_pressure_rate_damping_c": 22.0,
        "tissue_radial_rate_damping_c": 3.4,
        "tissue_shell_tangential_damping_c": 3.8,
    },
}

REQUIRED_OUTPUTS = [
    "summary.json",
    "interface_trace.json",
    "interface_network_trace.json",
    "interface_temporal_trace.json",
    "readout_trace.json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the stage-1 medium/sign audit panel.")
    p.add_argument("--outdir", type=str, default="outputs/stage1_medium_sign_audit")
    p.add_argument("--reference-dir", type=str, default="outputs/stage1_scale_sign_audit/N64")
    p.add_argument("--num-cells", type=int, default=96)
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    p.add_argument("--profiles", type=str, nargs="+", default=["baseline", "medium_balanced", "medium_outer_shell"])
    p.add_argument("--t-end", type=float, default=0.12)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--record-every", type=int, default=10)
    p.add_argument("--sensor-record-every", type=int, default=10)
    p.add_argument("--translation-accel", type=float, default=300.0)
    p.add_argument("--rotation-accel", type=float, default=1500.0)
    return p.parse_args()



def run_case(outdir: Path, cfg: GravityConfig) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    result = run_gravity(cfg, outdir)
    return result.summary



def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    cases = build_cases(args.translation_accel, args.rotation_accel)
    selected_profiles = {name: PROFILES[name] for name in args.profiles}

    manifest: dict[str, object] = {
        "protocol": "stage1_medium_sign_audit",
        "reference_dir": args.reference_dir,
        "num_cells": args.num_cells,
        "seeds": args.seeds,
        "profiles": selected_profiles,
        "cases": {},
    }

    for profile_name, profile_overrides in selected_profiles.items():
        for seed in args.seeds:
            for case_name, overrides in cases.items():
                cfg = GravityConfig(
                    num_cells=args.num_cells,
                    rng_seed=seed,
                    t_end=args.t_end,
                    dt=args.dt,
                    record_every=args.record_every,
                    sensor_record_every=args.sensor_record_every,
                    **profile_overrides,
                    **overrides,
                )
                case_outdir = outdir / profile_name / f"seed_{seed}" / case_name
                summary_path = case_outdir / "summary.json"
                print(f"[RUN] {profile_name} seed={seed} case={case_name}", flush=True)
                try:
                    if summary_path.exists() and is_complete_run(case_outdir):
                        summary = json.loads(summary_path.read_text())
                    else:
                        summary = run_case(case_outdir, cfg)
                    manifest["cases"][f"{profile_name}/seed_{seed}/{case_name}"] = {
                        "config": asdict(cfg),
                        "summary": summary,
                    }
                    print(f"[OK] {profile_name} seed={seed} case={case_name}", flush=True)
                except Exception as exc:
                    manifest["cases"][f"{profile_name}/seed_{seed}/{case_name}"] = {
                        "config": asdict(cfg),
                        "error": repr(exc),
                    }
                    print(f"[ERR] {profile_name} seed={seed} case={case_name}: {exc!r}", flush=True)

    (outdir / "stage1_medium_sign_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    print(f"[OK] stage-1 medium/sign audit outputs: {outdir}")


if __name__ == "__main__":
    main()
