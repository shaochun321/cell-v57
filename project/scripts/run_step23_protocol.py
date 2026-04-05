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
    p = argparse.ArgumentParser(description="Run the Step 23 interface-topology protocol.")
    p.add_argument("--num-cells", type=int, default=180)
    p.add_argument("--t-end", type=float, default=0.18)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--outdir", type=str, default="outputs/step23_protocol")
    p.add_argument("--translation-accel", type=float, default=80.0)
    p.add_argument("--rotation-alpha", type=float, default=500.0)
    p.add_argument("--onset-fraction", type=float, default=0.20)
    p.add_argument("--duration-fraction", type=float, default=0.60)
    return p.parse_args()


def _extract_report(summary: dict) -> dict:
    diag = summary.get("interface_topology_diagnostics", {})
    tracks = diag.get("tracks", {})
    out: dict[str, dict] = {}
    for name, payload in tracks.items():
        out[name] = {
            "family_shell_mean": payload.get("family_shell_mean", {}),
            "active_family_shell_mean": payload.get("active_family_shell_mean", {}),
            "family_response_roughness": payload.get("family_response_roughness", {}),
            "active_family_response_roughness": payload.get("active_family_response_roughness", {}),
            "edge_weight_mean": payload.get("edge_weight_mean", 0.0),
            "active_edge_weight_mean": payload.get("active_edge_weight_mean", 0.0),
            "lateral_edge_weight_mean": payload.get("lateral_edge_weight_mean", 0.0),
            "active_lateral_edge_weight_mean": payload.get("active_lateral_edge_weight_mean", 0.0),
            "radial_edge_weight_mean": payload.get("radial_edge_weight_mean", 0.0),
            "active_radial_edge_weight_mean": payload.get("active_radial_edge_weight_mean", 0.0),
            "axis_polarity_balance": payload.get("axis_polarity_balance", {}),
            "active_axis_polarity_balance": payload.get("active_axis_polarity_balance", {}),
            "mean_signed_circulation": payload.get("mean_signed_circulation", 0.0),
            "active_mean_signed_circulation": payload.get("active_mean_signed_circulation", 0.0),
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
        "topology_report": _extract_report(result.summary),
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
    report_path = outdir / "step23_protocol_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"输出目录: {outdir}")
    print(f"汇总报告: {report_path}")


if __name__ == "__main__":
    main()
