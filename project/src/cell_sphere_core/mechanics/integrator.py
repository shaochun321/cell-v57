from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState


def semi_implicit_euler(cells: CellState, forces: np.ndarray, dt: float, global_damping: float = 0.0) -> None:
    acc = forces / cells.m[:, None]
    cells.v[:] = cells.v + dt * acc
    if global_damping > 0.0:
        cells.v[:] *= max(0.0, 1.0 - dt * global_damping)
    cells.x[:] = cells.x + dt * cells.v
