from __future__ import annotations

import numpy as np

from cell_sphere_core.core.datatypes import CellState, NeighborGraph, TissueReference
from cell_sphere_core.tissue.local_volume import compute_local_volume_density_proxies


def _safe_normalize_rows(v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    norms = np.linalg.norm(v, axis=1)
    mask = norms > 1e-12
    out = np.zeros_like(v)
    out[mask] = v[mask] / norms[mask, None]
    return out, mask


def _compute_current_band_means(rho: np.ndarray, band_index: np.ndarray, num_bands: int) -> np.ndarray:
    sums = np.bincount(band_index, weights=rho, minlength=num_bands).astype(np.float64)
    counts = np.bincount(band_index, minlength=num_bands).astype(np.float64)
    means = np.zeros(num_bands, dtype=np.float64)
    mask = counts > 0
    means[mask] = sums[mask] / counts[mask]
    return means


def _band_pair_scale(values: np.ndarray, b0: int, b1: int) -> float:
    return 0.5 * (float(values[b0]) + float(values[b1]))


def _mean_neighbor_positions(
    x: np.ndarray,
    flat_neighbor_index: np.ndarray,
    flat_neighbor_owner: np.ndarray,
    neighbor_counts: np.ndarray,
) -> np.ndarray:
    n = len(x)
    out = np.zeros_like(x)
    if len(flat_neighbor_index) == 0:
        return out
    denom = np.maximum(neighbor_counts, 1)
    for dim in range(x.shape[1]):
        sums = np.bincount(
            flat_neighbor_owner,
            weights=x[flat_neighbor_index, dim],
            minlength=n,
        ).astype(np.float64)
        out[:, dim] = np.divide(
            sums,
            denom,
            out=np.zeros(n, dtype=np.float64),
            where=neighbor_counts > 0,
        )
    return out



def foam_network_forces(
    cells: CellState,
    graph: NeighborGraph,
    tissue_reference: TissueReference,
    local_pressure_k: float = 90.0,
    shell_curvature_k: float = 55.0,
    shell_radial_k: float = 65.0,
    bulk_radial_k: float = 14.0,
    band_interface_k: float = 24.0,
    band_restoring_k: float = 30.0,
    shell_reference_k: float = 56.0,
    bulk_reference_k: float = 8.0,
    stiffness_scale_by_cell: np.ndarray | None = None,
    stiffness_scale_by_band: np.ndarray | None = None,
    shear_scale_by_cell: np.ndarray | None = None,
    local_pressure_clip: float = 0.22,
    radial_rate_damping_c: float = 0.0,
    shell_tangential_damping_c: float = 0.0,
    shell_neighbor_support_k: float = 0.0,
    preserve_com: bool = True,
) -> np.ndarray:
    x = cells.x
    n = len(x)
    f = np.zeros_like(x)
    com = np.mean(x, axis=0)
    com_vec = x - com[None, :]
    rho = np.linalg.norm(com_vec, axis=1)
    normal_all, normal_mask = _safe_normalize_rows(com_vec)

    shell_mask = cells.is_surface
    band_index = tissue_reference.radial_band_index
    num_bands = tissue_reference.num_radial_bands

    if stiffness_scale_by_cell is None:
        stiffness_scale_by_cell = np.ones(n, dtype=np.float64)
    if shear_scale_by_cell is None:
        shear_scale_by_cell = np.ones(n, dtype=np.float64)
    if stiffness_scale_by_band is None:
        stiffness_scale_by_band = np.ones(num_bands, dtype=np.float64)

    band_means_current = _compute_current_band_means(rho, band_index, num_bands)
    band_means_rest = tissue_reference.radial_band_mean_rest_radius

    rest_outer = float(np.max(band_means_rest)) if len(band_means_rest) else 1.0
    if rest_outer <= 1e-12:
        rest_outer = 1.0

    current_local_volume_proxy, current_local_density_proxy = compute_local_volume_density_proxies(
        x,
        tissue_reference.neighbor_list,
        flat_neighbor_index=tissue_reference.neighbor_flat_index,
        flat_neighbor_owner=tissue_reference.neighbor_owner_index,
        neighbor_counts=tissue_reference.neighbor_counts,
    )

    local_centroid = _mean_neighbor_positions(
        x,
        tissue_reference.neighbor_flat_index,
        tissue_reference.neighbor_owner_index,
        tissue_reference.neighbor_counts,
    )
    axis = x - local_centroid
    axis_hat, axis_mask = _safe_normalize_rows(axis)
    local_mask = axis_mask & (tissue_reference.neighbor_counts > 0)

    rest_volume = np.maximum(tissue_reference.rest_local_volume_proxy, 1e-12)
    rest_density = np.maximum(tissue_reference.rest_local_density_proxy, 1e-12)
    current_volume = np.maximum(current_local_volume_proxy, 1e-12)
    current_density = np.maximum(current_local_density_proxy, 1e-12)

    volume_term = -np.log(current_volume / rest_volume)
    density_term = np.log(current_density / rest_density)
    local_proxy_delta = np.clip(0.5 * (volume_term + density_term), -local_pressure_clip, local_pressure_clip)
    f[local_mask] += (
        local_pressure_k
        * stiffness_scale_by_cell[local_mask]
        * local_proxy_delta[local_mask]
    )[:, None] * axis_hat[local_mask]

    surf_mask = shell_mask & (tissue_reference.surface_neighbor_counts >= 2) & normal_mask
    if np.any(surf_mask):
        shell_centroid = _mean_neighbor_positions(
            x,
            tissue_reference.surface_neighbor_flat_index,
            tissue_reference.surface_neighbor_owner_index,
            tissue_reference.surface_neighbor_counts,
        )
        lap = shell_centroid - x
        radial_lap = np.sum(lap * normal_all, axis=1)
        f[surf_mask] += (
            shell_curvature_k
            * shear_scale_by_cell[surf_mask]
            * radial_lap[surf_mask]
        )[:, None] * normal_all[surf_mask]
        if shell_neighbor_support_k > 0.0:
            shell_rho = np.linalg.norm(shell_centroid - com[None, :], axis=1)
            shell_err = shell_rho - rho
            f[surf_mask] += (
                float(shell_neighbor_support_k)
                * stiffness_scale_by_cell[surf_mask]
                * shell_err[surf_mask]
            )[:, None] * normal_all[surf_mask]

    valid_normal = normal_mask
    target_rho = band_means_current[band_index] + tissue_reference.radial_band_rest_offset
    delta = rho - target_rho
    rest_scale = band_means_rest[band_index] / rest_outer
    band_k = bulk_radial_k + (shell_radial_k - bulk_radial_k) * (rest_scale ** 1.5)
    band_k *= stiffness_scale_by_cell
    f[valid_normal] += (-band_k[valid_normal] * delta[valid_normal])[:, None] * normal_all[valid_normal]

    band_shift = band_means_current - band_means_rest
    band_restore = band_restoring_k * stiffness_scale_by_cell * band_shift[band_index]
    f[valid_normal] += (-band_restore[valid_normal])[:, None] * normal_all[valid_normal]

    reference_delta = rho - tissue_reference.rest_radius
    reference_k = bulk_reference_k + (shell_reference_k - bulk_reference_k) * (rest_scale ** 1.8)
    reference_k *= stiffness_scale_by_cell
    f[valid_normal] += (-reference_k[valid_normal] * reference_delta[valid_normal])[:, None] * normal_all[valid_normal]

    if radial_rate_damping_c > 0.0 and np.any(valid_normal):
        radial_v = np.sum(cells.v * normal_all, axis=1)
        radial_drag = radial_rate_damping_c * stiffness_scale_by_cell * radial_v
        f[valid_normal] += (-radial_drag[valid_normal])[:, None] * normal_all[valid_normal]

    if shell_tangential_damping_c > 0.0 and np.any(surf_mask):
        radial_v = np.sum(cells.v * normal_all, axis=1)
        tangential_v = cells.v - radial_v[:, None] * normal_all
        shell_drag = shell_tangential_damping_c * shear_scale_by_cell[surf_mask]
        f[surf_mask] += -shell_drag[:, None] * tangential_v[surf_mask]

    if num_bands >= 2 and band_interface_k > 0.0:
        for b in range(num_bands - 1):
            current_gap = band_means_current[b + 1] - band_means_current[b]
            rest_gap = band_means_rest[b + 1] - band_means_rest[b]
            delta_gap = current_gap - rest_gap
            if abs(delta_gap) < 1e-12:
                continue
            inner_mask = (band_index == b) & valid_normal
            outer_mask = (band_index == (b + 1)) & valid_normal
            if not np.any(inner_mask) or not np.any(outer_mask):
                continue
            interface_scale = _band_pair_scale(stiffness_scale_by_band, b, b + 1)
            inner_weight = 1.0 / max(int(np.sum(inner_mask)), 1)
            outer_weight = 1.0 / max(int(np.sum(outer_mask)), 1)
            f[inner_mask] += (band_interface_k * interface_scale * delta_gap * inner_weight) * normal_all[inner_mask]
            f[outer_mask] += (-band_interface_k * interface_scale * delta_gap * outer_weight) * normal_all[outer_mask]

    if preserve_com:
        f -= np.mean(f, axis=0, keepdims=True)
    return f
