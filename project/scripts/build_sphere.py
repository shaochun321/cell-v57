from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np

from cell_sphere_core.core.datatypes import BuildConfig, NeighborGraph, SphereAggregate
from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.aggregate.seed import generate_sphere_points
from cell_sphere_core.aggregate.neighbors import build_neighbor_graph
from cell_sphere_core.aggregate.surface import classify_surface_cells
from cell_sphere_core.aggregate.topology import classify_edges
from cell_sphere_core.viz.plot_cells import plot_aggregate
from cell_sphere_core.reference.sizing import estimate_reference_sphere
from cell_sphere_core.tissue.reference_state import build_tissue_reference


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-cells", type=int, default=None)
    parser.add_argument("--radius", type=float, default=None, help="固定球半径；不传则按 cell 数量自动估计")
    parser.add_argument("--cell-radius", type=float, default=0.004)
    parser.add_argument("--packing-fraction", type=float, default=0.68)
    parser.add_argument("--radius-safety-factor", type=float, default=1.02)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--outdir", type=str, default="outputs/build")
    return parser.parse_args()


def get_num_cells(arg_value: int | None) -> int:
    if arg_value is not None:
        if arg_value <= 0:
            raise ValueError("num-cells must be positive")
        return arg_value

    while True:
        raw = input("请输入细胞数量 num_cells: ").strip()
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("请输入一个正整数。")


def main() -> None:
    args = parse_args()
    num_cells = get_num_cells(args.num_cells)
    reference = estimate_reference_sphere(
        num_cells=num_cells,
        cell_radius=args.cell_radius,
        packing_fraction=args.packing_fraction,
        safety_factor=args.radius_safety_factor,
    )
    sphere_radius = args.radius if args.radius is not None else reference.target_radius

    cfg = BuildConfig(
        sphere_radius=sphere_radius,
        cell_radius=args.cell_radius,
        rng_seed=args.seed,
    )

    outdir = Path(args.outdir) / f"sphere_N{num_cells}"
    outdir.mkdir(parents=True, exist_ok=True)

    x = generate_sphere_points(
        num_cells=num_cells,
        sphere_radius=cfg.sphere_radius,
        cell_radius=cfg.cell_radius,
        jitter=cfg.jitter,
        rng_seed=cfg.rng_seed,
    )

    cells = make_cell_state(x=x, cell_radius=cfg.cell_radius)
    center = np.zeros(3, dtype=np.float64)

    edges, degree = build_neighbor_graph(
        x=cells.x,
        cell_radius=cfg.cell_radius,
        neighbor_radius_factor=cfg.neighbor_radius_factor,
        k_min=cfg.k_min,
        k_max=cfg.k_max,
    )

    is_surface, exposure = classify_surface_cells(
        x=cells.x,
        center=center,
        target_radius=cfg.sphere_radius,
        edges=edges,
        cell_radius=cfg.cell_radius,
        shell_thickness_factor=cfg.shell_thickness_factor,
        exposure_threshold=cfg.exposure_threshold,
        degree_factor=cfg.degree_factor,
    )
    cells.is_surface = is_surface

    edge_type = classify_edges(
        x=cells.x,
        center=center,
        edges=edges,
        is_surface=cells.is_surface,
    )

    rest_length = np.linalg.norm(cells.x[edges[:, 1]] - cells.x[edges[:, 0]], axis=1)

    graph = NeighborGraph(
        edges=edges,
        rest_length=rest_length,
        edge_type=edge_type,
        degree=degree,
    )

    tissue_reference = build_tissue_reference(cells.x, edges, cells.is_surface, center)

    aggregate = SphereAggregate(
        center=center,
        target_radius=cfg.sphere_radius,
        cells=cells,
        graph=graph,
        tissue_reference=tissue_reference,
    )

    plot_aggregate(
        x=aggregate.cells.x,
        is_surface=aggregate.cells.is_surface,
        out_path=outdir / "aggregate.png",
        title=f"Cell sphere aggregate (N={num_cells})",
    )

    counts = {
        "bulk": int(np.sum(edge_type == 0)),
        "surface_radial": int(np.sum(edge_type == 1)),
        "surface_tangential": int(np.sum(edge_type == 2)),
        "mixed_surface": int(np.sum(edge_type == 3)),
    }

    summary = {
        "num_cells": num_cells,
        "sphere_radius": cfg.sphere_radius,
        "cell_radius": cfg.cell_radius,
        "packing_fraction": args.packing_fraction,
        "reference_radius": reference.target_radius,
        "surface_cell_ratio": float(np.mean(cells.is_surface)),
        "num_edges": int(len(edges)),
        "degree_mean": float(np.mean(graph.degree)),
        "degree_median": float(np.median(graph.degree)),
        "edge_type_counts": counts,
        "exposure_mean": float(np.mean(exposure)),
        "exposure_surface_mean": float(np.mean(exposure[cells.is_surface])) if np.any(cells.is_surface) else 0.0,
    }

    with open(outdir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"输出目录: {outdir}")
    print(summary)


if __name__ == "__main__":
    main()
