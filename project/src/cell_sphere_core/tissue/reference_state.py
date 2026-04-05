from __future__ import annotations

import numpy as np

from cell_sphere_core.aggregate.surface import build_neighbor_list
from cell_sphere_core.core.datatypes import TissueReference
from cell_sphere_core.tissue.local_volume import compute_local_volume_density_proxies


def _flatten_neighbor_list(neighbor_list: list[list[int]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = np.array([len(v) for v in neighbor_list], dtype=np.int64)
    total = int(np.sum(counts))
    if total == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), counts

    flat_index = np.empty(total, dtype=np.int64)
    owner_index = np.empty(total, dtype=np.int64)
    cursor = 0
    for owner, nbrs in enumerate(neighbor_list):
        k = len(nbrs)
        if k == 0:
            continue
        flat_index[cursor:cursor + k] = np.asarray(nbrs, dtype=np.int64)
        owner_index[cursor:cursor + k] = owner
        cursor += k
    return flat_index, owner_index, counts


def _build_radial_bands(rest_radius: np.ndarray, num_radial_bands: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    if num_radial_bands <= 1:
        band_index = np.zeros(len(rest_radius), dtype=np.int64)
        bounds = np.array([float(np.min(rest_radius)), float(np.max(rest_radius))], dtype=np.float64)
        counts = np.array([len(rest_radius)], dtype=np.int64)
        return band_index, bounds, counts, 1

    r_max = float(np.max(rest_radius))
    if r_max <= 1e-12:
        band_index = np.zeros(len(rest_radius), dtype=np.int64)
        bounds = np.linspace(0.0, 1.0, 2, dtype=np.float64)
        counts = np.array([len(rest_radius)], dtype=np.int64)
        return band_index, bounds, counts, 1

    raw_bounds = np.linspace(0.0, r_max, num_radial_bands + 1, dtype=np.float64)
    band_index = np.digitize(rest_radius, raw_bounds[1:-1], right=False).astype(np.int64)
    counts = np.bincount(band_index, minlength=num_radial_bands).astype(np.int64)

    used = np.where(counts > 0)[0]
    if len(used) == 0:
        band_index = np.zeros(len(rest_radius), dtype=np.int64)
        bounds = np.array([0.0, r_max], dtype=np.float64)
        counts = np.array([len(rest_radius)], dtype=np.int64)
        return band_index, bounds, counts, 1

    if len(used) == num_radial_bands:
        return band_index, raw_bounds, counts, num_radial_bands

    mapping = {int(old): new for new, old in enumerate(used.tolist())}
    remapped = np.array([mapping[int(b)] for b in band_index], dtype=np.int64)
    new_bounds = [float(raw_bounds[used[0]])]
    for old in used:
        new_bounds.append(float(raw_bounds[int(old) + 1]))
    new_bounds_arr = np.array(new_bounds, dtype=np.float64)
    new_counts = np.bincount(remapped, minlength=len(used)).astype(np.int64)
    return remapped, new_bounds_arr, new_counts, len(used)


def build_tissue_reference(
    x: np.ndarray,
    edges: np.ndarray,
    is_surface: np.ndarray,
    center: np.ndarray,
    num_radial_bands: int = 4,
) -> TissueReference:
    n = x.shape[0]
    nbrs = build_neighbor_list(n, edges)
    surface_nbrs: list[list[int]] = []

    rest_radius = np.linalg.norm(x - center[None, :], axis=1)
    rest_mean_edge_length = np.zeros(n, dtype=np.float64)

    for i in range(n):
        ids = nbrs[i]
        if ids:
            rest_mean_edge_length[i] = float(np.mean(np.linalg.norm(x[ids] - x[i], axis=1)))
        else:
            rest_mean_edge_length[i] = 0.0

        if is_surface[i]:
            surface_nbrs.append([j for j in ids if is_surface[j]])
        else:
            surface_nbrs.append([])

    neighbor_flat_index, neighbor_owner_index, neighbor_counts = _flatten_neighbor_list(nbrs)
    surface_neighbor_flat_index, surface_neighbor_owner_index, surface_neighbor_counts = _flatten_neighbor_list(surface_nbrs)

    rest_local_volume_proxy, rest_local_density_proxy = compute_local_volume_density_proxies(
        x,
        nbrs,
        flat_neighbor_index=neighbor_flat_index,
        flat_neighbor_owner=neighbor_owner_index,
        neighbor_counts=neighbor_counts,
    )

    shell_mask = is_surface
    bulk_mask = ~is_surface

    shell_mean = float(np.mean(rest_radius[shell_mask])) if np.any(shell_mask) else float(np.mean(rest_radius))
    bulk_mean = float(np.mean(rest_radius[bulk_mask])) if np.any(bulk_mask) else float(np.mean(rest_radius))

    rest_shell_offset = np.zeros(n, dtype=np.float64)
    rest_bulk_offset = np.zeros(n, dtype=np.float64)
    rest_shell_offset[shell_mask] = rest_radius[shell_mask] - shell_mean
    rest_bulk_offset[bulk_mask] = rest_radius[bulk_mask] - bulk_mean

    radial_band_index, radial_band_bounds, radial_band_counts, effective_bands = _build_radial_bands(
        rest_radius, num_radial_bands=num_radial_bands
    )
    radial_band_mean_rest_radius = np.zeros(effective_bands, dtype=np.float64)
    radial_band_rest_offset = np.zeros(n, dtype=np.float64)
    for b in range(effective_bands):
        mask = radial_band_index == b
        mean_b = float(np.mean(rest_radius[mask]))
        radial_band_mean_rest_radius[b] = mean_b
        radial_band_rest_offset[mask] = rest_radius[mask] - mean_b

    return TissueReference(
        rest_radius=rest_radius,
        rest_mean_edge_length=rest_mean_edge_length,
        rest_local_volume_proxy=rest_local_volume_proxy,
        rest_local_density_proxy=rest_local_density_proxy,
        rest_shell_offset=rest_shell_offset,
        rest_bulk_offset=rest_bulk_offset,
        neighbor_list=nbrs,
        surface_neighbor_list=surface_nbrs,
        neighbor_flat_index=neighbor_flat_index,
        neighbor_owner_index=neighbor_owner_index,
        neighbor_counts=neighbor_counts,
        surface_neighbor_flat_index=surface_neighbor_flat_index,
        surface_neighbor_owner_index=surface_neighbor_owner_index,
        surface_neighbor_counts=surface_neighbor_counts,
        radial_band_index=radial_band_index,
        radial_band_mean_rest_radius=radial_band_mean_rest_radius,
        radial_band_rest_offset=radial_band_rest_offset,
        radial_band_bounds=radial_band_bounds,
        radial_band_counts=radial_band_counts,
        num_radial_bands=effective_bands,
    )
