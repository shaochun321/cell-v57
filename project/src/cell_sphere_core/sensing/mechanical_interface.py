from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np

from cell_sphere_core.core.datatypes import CellState, TissueReference
from cell_sphere_core.tissue.local_volume import compute_local_volume_density_proxies


@dataclass(frozen=True)
class MechanicalSensorSnapshot:
    global_accel_norm: float
    global_contact_ratio: float
    band_compression: np.ndarray
    band_sag: np.ndarray
    band_radial_speed: np.ndarray
    band_tangential_speed: np.ndarray
    band_force_density: np.ndarray
    band_contact_ratio: np.ndarray

    def to_dict(self) -> dict:
        return {
            "global_accel_norm": float(self.global_accel_norm),
            "global_contact_ratio": float(self.global_contact_ratio),
            "band_compression": self.band_compression.tolist(),
            "band_sag": self.band_sag.tolist(),
            "band_radial_speed": self.band_radial_speed.tolist(),
            "band_tangential_speed": self.band_tangential_speed.tolist(),
            "band_force_density": self.band_force_density.tolist(),
            "band_contact_ratio": self.band_contact_ratio.tolist(),
        }


@dataclass(frozen=True)
class NodeReferenceFrame:
    origin_type: str
    origin: np.ndarray
    axes: str = "global_fixed"

    def to_dict(self) -> dict:
        return {
            "origin_type": self.origin_type,
            "origin": [float(v) for v in self.origin.tolist()],
            "axes": self.axes,
        }


def _band_mean(values: np.ndarray, band_index: np.ndarray, num_bands: int) -> np.ndarray:
    sums = np.bincount(band_index, weights=values, minlength=num_bands).astype(np.float64)
    counts = np.bincount(band_index, minlength=num_bands).astype(np.float64)
    out = np.zeros(num_bands, dtype=np.float64)
    mask = counts > 0
    out[mask] = sums[mask] / counts[mask]
    return out


def _band_origin(cells: CellState, tissue_reference: TissueReference) -> np.ndarray:
    anchor_mask = tissue_reference.radial_band_index == 0
    if np.any(anchor_mask):
        return np.mean(cells.x[anchor_mask], axis=0)
    return np.mean(cells.x, axis=0)


def sample_mechanical_sensors(
    cells: CellState,
    tissue_reference: TissueReference,
    total_forces: np.ndarray,
    *,
    floor_z: float = 0.0,
) -> MechanicalSensorSnapshot:
    num_bands = int(tissue_reference.num_radial_bands)
    band_index = tissue_reference.radial_band_index.astype(np.int64)

    current_local_volume, _ = compute_local_volume_density_proxies(
        cells.x,
        tissue_reference.neighbor_list,
        flat_neighbor_index=tissue_reference.neighbor_flat_index,
        flat_neighbor_owner=tissue_reference.neighbor_owner_index,
        neighbor_counts=tissue_reference.neighbor_counts,
    )
    volume_ratio = current_local_volume / np.maximum(tissue_reference.rest_local_volume_proxy, 1e-12)

    ref_origin = _band_origin(cells, tissue_reference)
    centered = cells.x - ref_origin[None, :]
    radius = np.linalg.norm(centered, axis=1)
    radial_dir = np.zeros_like(cells.x)
    nz = radius > 1e-12
    radial_dir[nz] = centered[nz] / radius[nz, None]
    radial_speed = np.sum(cells.v * radial_dir, axis=1)
    tangential_v = cells.v - radial_dir * np.sum(cells.v * radial_dir, axis=1, keepdims=True)
    tangential_speed = np.linalg.norm(tangential_v, axis=1)
    rest_radius = np.maximum(tissue_reference.rest_radius, 1e-12)
    radius_ratio = radius / rest_radius

    accel = total_forces / np.maximum(cells.m[:, None], 1e-12)
    force_density = np.linalg.norm(accel, axis=1)
    contact_mask = (cells.x[:, 2] - cells.r) <= (floor_z + 1e-9)

    band_compression = _band_mean(np.clip(1.0 - volume_ratio, 0.0, None), band_index, num_bands)
    band_sag = _band_mean(np.clip(1.0 - radius_ratio, 0.0, None), band_index, num_bands)
    band_radial_speed = _band_mean(np.abs(radial_speed), band_index, num_bands)
    band_tangential_speed = _band_mean(tangential_speed, band_index, num_bands)
    band_force_density = _band_mean(force_density, band_index, num_bands)
    band_contact_ratio = _band_mean(contact_mask.astype(np.float64), band_index, num_bands)

    total_mass = float(np.sum(cells.m))
    global_accel_norm = float(np.linalg.norm(np.sum(total_forces, axis=0) / max(total_mass, 1e-12)))
    global_contact_ratio = float(np.mean(contact_mask))
    return MechanicalSensorSnapshot(
        global_accel_norm=global_accel_norm,
        global_contact_ratio=global_contact_ratio,
        band_compression=band_compression,
        band_sag=band_sag,
        band_radial_speed=band_radial_speed,
        band_tangential_speed=band_tangential_speed,
        band_force_density=band_force_density,
        band_contact_ratio=band_contact_ratio,
    )


def extract_surface_node_data(
    cells: CellState,
    tissue_reference: TissueReference,
    band_idx: int,
    field_values: np.ndarray | None = None,
    field_name: str = "u_r",
) -> dict:
    band_mask = tissue_reference.radial_band_index == band_idx
    if not np.any(band_mask):
        return {"polar": [], "azimuthal": [], "field": []}

    origin = _band_origin(cells, tissue_reference)
    coords = cells.x[band_mask] - origin
    r = np.linalg.norm(coords, axis=1)
    r_safe = np.maximum(r, 1e-12)
    polar = np.arccos(np.clip(coords[:, 2] / r_safe, -1.0, 1.0))
    azimuthal = np.arctan2(coords[:, 1], coords[:, 0])

    if field_values is not None:
        field = field_values[band_mask]
    else:
        if field_name == "u_r":
            rest_radius = tissue_reference.rest_radius[band_mask]
            field = r - rest_radius
        elif field_name == "v_radial":
            v = cells.v[band_mask]
            radial_dir = coords / r_safe[:, None]
            field = np.sum(v * radial_dir, axis=1)
        else:
            raise ValueError(f"Unknown field_name: {field_name}")

    return {
        "polar": polar.tolist(),
        "azimuthal": azimuthal.tolist(),
        "field": field.tolist(),
    }


def extract_node_sensor_frame(
    cells: CellState,
    tissue_reference: TissueReference,
    total_forces: np.ndarray,
    *,
    gate_level_by_band: np.ndarray | None = None,
    gate_signal_by_band: np.ndarray | None = None,
    floor_z: float = 0.0,
) -> dict:
    band_index = tissue_reference.radial_band_index.astype(np.int64)
    origin = _band_origin(cells, tissue_reference)
    coords_rel = cells.x - origin[None, :]
    radius = np.linalg.norm(coords_rel, axis=1)
    r_safe = np.maximum(radius, 1e-12)
    radial_dir = np.zeros_like(coords_rel)
    nz = radius > 1e-12
    radial_dir[nz] = coords_rel[nz] / r_safe[nz, None]

    polar = np.arccos(np.clip(coords_rel[:, 2] / r_safe, -1.0, 1.0))
    azimuthal = np.arctan2(coords_rel[:, 1], coords_rel[:, 0])
    radial_disp = radius - tissue_reference.rest_radius
    radial_speed = np.sum(cells.v * radial_dir, axis=1)
    tangential_speed = np.linalg.norm(cells.v - radial_dir * radial_speed[:, None], axis=1)

    accel = total_forces / np.maximum(cells.m[:, None], 1e-12)
    accel_radial = np.sum(accel * radial_dir, axis=1)
    accel_tangential = np.linalg.norm(accel - radial_dir * accel_radial[:, None], axis=1)
    force_density = np.linalg.norm(accel, axis=1)
    contact_mask = ((cells.x[:, 2] - cells.r) <= (floor_z + 1e-9)).astype(float)

    if gate_level_by_band is None:
        gate_level_by_band = np.ones(tissue_reference.num_radial_bands, dtype=np.float64)
    if gate_signal_by_band is None:
        gate_signal_by_band = np.zeros(tissue_reference.num_radial_bands, dtype=np.float64)

    layers: list[dict] = []
    for band in range(int(tissue_reference.num_radial_bands)):
        mask = band_index == band
        idx = np.where(mask)[0]
        layer_nodes = []
        for i in idx.tolist():
            layer_nodes.append(
                {
                    "id": int(i),
                    "band_index": int(band),
                    "is_surface": bool(cells.is_surface[i]),
                    "pos_abs": [float(v) for v in cells.x[i].tolist()],
                    "pos_rel": [float(v) for v in coords_rel[i].tolist()],
                    "vel_abs": [float(v) for v in cells.v[i].tolist()],
                    "accel_abs": [float(v) for v in accel[i].tolist()],
                    "r": float(radius[i]),
                    "polar": float(polar[i]),
                    "azimuthal": float(azimuthal[i]),
                    "u_r": float(radial_disp[i]),
                    "v_r": float(radial_speed[i]),
                    "tangential_speed": float(tangential_speed[i]),
                    "accel_r": float(accel_radial[i]),
                    "accel_tangential": float(accel_tangential[i]),
                    "force_density": float(force_density[i]),
                    "gate": float(gate_level_by_band[band]),
                    "gate_signal": float(gate_signal_by_band[band]),
                    "contact": float(contact_mask[i]),
                }
            )
        layers.append(
            {
                "band_index": int(band),
                "rest_mean_radius": float(tissue_reference.radial_band_mean_rest_radius[band]),
                "node_count": int(len(layer_nodes)),
                "nodes": layer_nodes,
            }
        )

    outer_band = int(tissue_reference.num_radial_bands - 1)
    outer_mask = band_index == outer_band
    surface_nodes = {
        "band_index": outer_band,
        "polar": polar[outer_mask].tolist(),
        "azimuthal": azimuthal[outer_mask].tolist(),
        "field": radial_disp[outer_mask].tolist(),
        "field_name": "u_r",
    }
    return {
        "reference_frame": NodeReferenceFrame("inner_anchor_center", origin).to_dict(),
        "layers": layers,
        "surface_nodes": surface_nodes,
    }


def write_sensor_nodes_jsonl(path: str | Path, frames: list[dict]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for frame in frames:
            f.write(json.dumps(frame, ensure_ascii=False))
            f.write("\n")