from __future__ import annotations

import numpy as np

from cell_sphere_core.core.datatypes import CellState, TissueReference


def band_viscous_damping_forces(
    cells: CellState,
    tissue_reference: TissueReference,
    damping_scale_by_cell: np.ndarray,
    base_damping_c: float = 5.0,
    radial_damping_c: float | None = None,
    tangential_damping_c: float | None = None,
) -> np.ndarray:
    """Apply internal viscous damping within each radial band.

    By default this behaves like the older isotropic band damping. If radial and
    tangential coefficients are both provided, the damping is split relative to
    the instantaneous radial direction from the aggregate COM so we can damp
    radial sloshing more strongly while preserving tangential / swirl motion.
    """
    if base_damping_c <= 0.0 and (radial_damping_c is None or radial_damping_c <= 0.0) and (tangential_damping_c is None or tangential_damping_c <= 0.0):
        return np.zeros_like(cells.x)

    v = cells.v
    band_index = tissue_reference.radial_band_index
    num_bands = tissue_reference.num_radial_bands
    f = np.zeros_like(v)

    use_split = radial_damping_c is not None or tangential_damping_c is not None
    com = np.mean(cells.x, axis=0)
    rel = cells.x - com[None, :]
    rho = np.linalg.norm(rel, axis=1, keepdims=True)
    normal = np.divide(rel, np.maximum(rho, 1e-12), out=np.zeros_like(rel), where=rho > 1e-12)

    for b in range(num_bands):
        mask = band_index == b
        if not np.any(mask):
            continue
        band_mean_v = np.mean(v[mask], axis=0, keepdims=True)
        rel_v = v[mask] - band_mean_v
        coeff = damping_scale_by_cell[mask][:, None]
        if use_split:
            c_r = float(base_damping_c if radial_damping_c is None else radial_damping_c)
            c_t = float(base_damping_c if tangential_damping_c is None else tangential_damping_c)
            n = normal[mask]
            radial_v = np.sum(rel_v * n, axis=1, keepdims=True) * n
            tangential_v = rel_v - radial_v
            f[mask] = -(c_r * coeff) * radial_v - (c_t * coeff) * tangential_v
        else:
            f[mask] = -(float(base_damping_c) * coeff) * rel_v

    return f
