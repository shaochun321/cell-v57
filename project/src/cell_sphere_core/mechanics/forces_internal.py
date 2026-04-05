from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState, NeighborGraph
from cell_sphere_core.aggregate.topology import (
    EDGE_SURFACE_RADIAL,
    EDGE_SURFACE_TANGENTIAL,
    EDGE_MIXED_SURFACE,
)


def spring_damper_forces(
    cells: CellState,
    graph: NeighborGraph,
    k_bulk: float,
    c_bulk: float,
    surface_radial_gain: float = 1.15,
    surface_tangential_gain: float = 1.8,
    mixed_surface_gain: float = 1.35,
    edge_stiffness_scale: np.ndarray | None = None,
    edge_damping_scale: np.ndarray | None = None,
) -> np.ndarray:
    x = cells.x
    v = cells.v
    f = np.zeros_like(x)

    edges = graph.edges
    if len(edges) == 0:
        return f

    if edge_stiffness_scale is None:
        edge_stiffness_scale = np.ones(len(edges), dtype=np.float64)
    if edge_damping_scale is None:
        edge_damping_scale = np.ones(len(edges), dtype=np.float64)

    i = edges[:, 0]
    j = edges[:, 1]
    dvec = x[j] - x[i]
    d = np.linalg.norm(dvec, axis=1)
    mask = d > 1e-12
    if not np.any(mask):
        return f

    i = i[mask]
    j = j[mask]
    dvec = dvec[mask]
    d = d[mask]
    ehat = dvec / d[:, None]
    rel_v = np.sum((v[j] - v[i]) * ehat, axis=1)

    gain = np.ones(len(d), dtype=np.float64)
    edge_type = graph.edge_type[mask]
    gain[edge_type == EDGE_SURFACE_RADIAL] = surface_radial_gain
    gain[edge_type == EDGE_SURFACE_TANGENTIAL] = surface_tangential_gain
    gain[edge_type == EDGE_MIXED_SURFACE] = mixed_surface_gain

    stiffness = k_bulk * gain * edge_stiffness_scale[mask]
    damping = c_bulk * gain * edge_damping_scale[mask]
    rest = graph.rest_length[mask]
    mag = stiffness * (d - rest) + damping * rel_v
    fij = mag[:, None] * ehat
    np.add.at(f, i, fij)
    np.add.at(f, j, -fij)
    return f
