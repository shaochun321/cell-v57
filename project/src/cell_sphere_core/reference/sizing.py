from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ReferenceSphere:
    num_cells: int
    cell_radius: float
    packing_fraction: float
    safety_factor: float
    target_radius: float
    target_volume: float
    single_cell_volume: float
    total_cell_volume: float


def _cell_volume(cell_radius: float) -> float:
    return (4.0 / 3.0) * math.pi * (cell_radius ** 3)


def estimate_reference_sphere(
    num_cells: int,
    cell_radius: float,
    packing_fraction: float = 0.68,
    safety_factor: float = 1.02,
) -> ReferenceSphere:
    if num_cells <= 0:
        raise ValueError("num_cells must be positive")
    if cell_radius <= 0:
        raise ValueError("cell_radius must be positive")
    if not (0.0 < packing_fraction < 1.0):
        raise ValueError("packing_fraction must be in (0, 1)")
    if safety_factor <= 0.0:
        raise ValueError("safety_factor must be positive")

    single_cell_volume = _cell_volume(cell_radius)
    total_cell_volume = num_cells * single_cell_volume
    target_volume = total_cell_volume / packing_fraction
    target_radius = ((3.0 * target_volume) / (4.0 * math.pi)) ** (1.0 / 3.0)
    target_radius *= safety_factor
    target_volume = (4.0 / 3.0) * math.pi * (target_radius ** 3)

    return ReferenceSphere(
        num_cells=num_cells,
        cell_radius=cell_radius,
        packing_fraction=packing_fraction,
        safety_factor=safety_factor,
        target_radius=target_radius,
        target_volume=target_volume,
        single_cell_volume=single_cell_volume,
        total_cell_volume=total_cell_volume,
    )
