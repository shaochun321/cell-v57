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

import csv
import json

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

DEFAULT_COUNTS = [100, 300, 500, 800]

def parse_float_grid(raw: str) -> list[float]:
    values = [float(x.strip()) for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("grid must not be empty")
    return values

def parse_int_grid(raw: str) -> list[int]:
    values = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("grid must not be empty")
    return values

def parse_counts(raw: str) -> list[int]:
    values = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not values or any(v <= 0 for v in values):
        raise ValueError("counts must be a comma separated list of positive integers")
    return values

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--counts", type=str, default=",".join(str(x) for x in DEFAULT_COUNTS))
    p.add_argument("--tension-grid", type=str, default="14,18,22")
    p.add_argument("--pressure-grid", type=str, default="700,900,1100")
    p.add_argument("--radial-bands-grid", type=str, default="3,4,5")
    p.add_argument("--local-pressure-grid", type=str, default="70,90")
    p.add_argument("--shell-curvature-grid", type=str, default="40,55")
    p.add_argument("--band-interface-grid", type=str, default="16,24,32")
    p.add_argument("--band-restoring-grid", type=str, default="24,30,36")
    p.add_argument("--shell-reference-grid", type=str, default="46,56,66")
    p.add_argument("--bulk-reference-grid", type=str, default="6,8")
    p.add_argument("--outer-stiffness-grid", type=str, default="1.35")
    p.add_argument("--inner-damping-grid", type=str, default="1.55")
    p.add_argument("--outer-shear-grid", type=str, default="1.45")
    p.add_argument("--band-damping-grid", type=str, default="5.0")
    p.add_argument("--gravity-ramp-grid", type=str, default="0.18,0.22")
    p.add_argument("--settle-damping-grid", type=str, default="2.6,3.0")
    p.add_argument("--settle-pressure-grid", type=str, default="1.3,1.4")
    p.add_argument("--settle-shell-grid", type=str, default="1.1,1.2")
    p.add_argument("--cell-radius", type=float, default=0.004)
    p.add_argument("--packing-fraction", type=float, default=0.68)
    p.add_argument("--radius-safety-factor", type=float, default=1.02)
    p.add_argument("--t-end", type=float, default=0.6)
    p.add_argument("--dt", type=float, default=0.001)
    p.add_argument("--disable-foam-tissue", action="store_true")
    p.add_argument("--outdir", type=str, default="outputs/calibration")
    return p.parse_args()

def main() -> None:
    args = parse_args()
    counts = parse_counts(args.counts)
    tension_grid = parse_float_grid(args.tension_grid)
    pressure_grid = parse_float_grid(args.pressure_grid)
    radial_bands_grid = parse_int_grid(args.radial_bands_grid)
    local_pressure_grid = parse_float_grid(args.local_pressure_grid)
    shell_curvature_grid = parse_float_grid(args.shell_curvature_grid)
    band_interface_grid = parse_float_grid(args.band_interface_grid)
    band_restoring_grid = parse_float_grid(args.band_restoring_grid)
    shell_reference_grid = parse_float_grid(args.shell_reference_grid)
    bulk_reference_grid = parse_float_grid(args.bulk_reference_grid)
    outer_stiffness_grid = parse_float_grid(args.outer_stiffness_grid)
    inner_damping_grid = parse_float_grid(args.inner_damping_grid)
    outer_shear_grid = parse_float_grid(args.outer_shear_grid)
    band_damping_grid = parse_float_grid(args.band_damping_grid)
    gravity_ramp_grid = parse_float_grid(args.gravity_ramp_grid)
    settle_damping_grid = parse_float_grid(args.settle_damping_grid)
    settle_pressure_grid = parse_float_grid(args.settle_pressure_grid)
    settle_shell_grid = parse_float_grid(args.settle_shell_grid)
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows=[]; best_row=None
    radial_bands_values = [1] if args.disable_foam_tissue else radial_bands_grid
    local_grid = [0.0] if args.disable_foam_tissue else local_pressure_grid
    curvature_grid = [0.0] if args.disable_foam_tissue else shell_curvature_grid
    interface_grid = [0.0] if args.disable_foam_tissue else band_interface_grid
    band_restoring_values = [0.0] if args.disable_foam_tissue else band_restoring_grid
    shell_reference_values = [0.0] if args.disable_foam_tissue else shell_reference_grid
    bulk_reference_values = [0.0] if args.disable_foam_tissue else bulk_reference_grid
    stiffness_grid = [1.0] if args.disable_foam_tissue else outer_stiffness_grid
    damping_grid = [1.0] if args.disable_foam_tissue else inner_damping_grid
    shear_grid = [1.0] if args.disable_foam_tissue else outer_shear_grid
    band_damping_values = [0.0] if args.disable_foam_tissue else band_damping_grid
    for tension_k in tension_grid:
      for pressure_k in pressure_grid:
       for radial_bands in radial_bands_values:
        for local_pressure_k in local_grid:
         for shell_curvature_k in curvature_grid:
          for band_interface_k in interface_grid:
           for band_restoring_k in band_restoring_values:
            for shell_reference_k in shell_reference_values:
             for bulk_reference_k in bulk_reference_values:
              for outer_stiffness_scale in stiffness_grid:
               for inner_damping_scale in damping_grid:
                for outer_shear_scale in shear_grid:
                 for band_damping_c in band_damping_values:
                  for gravity_ramp_fraction in gravity_ramp_grid:
                   for settle_damping_boost in settle_damping_grid:
                    for settle_pressure_boost in settle_pressure_grid:
                     for settle_shell_boost in settle_shell_grid:
                      scores=[]; per_count=[]
                      for n in counts:
                        cfg = GravityConfig(num_cells=n, cell_radius=args.cell_radius, packing_fraction=args.packing_fraction, radius_safety_factor=args.radius_safety_factor, t_end=args.t_end, dt=args.dt, tissue_tension_k=tension_k, tissue_pressure_k=pressure_k, enable_foam_tissue=not args.disable_foam_tissue, tissue_radial_bands=radial_bands, tissue_local_pressure_k=local_pressure_k, tissue_shell_curvature_k=shell_curvature_k, tissue_band_interface_k=band_interface_k, tissue_band_restoring_k=band_restoring_k, tissue_shell_reference_k=shell_reference_k, tissue_bulk_reference_k=bulk_reference_k, tissue_outer_stiffness_scale=outer_stiffness_scale, tissue_inner_damping_scale=inner_damping_scale, tissue_outer_shear_scale=outer_shear_scale, tissue_band_damping_c=band_damping_c, gravity_ramp_fraction=gravity_ramp_fraction, settle_damping_boost=settle_damping_boost, settle_pressure_boost=settle_pressure_boost, settle_shell_boost=settle_shell_boost)
                        result = run_gravity(cfg, save_outputs=False)
                        final = result.summary["final_metrics"]
                        eq = result.summary["equilibrium_diagnostics"]
                        score = result.summary["near_sphere_score"]
                        scores.append(score)
                        per_count.append({"num_cells": n, "sag_ratio": final["sag_ratio"], "volume_ratio": final["volume_ratio"], "shape_deviation": final["shape_deviation"], "near_sphere_score": score, "tail_kinetic_mean": eq["tail_kinetic_mean"], "effective_radial_bands": result.summary["tissue_reference"]["effective_radial_bands"]})
                      mean_score = sum(scores) / len(scores)
                      row = {"tension_k": tension_k, "pressure_k": pressure_k, "radial_bands": radial_bands, "local_pressure_k": local_pressure_k, "shell_curvature_k": shell_curvature_k, "band_interface_k": band_interface_k, "band_restoring_k": band_restoring_k, "shell_reference_k": shell_reference_k, "bulk_reference_k": bulk_reference_k, "outer_stiffness_scale": outer_stiffness_scale, "inner_damping_scale": inner_damping_scale, "outer_shear_scale": outer_shear_scale, "band_damping_c": band_damping_c, "gravity_ramp_fraction": gravity_ramp_fraction, "settle_damping_boost": settle_damping_boost, "settle_pressure_boost": settle_pressure_boost, "settle_shell_boost": settle_shell_boost, "mean_score": mean_score, "max_score": max(scores), "counts": counts, "per_count": per_count}
                      rows.append(row)
                      if best_row is None or mean_score < best_row["mean_score"]: best_row = row
    rows_sorted = sorted(rows, key=lambda item: (item["mean_score"], item["max_score"]))
    with open(outdir / "calibration_results.json", "w", encoding="utf-8") as f: json.dump(rows_sorted, f, ensure_ascii=False, indent=2)
    fieldnames = ["tension_k", "pressure_k", "radial_bands", "local_pressure_k", "shell_curvature_k", "band_interface_k", "band_restoring_k", "shell_reference_k", "bulk_reference_k", "outer_stiffness_scale", "inner_damping_scale", "outer_shear_scale", "band_damping_c", "gravity_ramp_fraction", "settle_damping_boost", "settle_pressure_boost", "settle_shell_boost", "mean_score", "max_score"]
    with open(outdir / "calibration_results.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames); writer.writeheader(); writer.writerows({k: row[k] for k in fieldnames} for row in rows_sorted)
    with open(outdir / "best_config.json", "w", encoding="utf-8") as f: json.dump(best_row, f, ensure_ascii=False, indent=2)
    print(f"输出目录: {outdir}")

if __name__ == "__main__":
    main()
