from __future__ import annotations

import numpy as np


EPS = 1e-12


def _proxy_from_flat_neighbors(
    x: np.ndarray,
    flat_neighbor_index: np.ndarray,
    flat_neighbor_owner: np.ndarray,
    neighbor_counts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    local_volume = np.ones(n, dtype=np.float64)
    if len(flat_neighbor_index) == 0:
        return local_volume, 1.0 / local_volume

    dvec = x[flat_neighbor_index] - x[flat_neighbor_owner]
    dist3 = np.maximum(np.linalg.norm(dvec, axis=1), 1e-9) ** 3
    sum_dist3 = np.bincount(flat_neighbor_owner, weights=dist3, minlength=n)
    mask = neighbor_counts > 0
    local_volume[mask] = np.maximum(sum_dist3[mask] / neighbor_counts[mask], EPS)
    local_density = 1.0 / local_volume
    return local_volume, local_density


def compute_local_volume_density_proxies(
    x: np.ndarray,
    neighbor_list: list[list[int]],
    flat_neighbor_index: np.ndarray | None = None,
    flat_neighbor_owner: np.ndarray | None = None,
    neighbor_counts: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate per-cell local volume and density from neighbor spacing."""
    if (
        flat_neighbor_index is not None
        and flat_neighbor_owner is not None
        and neighbor_counts is not None
    ):
        return _proxy_from_flat_neighbors(x, flat_neighbor_index, flat_neighbor_owner, neighbor_counts)

    n = len(x)
    local_volume = np.ones(n, dtype=np.float64)
    local_density = np.ones(n, dtype=np.float64)

    for i, nbrs in enumerate(neighbor_list):
        if not nbrs:
            continue
        ids = np.asarray(nbrs, dtype=np.int64)
        distances = np.linalg.norm(x[ids] - x[i], axis=1)
        mean_cubed_distance = float(np.mean(np.maximum(distances, 1e-9) ** 3))
        local_volume[i] = max(mean_cubed_distance, EPS)
        local_density[i] = 1.0 / local_volume[i]

    return local_volume, local_density


def summarize_local_proxy_drift(
    rest_local_volume: np.ndarray,
    current_local_volume: np.ndarray,
    rest_local_density: np.ndarray,
    current_local_density: np.ndarray,
) -> dict:
    volume_ratio = current_local_volume / np.maximum(rest_local_volume, EPS)
    density_ratio = current_local_density / np.maximum(rest_local_density, EPS)
    return {
        "proxy_model": "volume_density_proxy",
        "mean_local_volume_ratio": float(np.mean(volume_ratio)),
        "std_local_volume_ratio": float(np.std(volume_ratio)),
        "min_local_volume_ratio": float(np.min(volume_ratio)),
        "max_local_volume_ratio": float(np.max(volume_ratio)),
        "mean_local_density_ratio": float(np.mean(density_ratio)),
        "std_local_density_ratio": float(np.std(density_ratio)),
        "min_local_density_ratio": float(np.min(density_ratio)),
        "max_local_density_ratio": float(np.max(density_ratio)),
    }
