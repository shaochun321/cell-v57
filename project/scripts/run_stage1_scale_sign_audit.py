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

REQUIRED_OUTPUTS = [
    "summary.json",
    "interface_trace.json",
    "interface_network_trace.json",
    "interface_temporal_trace.json",
    "readout_trace.json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the stage-1 scale/sign audit panel.")
    p.add_argument("--outdir", type=str, default="outputs/stage1_scale_sign_audit")
    p.add_argument("--num-cells", type=int, nargs="+", default=[64, 96])
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    p.add_argument("--t-end", type=float, default=0.12)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--record-every", type=int, default=10)
    p.add_argument("--sensor-record-every", type=int, default=10)
    p.add_argument("--translation-accel", type=float, default=300.0)
    p.add_argument("--rotation-accel", type=float, default=1500.0)
    return p.parse_args()


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


def run_case(outdir: Path, cfg: GravityConfig) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    result = run_gravity(cfg, outdir)
    return result.summary


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    cases = build_cases(args.translation_accel, args.rotation_accel)
    manifest: dict[str, object] = {
        "protocol": "stage1_scale_sign_audit",
        "num_cells": args.num_cells,
        "seeds": args.seeds,
        "t_end": args.t_end,
        "dt": args.dt,
        "record_every": args.record_every,
        "sensor_record_every": args.sensor_record_every,
        "cases": {},
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
                case_outdir = outdir / f"N{num_cells}" / f"seed_{seed}" / case_name
                summary_path = case_outdir / "summary.json"
                if summary_path.exists() and is_complete_run(case_outdir):
                    summary = json.loads(summary_path.read_text())
                else:
                    summary = run_case(case_outdir, cfg)
                manifest["cases"][f"N{num_cells}/seed_{seed}/{case_name}"] = {
                    "config": asdict(cfg),
                    "summary": summary,
                }

    (outdir / "stage1_scale_sign_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    print(f"[OK] stage-1 scale/sign audit outputs: {outdir}")


if __name__ == "__main__":
    main()
