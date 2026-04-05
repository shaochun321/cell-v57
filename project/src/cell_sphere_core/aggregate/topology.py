from __future__ import annotations

import numpy as np

EDGE_BULK = 0
EDGE_SURFACE_RADIAL = 1
EDGE_SURFACE_TANGENTIAL = 2
EDGE_MIXED_SURFACE = 3


def classify_edges(
    x: np.ndarray,
    center: np.ndarray,
    edges: np.ndarray,
    is_surface: np.ndarray,
    radial_threshold: float = 0.70,
    tangential_threshold: float = 0.35,
) -> np.ndarray:
    edge_type = np.zeros(len(edges), dtype=np.int64)

    for k, (i, j) in enumerate(edges):
        si = bool(is_surface[i])
        sj = bool(is_surface[j])

        if not si and not sj:
            edge_type[k] = EDGE_BULK
            continue

        dvec = x[j] - x[i]
        dnorm = np.linalg.norm(dvec)
        if dnorm < 1e-12:
            edge_type[k] = EDGE_BULK
            continue
        e_hat = dvec / dnorm

        if si and sj:
            ri = x[i] - center
            rj = x[j] - center
            ni = ri / (np.linalg.norm(ri) + 1e-12)
            nj = rj / (np.linalg.norm(rj) + 1e-12)
            a = 0.5 * (abs(np.dot(e_hat, ni)) + abs(np.dot(e_hat, nj)))

            if a > radial_threshold:
                edge_type[k] = EDGE_SURFACE_RADIAL
            elif a < tangential_threshold:
                edge_type[k] = EDGE_SURFACE_TANGENTIAL
            else:
                edge_type[k] = EDGE_MIXED_SURFACE
        else:
            edge_type[k] = EDGE_SURFACE_RADIAL

    return edge_type
