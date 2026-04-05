from __future__ import annotations

import argparse
from pathlib import Path
import sys
import os

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the Step 14 floating protocol.")
    p.add_argument("--num-cells", type=int, default=180)
    p.add_argument("--t-end", type=float, default=0.12)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--outdir", type=str, default="outputs/step14_protocol")
    p.add_argument("--translation-accel", type=float, default=80.0)
    p.add_argument("--rotation-alpha", type=float, default=500.0)
    return p.parse_args()


def _run_one(base_outdir: Path, name: str, **kwargs) -> None:
    cfg = GravityConfig(
        num_cells=kwargs.pop("num_cells"),
        t_end=kwargs.pop("t_end"),
        dt=kwargs.pop("dt"),
        disable_gravity=True,
        sensor_record_every=10,
        record_every=10,
        **kwargs,
    )
    outdir = base_outdir / name
    run_gravity(cfg, outdir=outdir, save_outputs=True)


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    common = {"num_cells": args.num_cells, "t_end": args.t_end, "dt": args.dt}
    _run_one(outdir, "floating_static", **common)
    _run_one(outdir, "floating_translation", vestibular_motion="translation", vestibular_linear_accel=args.translation_accel, **common)
    _run_one(outdir, "floating_rotation", vestibular_motion="rotation", vestibular_angular_accel=args.rotation_alpha, **common)
    print(f"输出目录: {outdir}")


if __name__ == "__main__":
    main()
