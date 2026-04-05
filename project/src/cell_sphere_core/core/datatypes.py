from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


@dataclass
class BuildConfig:
    sphere_radius: float = 0.08
    cell_radius: float = 0.004
    jitter: float = 0.15
    rng_seed: int = 7

    neighbor_radius_factor: float = 2.2
    k_min: int = 8
    k_max: int = 16

    shell_thickness_factor: float = 2.0
    exposure_threshold: float = 0.30
    degree_factor: float = 0.80


@dataclass
class CellState:
    x: FloatArray
    v: FloatArray
    m: FloatArray
    r: FloatArray
    is_surface: BoolArray


@dataclass
class NeighborGraph:
    edges: IntArray
    rest_length: FloatArray
    edge_type: IntArray
    degree: IntArray
    bonded_pair_codes: IntArray | None = None


@dataclass
class TissueReference:
    rest_radius: FloatArray
    rest_mean_edge_length: FloatArray
    rest_local_volume_proxy: FloatArray
    rest_local_density_proxy: FloatArray
    rest_shell_offset: FloatArray
    rest_bulk_offset: FloatArray
    neighbor_list: list[list[int]]
    surface_neighbor_list: list[list[int]]
    neighbor_flat_index: IntArray
    neighbor_owner_index: IntArray
    neighbor_counts: IntArray
    surface_neighbor_flat_index: IntArray
    surface_neighbor_owner_index: IntArray
    surface_neighbor_counts: IntArray
    radial_band_index: IntArray
    radial_band_mean_rest_radius: FloatArray
    radial_band_rest_offset: FloatArray
    radial_band_bounds: FloatArray
    radial_band_counts: IntArray
    num_radial_bands: int


@dataclass
class SphereAggregate:
    center: FloatArray
    target_radius: float
    cells: CellState
    graph: NeighborGraph
    tissue_reference: TissueReference
