from __future__ import annotations

import numpy as np


def build_neighbor_list(num_nodes: int, edges: np.ndarray) -> list[list[int]]:
    nbrs = [[] for _ in range(num_nodes)]
    for i, j in edges:
        nbrs[i].append(int(j))
        nbrs[j].append(int(i))
    return nbrs


def classify_surface_cells(
    x: np.ndarray,
    center: np.ndarray,
    target_radius: float,
    edges: np.ndarray,
    cell_radius: float,
    shell_thickness_factor: float = 2.0,
    exposure_threshold: float = 0.30,
    degree_factor: float = 0.80,
) -> tuple[np.ndarray, np.ndarray]:
    n = x.shape[0]
    nbrs = build_neighbor_list(n, edges)

    rho = np.linalg.norm(x - center[None, :], axis=1)
    shell_thickness = shell_thickness_factor * cell_radius

    degree = np.array([len(v) for v in nbrs], dtype=np.int64)
    median_degree = np.median(degree) if len(degree) > 0 else 0.0
    degree_threshold = degree_factor * median_degree

    is_surface = np.zeros(n, dtype=bool)
    exposure = np.zeros(n, dtype=np.float64)

    for i in range(n):
        if rho[i] <= target_radius - shell_thickness:
            continue

        if rho[i] < 1e-12:
            continue

        n_hat = (x[i] - center) / rho[i]
        max_dot = -1.0

        for j in nbrs[i]:
            dvec = x[j] - x[i]
            dnorm = np.linalg.norm(dvec)
            if dnorm < 1e-12:
                continue
            e_hat = dvec / dnorm
            max_dot = max(max_dot, float(np.dot(n_hat, e_hat)))

        exposure[i] = 1.0 - max_dot
        if exposure[i] > exposure_threshold or degree[i] < degree_threshold:
            is_surface[i] = True

    return is_surface, exposure
