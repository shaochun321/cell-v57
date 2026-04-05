from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState, NeighborGraph
from cell_sphere_core.aggregate.topology import EDGE_SURFACE_TANGENTIAL, EDGE_MIXED_SURFACE


def surface_tension_forces(
    cells: CellState,
    graph: NeighborGraph,
    tension_k: float = 15.0,
    target_shrink: float = 0.97,
    mixed_gain: float = 0.5,
) -> np.ndarray:
    """
    A simple cortical-tension model:
    surface tangential edges prefer to be slightly shorter than their initial rest length,
    which creates a contractile shell-like tendency without introducing a rigid shell.
    """
    x = cells.x
    f = np.zeros_like(x)

    edge_type = graph.edge_type
    mask = (edge_type == EDGE_SURFACE_TANGENTIAL) | (edge_type == EDGE_MIXED_SURFACE)
    if not np.any(mask):
        return f

    edges = graph.edges[mask]
    i = edges[:, 0]
    j = edges[:, 1]
    dvec = x[j] - x[i]
    d = np.linalg.norm(dvec, axis=1)
    good = d > 1e-12
    if not np.any(good):
        return f

    i = i[good]
    j = j[good]
    d = d[good]
    dvec = dvec[good]
    et = edge_type[mask][good]

    gain = np.where(et == EDGE_SURFACE_TANGENTIAL, 1.0, mixed_gain)
    target = graph.rest_length[mask][good] * target_shrink
    mag = tension_k * gain * (d - target)
    fij = mag[:, None] * (dvec / d[:, None])
    np.add.at(f, i, fij)
    np.add.at(f, j, -fij)
    return f
