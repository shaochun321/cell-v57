from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull
from cell_sphere_core.core.datatypes import CellState


def convex_hull_volume(x: np.ndarray) -> float:
    try:
        return float(ConvexHull(x).volume)
    except Exception:
        return float('nan')


def volume_pressure_forces(
    cells: CellState,
    target_volume: float,
    pressure_k: float = 1200.0,
    surface_only: bool = True,
    max_delta_ratio: float = 0.25,
    prev_volume: float | None = None,
    dt: float | None = None,
    pressure_rate_damping_c: float = 0.0,
) -> tuple[np.ndarray, float, float, float]:
    """Hydrostatic-like pressure with optional volumetric rate damping.

    The rate damping term resists rapid volume change, which helps large-N runs
    approach static equilibrium instead of overshooting through repeated global
    compression / re-expansion cycles.
    """
    x = cells.x
    current_volume = convex_hull_volume(x)
    f = np.zeros_like(x)
    if not np.isfinite(current_volume) or target_volume <= 0:
        return f, current_volume, 0.0, 0.0

    delta_ratio = (target_volume - current_volume) / target_volume
    delta_ratio = float(np.clip(delta_ratio, -max_delta_ratio, max_delta_ratio))

    volume_rate_ratio = 0.0
    if prev_volume is not None and dt is not None and dt > 0.0 and np.isfinite(prev_volume):
        volume_rate_ratio = float((current_volume - prev_volume) / (target_volume * dt))
        volume_rate_ratio = float(np.clip(volume_rate_ratio, -0.5, 0.5))

    if abs(delta_ratio) < 1e-12 and abs(volume_rate_ratio) < 1e-12:
        return f, current_volume, delta_ratio, volume_rate_ratio

    com = np.mean(x, axis=0)
    mask = cells.is_surface if surface_only and np.any(cells.is_surface) else np.ones(len(x), dtype=bool)
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return f, current_volume, delta_ratio, volume_rate_ratio

    dirs = x[idx] - com[None, :]
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    dirs = dirs / np.maximum(norms, 1e-12)

    total_mass = float(np.sum(cells.m))
    mass_share = total_mass / max(1, len(idx))
    mag = mass_share * (pressure_k * delta_ratio - pressure_rate_damping_c * volume_rate_ratio)
    f[idx] += mag * dirs
    return f, current_volume, delta_ratio, volume_rate_ratio
