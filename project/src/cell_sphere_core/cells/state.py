from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState


def make_cell_state(
    x: np.ndarray,
    cell_radius: float,
    cell_mass: float = 1.0,
) -> CellState:
    n = x.shape[0]
    v = np.zeros((n, 3), dtype=np.float64)
    m = np.full(n, cell_mass, dtype=np.float64)
    r = np.full(n, cell_radius, dtype=np.float64)
    is_surface = np.zeros(n, dtype=bool)
    return CellState(x=x, v=v, m=m, r=r, is_surface=is_surface)
