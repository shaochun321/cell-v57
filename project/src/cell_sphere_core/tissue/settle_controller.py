from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from cell_sphere_core.core.datatypes import CellState


@dataclass(frozen=True)
class SettleControllerDiagnostics:
    active: bool
    intensity: float
    contact_ratio: float
    kinetic_per_cell: float
    target_kinetic_per_cell: float


def compute_settle_controller_intensity(
    *,
    step: int,
    steps: int,
    kinetic_energy: float,
    floor_contact_ratio: float,
    num_cells: int,
    enabled: bool = True,
    activation_floor_contact: float = 0.10,
    activation_time_fraction: float = 0.18,
    gain: float = 0.85,
    max_intensity: float = 2.2,
    kinetic_per_cell_target: float = 0.10,
    floor_gain: float = 1.2,
) -> SettleControllerDiagnostics:
    if not enabled or num_cells <= 0:
        return SettleControllerDiagnostics(False, 0.0, float(floor_contact_ratio), 0.0, float(kinetic_per_cell_target))

    time_ready = step >= max(1, int(round(max(0.0, activation_time_fraction) * max(1, steps))))
    contact_ready = floor_contact_ratio >= activation_floor_contact
    active = bool(time_ready or contact_ready)
    kinetic_per_cell = float(max(0.0, kinetic_energy) / max(1, num_cells))
    target = float(max(kinetic_per_cell_target, 1e-12))
    if not active:
        return SettleControllerDiagnostics(False, 0.0, float(floor_contact_ratio), kinetic_per_cell, target)

    kinetic_term = max(0.0, np.sqrt(kinetic_per_cell / target) - 1.0)
    floor_term = max(0.0, floor_contact_ratio - activation_floor_contact)
    intensity = gain * kinetic_term + floor_gain * floor_term
    intensity = float(np.clip(intensity, 0.0, max_intensity))
    return SettleControllerDiagnostics(True, intensity, float(floor_contact_ratio), kinetic_per_cell, target)


def settle_to_rest_forces(
    cells: CellState,
    *,
    floor_z: float = 0.0,
    intensity: float,
    global_c: float = 0.0,
    contact_c: float = 0.0,
    radial_c: float = 0.0,
    shell_tangential_c: float = 0.0,
    contact_pad: float = 0.10,
) -> np.ndarray:
    f = np.zeros_like(cells.x)
    if intensity <= 0.0:
        return f

    masses = cells.m[:, None]
    v_com = np.sum(cells.v * masses, axis=0, keepdims=True) / max(float(np.sum(cells.m)), 1e-12)
    v_rel = cells.v - v_com

    if global_c > 0.0:
        f += -(intensity * global_c) * masses * v_rel

    com = np.mean(cells.x, axis=0, keepdims=True)
    radial = cells.x - com
    radial_norm = np.linalg.norm(radial, axis=1, keepdims=True)
    radial_hat = radial / np.maximum(radial_norm, 1e-12)

    if radial_c > 0.0:
        radial_v = np.sum(v_rel * radial_hat, axis=1, keepdims=True)
        f += -(intensity * radial_c) * masses * radial_v * radial_hat

    if shell_tangential_c > 0.0 and np.any(cells.is_surface):
        radial_v = np.sum(v_rel * radial_hat, axis=1, keepdims=True)
        tangential_v = v_rel - radial_v * radial_hat
        shell_mask = cells.is_surface.astype(np.float64)[:, None]
        f += -(intensity * shell_tangential_c) * masses * tangential_v * shell_mask

    if contact_c > 0.0:
        penetration = floor_z - (cells.x[:, 2] - cells.r)
        contact_mask = penetration > (-contact_pad * cells.r)
        if np.any(contact_mask):
            f[contact_mask] += -(intensity * contact_c) * masses[contact_mask] * v_rel[contact_mask]

    return f
