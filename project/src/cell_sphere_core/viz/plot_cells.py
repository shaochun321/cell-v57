from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def plot_aggregate(
    x: np.ndarray,
    is_surface: np.ndarray,
    out_path: str | Path,
    title: str = "Cell sphere aggregate",
) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(10, 9))
    ax = fig.add_subplot(111, projection="3d")

    inner = ~is_surface
    ax.scatter(
        x[inner, 0], x[inner, 1], x[inner, 2],
        s=6, alpha=0.25
    )
    ax.scatter(
        x[is_surface, 0], x[is_surface, 1], x[is_surface, 2],
        s=16, alpha=0.85
    )

    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")

    max_range = np.max(np.abs(x)) * 1.15
    if max_range < 1e-6:
        max_range = 1.0
    for setter in (ax.set_xlim, ax.set_ylim, ax.set_zlim):
        setter(-max_range, max_range)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
