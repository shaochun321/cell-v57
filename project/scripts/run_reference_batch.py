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
import matplotlib.pyplot as plt

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

DEFAULT_COUNTS = [100, 300, 500, 800]

def parse_counts(raw: str) -> list[int]:
    values = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not values or any(v <= 0 for v in values):
        raise ValueError("counts must be a comma separated list of positive integers")
    return values

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--counts", type=str, default=",".join(str(x) for x in DEFAULT_COUNTS))
    p.add_argument("--cell-radius", type=float, default=0.004)
    p.add_argument("--packing-fraction", type=float, default=0.68)
    p.add_argument("--radius-safety-factor", type=float, default=1.02)
    p.add_argument("--t-end", type=float, default=1.0)
    p.add_argument("--dt", type=float, default=5e-4)
    p.add_argument("--disable-tissue", action="store_true")
    p.add_argument("--disable-foam-tissue", action="store_true")
    p.add_argument("--tissue-tension-k", type=float, default=18.0)
    p.add_argument("--tissue-pressure-k", type=float, default=900.0)
    p.add_argument("--tissue-radial-bands", type=int, default=4)
    p.add_argument("--tissue-local-pressure-k", type=float, default=90.0)
    p.add_argument("--tissue-shell-curvature-k", type=float, default=55.0)
    p.add_argument("--tissue-shell-radial-k", type=float, default=65.0)
    p.add_argument("--tissue-bulk-radial-k", type=float, default=14.0)
    p.add_argument("--tissue-band-interface-k", type=float, default=24.0)
    p.add_argument("--tissue-band-restoring-k", type=float, default=30.0)
    p.add_argument("--tissue-shell-reference-k", type=float, default=56.0)
    p.add_argument("--tissue-bulk-reference-k", type=float, default=8.0)
    p.add_argument("--tissue-inner-stiffness-scale", type=float, default=0.85)
    p.add_argument("--tissue-outer-stiffness-scale", type=float, default=1.35)
    p.add_argument("--tissue-inner-damping-scale", type=float, default=1.55)
    p.add_argument("--tissue-outer-damping-scale", type=float, default=0.90)
    p.add_argument("--tissue-inner-shear-scale", type=float, default=0.80)
    p.add_argument("--tissue-outer-shear-scale", type=float, default=1.45)
    p.add_argument("--tissue-band-damping-c", type=float, default=5.0)
    p.add_argument("--gravity-ramp-fraction", type=float, default=0.22)
    p.add_argument("--settle-damping-boost", type=float, default=3.0)
    p.add_argument("--settle-pressure-boost", type=float, default=1.40)
    p.add_argument("--settle-shell-boost", type=float, default=1.20)
    p.add_argument("--floor-tangential-c", type=float, default=6.0)
    p.add_argument("--floor-friction-mu", type=float, default=0.22)
    p.add_argument("--tissue-pressure-rate-damping-c", type=float, default=18.0)
    p.add_argument("--tissue-radial-rate-damping-c", type=float, default=3.0)
    p.add_argument("--tissue-shell-tangential-damping-c", type=float, default=2.0)
    p.add_argument("--disable-adaptive-settle", action="store_true")
    p.add_argument("--adaptive-settle-gain", type=float, default=0.12)
    p.add_argument("--adaptive-settle-max-boost", type=float, default=1.6)
    p.add_argument("--adaptive-settle-ke-ref", type=float, default=60.0)
    p.add_argument("--adaptive-settle-floor-ref", type=float, default=0.28)
    p.add_argument("--outdir", type=str, default="outputs/reference_batch")
    return p.parse_args()

def save_plots(rows: list[dict], outdir: Path) -> None:
    counts = [row["num_cells"] for row in rows]
    sag = [row["sag_ratio"] for row in rows]
    shape = [row["shape_deviation"] for row in rows]
    vol = [row["volume_ratio"] for row in rows]
    score = [row["near_sphere_score"] for row in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(counts, sag, marker="o", label="sag")
    ax.plot(counts, shape, marker="o", label="shape_dev")
    ax.plot(counts, [abs(1.0 - x) for x in vol], marker="o", label="|1-volume_ratio|")
    ax.plot(counts, score, marker="o", label="near_sphere_score")
    ax.set_xlabel("num_cells")
    ax.set_title("Reference batch diagnostics")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / "batch_metrics.png", dpi=180)
    plt.close(fig)

def main() -> None:
    args = parse_args()
    counts = parse_counts(args.counts)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for n in counts:
        cfg = GravityConfig(num_cells=n, cell_radius=args.cell_radius, packing_fraction=args.packing_fraction, radius_safety_factor=args.radius_safety_factor, t_end=args.t_end, dt=args.dt, enable_tissue=not args.disable_tissue, enable_foam_tissue=not args.disable_foam_tissue, tissue_tension_k=args.tissue_tension_k, tissue_pressure_k=args.tissue_pressure_k, tissue_radial_bands=args.tissue_radial_bands, tissue_local_pressure_k=args.tissue_local_pressure_k, tissue_shell_curvature_k=args.tissue_shell_curvature_k, tissue_shell_radial_k=args.tissue_shell_radial_k, tissue_bulk_radial_k=args.tissue_bulk_radial_k, tissue_band_interface_k=args.tissue_band_interface_k, tissue_band_restoring_k=args.tissue_band_restoring_k, tissue_shell_reference_k=args.tissue_shell_reference_k, tissue_bulk_reference_k=args.tissue_bulk_reference_k, tissue_inner_stiffness_scale=args.tissue_inner_stiffness_scale, tissue_outer_stiffness_scale=args.tissue_outer_stiffness_scale, tissue_inner_damping_scale=args.tissue_inner_damping_scale, tissue_outer_damping_scale=args.tissue_outer_damping_scale, tissue_inner_shear_scale=args.tissue_inner_shear_scale, tissue_outer_shear_scale=args.tissue_outer_shear_scale, tissue_band_damping_c=args.tissue_band_damping_c, gravity_ramp_fraction=args.gravity_ramp_fraction, settle_damping_boost=args.settle_damping_boost, settle_pressure_boost=args.settle_pressure_boost, settle_shell_boost=args.settle_shell_boost, floor_tangential_c=args.floor_tangential_c, floor_friction_mu=args.floor_friction_mu, tissue_pressure_rate_damping_c=args.tissue_pressure_rate_damping_c, tissue_radial_rate_damping_c=args.tissue_radial_rate_damping_c, tissue_shell_tangential_damping_c=args.tissue_shell_tangential_damping_c, adaptive_settle_enabled=not args.disable_adaptive_settle, adaptive_settle_gain=args.adaptive_settle_gain, adaptive_settle_max_boost=args.adaptive_settle_max_boost, adaptive_settle_ke_ref=args.adaptive_settle_ke_ref, adaptive_settle_floor_ref=args.adaptive_settle_floor_ref)
        result = run_gravity(cfg, outdir / f"gravity_N{n}")
        final = result.summary["final_metrics"]
        rows.append({"num_cells": n, "target_radius": result.summary["target_radius"], "target_volume": result.summary["target_volume"], "radial_bands": result.summary["tissue_reference"]["effective_radial_bands"], "band_restoring_k": args.tissue_band_restoring_k, "shell_reference_k": args.tissue_shell_reference_k, "bulk_reference_k": args.tissue_bulk_reference_k, "outer_stiffness_scale": args.tissue_outer_stiffness_scale, "inner_damping_scale": args.tissue_inner_damping_scale, "outer_shear_scale": args.tissue_outer_shear_scale, "band_damping_c": args.tissue_band_damping_c, "gravity_ramp_fraction": args.gravity_ramp_fraction, "settle_damping_boost": args.settle_damping_boost, "settle_pressure_boost": args.settle_pressure_boost, "settle_shell_boost": args.settle_shell_boost, "sag_ratio": final["sag_ratio"], "volume_ratio": final["volume_ratio"], "shape_deviation": final["shape_deviation"], "radius_cv": final["radius_cv"], "asphericity": final["asphericity"], "tail_kinetic_mean": result.summary["equilibrium_diagnostics"]["tail_kinetic_mean"], "tail_score_std": result.summary["equilibrium_diagnostics"]["tail_score_std"], "quasi_static": result.summary["equilibrium_diagnostics"]["is_quasi_static"], "near_sphere_score": result.summary["near_sphere_score"], "mean_local_volume_ratio": result.summary["local_proxy_diagnostics"]["mean_local_volume_ratio"], "mean_local_density_ratio": result.summary["local_proxy_diagnostics"]["mean_local_density_ratio"], "tissue_enabled": result.summary["tissue_enabled"], "foam_tissue_enabled": result.summary["foam_tissue_enabled"]})
        print(f"[done] N={n} score={result.summary['near_sphere_score']:.6f}")
    with open(outdir / "batch_summary.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(outdir / "batch_summary.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    save_plots(rows, outdir)
    print(f"输出目录: {outdir}")

if __name__ == "__main__":
    main()
