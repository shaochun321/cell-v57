from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def build_neighbor_graph(
    x: np.ndarray,
    cell_radius: float,
    neighbor_radius_factor: float = 2.2,
    k_min: int = 8,
    k_max: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    n = x.shape[0]
    tree = cKDTree(x)

    search_radius = neighbor_radius_factor * 2.0 * cell_radius
    neighbor_sets: list[set[int]] = [set() for _ in range(n)]

    for i in range(n):
        ids = tree.query_ball_point(x[i], r=search_radius)
        ids = [j for j in ids if j != i]
        if len(ids) > k_max:
            d = np.linalg.norm(x[ids] - x[i], axis=1)
            order = np.argsort(d)
            ids = [ids[k] for k in order[:k_max]]
        neighbor_sets[i].update(ids)

    for i in range(n):
        if len(neighbor_sets[i]) < k_min:
            _, idx = tree.query(x[i], k=min(k_max + 1, n))
            idx = np.atleast_1d(idx)
            idx = [j for j in idx if j != i]
            for j in idx:
                neighbor_sets[i].add(int(j))
                if len(neighbor_sets[i]) >= k_min:
                    break

    for i in range(n):
        for j in list(neighbor_sets[i]):
            neighbor_sets[j].add(i)

    for i in range(n):
        if len(neighbor_sets[i]) > k_max:
            ids = list(neighbor_sets[i])
            d = np.linalg.norm(x[ids] - x[i], axis=1)
            order = np.argsort(d)
            keep = [ids[k] for k in order[:k_max]]
            neighbor_sets[i] = set(keep)

    for i in range(n):
        for j in list(neighbor_sets[i]):
            neighbor_sets[j].add(i)

    edges = set()
    degree = np.zeros(n, dtype=np.int64)

    for i in range(n):
        ids = sorted(neighbor_sets[i])
        degree[i] = len(ids)
        for j in ids:
            a, b = (i, j) if i < j else (j, i)
            if a != b:
                edges.add((a, b))

    edges_arr = np.array(sorted(edges), dtype=np.int64)
    return edges_arr, degree
