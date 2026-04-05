from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull


def convex_hull_volume(x: np.ndarray) -> float:
    try:
        return float(ConvexHull(x).volume)
    except Exception:
        return float("nan")


def _asphericity(x_centered: np.ndarray) -> float:
    cov = np.cov(x_centered.T)
    eigvals = np.linalg.eigvalsh(cov)
    eigvals = np.maximum(eigvals, 1e-12)
    lam_sum = float(np.sum(eigvals))
    if lam_sum <= 0.0:
        return 0.0
    return float((np.max(eigvals) - np.min(eigvals)) / lam_sum)


def compute_metrics(
    x: np.ndarray,
    v: np.ndarray,
    m: np.ndarray,
    r: np.ndarray,
    sphere_radius: float,
    target_volume: float,
    floor_z: float = 0.0,
) -> dict:
    com = np.sum(x * m[:, None], axis=0) / np.sum(m)
    centered = x - com[None, :]
    radial = np.linalg.norm(centered, axis=1)
    ke = 0.5 * np.sum(m * np.sum(v * v, axis=1))
    hull_vol = convex_hull_volume(x)
    volume_ratio = hull_vol / target_volume if np.isfinite(hull_vol) and target_volume > 0 else float("nan")
    shape_dev = float(np.std(radial) / max(sphere_radius, 1e-12))
    mean_radius = float(np.mean(radial))
    radius_cv = float(np.std(radial) / max(mean_radius, 1e-12))
    sag_ratio = max(0.0, (sphere_radius - (com[2] - floor_z)) / max(sphere_radius, 1e-12))
    floor_contact_ratio = float(np.mean((x[:, 2] - r) <= floor_z))
    return {
        "sag_ratio": float(sag_ratio),
        "volume_ratio": float(volume_ratio),
        "shape_deviation": shape_dev,
        "kinetic_energy": float(ke),
        "com_z": float(com[2]),
        "mean_radius": mean_radius,
        "radius_cv": radius_cv,
        "asphericity": _asphericity(centered),
        "floor_contact_ratio": floor_contact_ratio,
        "target_radius": float(sphere_radius),
        "target_volume": float(target_volume),
        "hull_volume": float(hull_vol),
    }
