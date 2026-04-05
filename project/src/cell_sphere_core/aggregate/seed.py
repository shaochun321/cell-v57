from __future__ import annotations

import math
import numpy as np


def generate_sphere_points(
    num_cells: int,
    sphere_radius: float,
    cell_radius: float,
    jitter: float = 0.15,
    rng_seed: int = 7,
) -> np.ndarray:
    rng = np.random.default_rng(rng_seed)

    sphere_volume = 4.0 / 3.0 * math.pi * sphere_radius**3
    nominal_cell_volume = sphere_volume / num_cells
    spacing = nominal_cell_volume ** (1.0 / 3.0)
    spacing *= 0.92

    grid_min = -sphere_radius
    grid_max = sphere_radius

    xs = np.arange(grid_min, grid_max + spacing, spacing)
    ys = np.arange(grid_min, grid_max + spacing, spacing)
    zs = np.arange(grid_min, grid_max + spacing, spacing)

    pts = []
    for x in xs:
        for y in ys:
            for z in zs:
                p = np.array([x, y, z], dtype=np.float64)
                p += rng.normal(scale=jitter * spacing, size=3)
                if np.linalg.norm(p) <= sphere_radius - 0.25 * cell_radius:
                    pts.append(p)

    pts = np.asarray(pts, dtype=np.float64)

    if len(pts) < num_cells:
        extra = []
        while len(pts) + len(extra) < num_cells:
            p = rng.uniform(-sphere_radius, sphere_radius, size=3)
            if np.linalg.norm(p) <= sphere_radius - 0.25 * cell_radius:
                extra.append(p)
        pts = np.vstack([pts, np.asarray(extra, dtype=np.float64)])

    if len(pts) > num_cells:
        idx = rng.choice(len(pts), size=num_cells, replace=False)
        pts = pts[idx]

    pts = pts - pts.mean(axis=0, keepdims=True)
    return pts
