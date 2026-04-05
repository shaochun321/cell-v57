from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from cell_sphere_core.core.datatypes import CellState, NeighborGraph


def _pair_codes(pairs: np.ndarray, n: int) -> np.ndarray:
    a = np.minimum(pairs[:, 0], pairs[:, 1]).astype(np.int64, copy=False)
    b = np.maximum(pairs[:, 0], pairs[:, 1]).astype(np.int64, copy=False)
    return a * np.int64(n) + b


def contact_repulsion_forces(
    cells: CellState,
    graph: NeighborGraph,
    repulsion_k: float = 700.0,
    search_factor: float = 1.0,
) -> np.ndarray:
    x = cells.x
    r = cells.r
    n = x.shape[0]
    tree = cKDTree(x)
    search_r = float(search_factor * 2.0 * np.max(r))
    pairs = tree.query_pairs(search_r, output_type='ndarray')

    f = np.zeros_like(x)
    if pairs.size == 0:
        return f

    if graph.bonded_pair_codes is not None and len(graph.bonded_pair_codes) > 0:
        mask = ~np.isin(_pair_codes(pairs, n), graph.bonded_pair_codes, assume_unique=False)
        pairs = pairs[mask]
        if pairs.size == 0:
            return f

    i = pairs[:, 0]
    j = pairs[:, 1]
    dvec = x[j] - x[i]
    d = np.linalg.norm(dvec, axis=1)
    min_dist = r[i] + r[j]
    mask = (d > 1e-12) & (d < min_dist)
    if not np.any(mask):
        return f

    i = i[mask]
    j = j[mask]
    dvec = dvec[mask]
    d = d[mask]
    overlap = min_dist[mask] - d
    fij = (repulsion_k * overlap / d)[:, None] * dvec
    np.add.at(f, i, -fij)
    np.add.at(f, j, fij)
    return f
