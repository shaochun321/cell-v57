from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState


def floor_forces(
    cells: CellState,
    floor_z: float = 0.0,
    k_floor: float = 4000.0,
    c_floor: float = 25.0,
    tangential_c: float = 0.0,
    friction_mu: float = 0.0,
) -> np.ndarray:
    """Penalty floor with optional tangential damping / capped friction.

    The normal term prevents penetration. The tangential term is intentionally
    dissipative and only acts on cells currently in floor contact, which helps
    static settling without globally freezing the aggregate.
    """
    f = np.zeros_like(cells.x)
    z = cells.x[:, 2]
    vz = cells.v[:, 2]
    penetration = floor_z - (z - cells.r)
    mask = penetration > 0.0
    if not np.any(mask):
        return f

    normal_force = k_floor * penetration[mask] - c_floor * np.minimum(vz[mask], 0.0)
    normal_force = np.maximum(normal_force, 0.0)
    f[mask, 2] += normal_force

    if tangential_c > 0.0:
        tangent_v = cells.v[mask, :2]
        tangent_force = -tangential_c * tangent_v
        if friction_mu > 0.0:
            tangent_norm = np.linalg.norm(tangent_force, axis=1)
            limit = friction_mu * normal_force
            scale = np.ones_like(tangent_norm)
            over = tangent_norm > np.maximum(limit, 1e-12)
            scale[over] = limit[over] / tangent_norm[over]
            tangent_force *= scale[:, None]
        f[mask, :2] += tangent_force
    return f
