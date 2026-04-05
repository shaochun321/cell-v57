from __future__ import annotations

import numpy as np
from cell_sphere_core.core.datatypes import CellState


def gravity_forces(cells: CellState, gravity: np.ndarray) -> np.ndarray:
    return cells.m[:, None] * gravity[None, :]


def vestibular_translation_inertial_forces(
    cells: CellState,
    anchor_mask: np.ndarray,
    *,
    accel: np.ndarray,
) -> np.ndarray:
    forces = np.zeros_like(cells.x)
    if np.any(anchor_mask):
        forces[anchor_mask] = cells.m[anchor_mask][:, None] * accel[None, :]
    return forces


def vestibular_rotation_inertial_forces(
    cells: CellState,
    positions: np.ndarray,
    *,
    axis_vec: np.ndarray,
    axis_sign: float,
    alpha_val: float,
    reference_radius: float,
    shell_fraction: np.ndarray | None = None,
    tangential_gain: float = 0.050,
    quadrupole_gain: float = 0.015,
    shell_bias: float = 0.35,
    origin: np.ndarray | None = None,
) -> np.ndarray:
    """Return rotation-like inertial forces with an explicit tangential swirl term.

    This is still a synthetic vestibular-like drive, but it is more physically aligned
    with rotational motion than a purely quadrupolar displacement field. The returned
    force combines:
    - a tangential term proportional to axis x radial position (swirl proxy)
    - a weaker quadrupolar term to preserve shell deformation signatures
    - an optional outer-shell bias that increases coupling for outer bands
    """
    ref_r = max(float(reference_radius), 1e-12)
    if origin is None:
        origin = np.mean(positions, axis=0)
    r_vec = positions - origin[None, :]
    axial = np.sum(r_vec * axis_vec[None, :], axis=1, keepdims=True) * axis_vec[None, :]
    radial = r_vec - axial
    radial_norm = np.linalg.norm(radial, axis=1, keepdims=True)

    tangential_dir = np.cross(np.broadcast_to(axis_vec[None, :], radial.shape), radial)
    tangential_norm = np.linalg.norm(tangential_dir, axis=1, keepdims=True)
    tangential_unit = np.divide(
        tangential_dir,
        np.maximum(tangential_norm, 1e-12),
        out=np.zeros_like(tangential_dir),
        where=tangential_norm > 1e-12,
    )
    tangential_mag = tangential_gain * float(alpha_val) * np.clip(radial_norm / ref_r, 0.0, 2.0)

    quad_dir = radial - 2.0 * axial
    quad_scale = quadrupole_gain * float(alpha_val) / ref_r

    if shell_fraction is None:
        shell_scale = np.ones((positions.shape[0], 1), dtype=np.float64)
    else:
        shell_frac = np.clip(np.asarray(shell_fraction, dtype=np.float64).reshape(-1, 1), 0.0, 1.0)
        shell_scale = 1.0 + float(shell_bias) * shell_frac

    combined = axis_sign * (
        tangential_mag * tangential_unit * shell_scale
        + quad_scale * quad_dir * (0.85 + 0.15 * shell_scale)
    )
    return cells.m[:, None] * combined



def floating_support_forces(
    cells: CellState,
    *,
    reference_center: np.ndarray,
    target_radius: float,
    shell_fraction: np.ndarray | None = None,
    center_k: float = 0.0,
    com_damping_c: float = 0.0,
    radial_k: float = 0.0,
    radial_shell_bias: float = 0.0,
    internal_drag_c: float = 0.0,
    center_scale: float = 1.0,
    radial_scale: float = 1.0,
) -> np.ndarray:
    """Weak isotropic suspension field for floating / gravity-disabled runs.

    This is not a cognitive layer. It is a simple physical support proxy that:
    - suppresses bulk center-of-mass drift
    - damps center-of-mass velocity
    - gently restores shell radius around the instantaneous COM

    The support can be scaled down while vestibular stimuli are active so it does
    not wash out translation / rotation signatures.
    """
    n = cells.x.shape[0]
    if n == 0:
        return np.zeros_like(cells.x)
    ref_center = np.asarray(reference_center, dtype=np.float64).reshape(3)
    target_r = max(float(target_radius), 1e-12)
    center_scale = float(np.clip(center_scale, 0.0, 2.0))
    radial_scale = float(np.clip(radial_scale, 0.0, 2.0))

    total_m = float(np.sum(cells.m))
    if total_m <= 1e-12:
        return np.zeros_like(cells.x)
    com = np.sum(cells.x * cells.m[:, None], axis=0) / total_m
    com_v = np.sum(cells.v * cells.m[:, None], axis=0) / total_m

    forces = np.zeros_like(cells.x)
    if center_k > 0.0 and center_scale > 0.0:
        f_center = -float(center_k) * center_scale * (com - ref_center)
        forces += cells.m[:, None] * f_center[None, :]
    if com_damping_c > 0.0 and center_scale > 0.0:
        f_damp = -float(com_damping_c) * center_scale * com_v
        forces += cells.m[:, None] * f_damp[None, :]

    if internal_drag_c > 0.0 and radial_scale > 0.0:
        internal_v = cells.v - com_v[None, :]
        forces += cells.m[:, None] * (-float(internal_drag_c) * radial_scale * internal_v)

    if radial_k > 0.0 and radial_scale > 0.0:
        rel = cells.x - com[None, :]
        rho = np.linalg.norm(rel, axis=1, keepdims=True)
        unit = np.divide(rel, np.maximum(rho, 1e-12), out=np.zeros_like(rel), where=rho > 1e-12)
        radial_err = rho - target_r
        if shell_fraction is None:
            shell_scale = np.ones_like(radial_err)
        else:
            shell_f = np.clip(np.asarray(shell_fraction, dtype=np.float64).reshape(-1, 1), 0.0, 1.0)
            shell_scale = 1.0 + float(radial_shell_bias) * shell_f
        f_radial = -float(radial_k) * radial_scale * radial_err * unit * shell_scale
        forces += cells.m[:, None] * f_radial

    return forces
