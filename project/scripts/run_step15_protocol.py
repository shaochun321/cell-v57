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
from cell_sphere_core.analysis.multipole import analyze_sensor_frames, load_sensor_nodes_jsonl, summarize_energy_series
from cell_sphere_core.analysis.process_state import summarize_process_state_trace


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the Step 15 floating process-state protocol.")
    p.add_argument("--num-cells", type=int, default=180)
    p.add_argument("--t-end", type=float, default=0.14)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--outdir", type=str, default="outputs/step15_protocol")
    p.add_argument("--translation-accel", type=float, default=80.0)
    p.add_argument("--rotation-alpha", type=float, default=500.0)
    return p.parse_args()


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
    motion_trace = json.loads((outdir / "motion_state_trace.json").read_text(encoding="utf-8"))
    process_summary = summarize_process_state_trace(motion_trace)
    node_frames = load_sensor_nodes_jsonl(outdir / "sensor_nodes.jsonl")
    active_frames = [fr for fr in node_frames if fr.get("stimulus", {}).get("active")]
    multipole_summary = summarize_energy_series(analyze_sensor_frames(active_frames or node_frames, band="outer", field_name="v_r"))
    return {
        "summary": result.summary,
        "process_state": process_summary,
        "multipole": multipole_summary,
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    common = {"num_cells": args.num_cells, "t_end": args.t_end, "dt": args.dt}
    report = {
        "floating_static": _run_one(outdir, "floating_static", **common),
        "floating_translation": _run_one(outdir, "floating_translation", vestibular_motion="translation", vestibular_linear_accel=args.translation_accel, **common),
        "floating_rotation": _run_one(outdir, "floating_rotation", vestibular_motion="rotation", vestibular_angular_accel=args.rotation_alpha, **common),
    }
    report_path = outdir / "step15_protocol_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"输出目录: {outdir}")
    print(f"汇总报告: {report_path}")


if __name__ == "__main__":
    main()
