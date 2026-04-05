from __future__ import annotations

import argparse
import json
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
    p = argparse.ArgumentParser(description="Run the Step 20 direction-polarity and constrained-propagation protocol.")
    p.add_argument("--num-cells", type=int, default=180)
    p.add_argument("--t-end", type=float, default=0.18)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--outdir", type=str, default="outputs/step20_protocol")
    p.add_argument("--translation-accel", type=float, default=80.0)
    p.add_argument("--rotation-alpha", type=float, default=500.0)
    p.add_argument("--onset-fraction", type=float, default=0.20)
    p.add_argument("--duration-fraction", type=float, default=0.60)
    return p.parse_args()


def _extract_track_report(summary: dict) -> dict:
    diag = summary.get("interface_network_diagnostics", {})
    tracks = diag.get("tracks", {})
    out: dict[str, dict] = {}
    for name, payload in tracks.items():
        active = payload.get("active_summary", {})
        active_channels = active.get("mean_global_channels", {})
        out[name] = {
            "mean_global_channels": payload.get("mean_global_channels", {}),
            "mean_spatial_coherence": payload.get("mean_spatial_coherence", 0.0),
            "mean_transfer_std": payload.get("mean_transfer_std", 0.0),
            "protocol_aligned_flux_margin": payload.get("protocol_aligned_flux_margin", 0.0),
            "active_summary": active,
            "axis_balance": active.get("axis_balance", {}),
            "signed_polarity": float(active_channels.get("mean_signed_polarity", 0.0)),
            "signed_circulation": float(active_channels.get("mean_signed_circulation", 0.0)),
        }
    return out


def _run_one(base_outdir: Path, name: str, **kwargs) -> dict:
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
    result = run_gravity(cfg, outdir=outdir, save_outputs=True)
    return {
        "summary": result.summary,
        "track_report": _extract_track_report(result.summary),
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    common = {
        "num_cells": args.num_cells,
        "t_end": args.t_end,
        "dt": args.dt,
        "vestibular_onset_fraction": args.onset_fraction,
        "vestibular_duration_fraction": args.duration_fraction,
    }
    report = {
        "floating_static": _run_one(outdir, "floating_static", **common),
        "translation_x_pos": _run_one(
            outdir,
            "translation_x_pos",
            vestibular_motion="translation",
            vestibular_linear_accel=args.translation_accel,
            vestibular_linear_axis="x",
            vestibular_linear_sign=1.0,
            **common,
        ),
        "translation_x_neg": _run_one(
            outdir,
            "translation_x_neg",
            vestibular_motion="translation",
            vestibular_linear_accel=args.translation_accel,
            vestibular_linear_axis="x",
            vestibular_linear_sign=-1.0,
            **common,
        ),
        "rotation_z_pos": _run_one(
            outdir,
            "rotation_z_pos",
            vestibular_motion="rotation",
            vestibular_angular_accel=args.rotation_alpha,
            vestibular_rotation_axis="z",
            vestibular_rotation_sign=1.0,
            **common,
        ),
        "rotation_z_neg": _run_one(
            outdir,
            "rotation_z_neg",
            vestibular_motion="rotation",
            vestibular_angular_accel=args.rotation_alpha,
            vestibular_rotation_axis="z",
            vestibular_rotation_sign=-1.0,
            **common,
        ),
    }
    report_path = outdir / "step20_protocol_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"输出目录: {outdir}")
    print(f"汇总报告: {report_path}")


if __name__ == "__main__":
    main()
