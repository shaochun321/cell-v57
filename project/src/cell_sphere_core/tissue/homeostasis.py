from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from cell_sphere_core.core.datatypes import CellState, TissueReference
from cell_sphere_core.tissue.local_volume import compute_local_volume_density_proxies


EPS = 1e-12


@dataclass
class ActiveHomeostasisState:
    energy_by_band: np.ndarray
    osmotic_activation_by_band: np.ndarray
    contractile_activation_by_band: np.ndarray
    recovery_activation_by_band: np.ndarray
    gate_level_by_band: np.ndarray
    gate_active_by_band: np.ndarray
    stress_memory_by_band: np.ndarray
    prev_band_volume_ratio: np.ndarray
    prev_band_radius_ratio: np.ndarray
    cumulative_energy_used: float = 0.0
    cumulative_energy_recovered: float = 0.0
    initialized: bool = False


@dataclass(frozen=True)
class ActiveHomeostasisDiagnostics:
    mean_energy: float
    min_energy: float
    max_energy: float
    osmotic_mean: float
    contractile_mean: float
    recovery_mean: float
    gate_mean: float
    gate_active_fraction: float
    stress_memory_mean: float
    cumulative_energy_used: float
    cumulative_energy_recovered: float
    band_volume_ratio: np.ndarray
    band_radius_ratio: np.ndarray
    band_gate_level: np.ndarray
    band_gate_signal: np.ndarray
    active_cell_fraction: float


def init_active_homeostasis_state(
    num_bands: int,
    initial_energy: float = 1.0,
) -> ActiveHomeostasisState:
    energy = np.full(int(num_bands), float(initial_energy), dtype=np.float64)
    zeros = np.zeros(int(num_bands), dtype=np.float64)
    return ActiveHomeostasisState(
        energy_by_band=energy,
        osmotic_activation_by_band=zeros.copy(),
        contractile_activation_by_band=zeros.copy(),
        recovery_activation_by_band=zeros.copy(),
        gate_level_by_band=zeros.copy(),
        gate_active_by_band=np.zeros(int(num_bands), dtype=np.bool_),
        stress_memory_by_band=zeros.copy(),
        prev_band_volume_ratio=np.ones(int(num_bands), dtype=np.float64),
        prev_band_radius_ratio=np.ones(int(num_bands), dtype=np.float64),
    )


def _band_means(values: np.ndarray, band_index: np.ndarray, num_bands: int) -> np.ndarray:
    sums = np.bincount(band_index, weights=values, minlength=num_bands).astype(np.float64)
    counts = np.bincount(band_index, minlength=num_bands).astype(np.float64)
    out = np.ones(num_bands, dtype=np.float64)
    mask = counts > 0
    out[mask] = sums[mask] / counts[mask]
    return out


def _empty_diagnostics(num_bands: int, state: ActiveHomeostasisState) -> ActiveHomeostasisDiagnostics:
    return ActiveHomeostasisDiagnostics(
        mean_energy=float(np.mean(state.energy_by_band)) if len(state.energy_by_band) else 0.0,
        min_energy=float(np.min(state.energy_by_band)) if len(state.energy_by_band) else 0.0,
        max_energy=float(np.max(state.energy_by_band)) if len(state.energy_by_band) else 0.0,
        osmotic_mean=float(np.mean(state.osmotic_activation_by_band)) if len(state.osmotic_activation_by_band) else 0.0,
        contractile_mean=float(np.mean(state.contractile_activation_by_band)) if len(state.contractile_activation_by_band) else 0.0,
        recovery_mean=float(np.mean(state.recovery_activation_by_band)) if len(state.recovery_activation_by_band) else 0.0,
        gate_mean=float(np.mean(state.gate_level_by_band)) if len(state.gate_level_by_band) else 0.0,
        gate_active_fraction=float(np.mean(state.gate_active_by_band)) if len(state.gate_active_by_band) else 0.0,
        stress_memory_mean=float(np.mean(state.stress_memory_by_band)) if len(state.stress_memory_by_band) else 0.0,
        cumulative_energy_used=float(state.cumulative_energy_used),
        cumulative_energy_recovered=float(state.cumulative_energy_recovered),
        band_volume_ratio=np.ones(num_bands, dtype=np.float64),
        band_radius_ratio=np.ones(num_bands, dtype=np.float64),
        band_gate_level=np.zeros(num_bands, dtype=np.float64),
        band_gate_signal=np.zeros(num_bands, dtype=np.float64),
        active_cell_fraction=0.0,
    )


def _update_gate_levels(
    state: ActiveHomeostasisState,
    gate_signal: np.ndarray,
    dt: float,
    *,
    gate_on_threshold: float,
    gate_off_threshold: float,
    gate_tau_on: float,
    gate_tau_off: float,
) -> None:
    activate = gate_signal >= gate_on_threshold
    deactivate = gate_signal <= gate_off_threshold
    state.gate_active_by_band = np.where(activate, True, np.where(deactivate, False, state.gate_active_by_band))

    target = np.where(state.gate_active_by_band, np.clip(gate_signal / max(gate_on_threshold, EPS), 0.0, 1.0), 0.0)
    tau = np.where(target > state.gate_level_by_band, max(gate_tau_on, 1e-6), max(gate_tau_off, 1e-6))
    alpha = np.clip(dt / tau, 0.0, 1.0)
    state.gate_level_by_band += alpha * (target - state.gate_level_by_band)
    state.gate_level_by_band = np.clip(state.gate_level_by_band, 0.0, 1.0)



def active_homeostasis_forces(
    cells: CellState,
    tissue_reference: TissueReference,
    state: ActiveHomeostasisState,
    dt: float,
    enabled: bool = True,
    osmotic_force_k: float = 18.0,
    contractile_force_k: float = 12.0,
    recovery_force_k: float = 10.0,
    osmotic_target_gain: float = 1.2,
    contractile_target_gain: float = 1.0,
    recovery_target_gain: float = 0.9,
    activation_tau: float = 0.08,
    energy_recovery_rate: float = 0.12,
    energy_use_rate: float = 0.20,
    energy_floor: float = 0.08,
    max_energy: float = 1.35,
    gating_enabled: bool = True,
    gate_on_threshold: float = 0.12,
    gate_off_threshold: float = 0.06,
    gate_tau_on: float = 0.035,
    gate_tau_off: float = 0.16,
    gate_compression_weight: float = 1.0,
    gate_sag_weight: float = 0.6,
    gate_rate_weight: float = 0.25,
    stress_relax_tau: float = 0.22,
) -> tuple[np.ndarray, ActiveHomeostasisDiagnostics]:
    num_bands = int(tissue_reference.num_radial_bands)
    if not enabled or num_bands <= 0:
        return np.zeros_like(cells.x), _empty_diagnostics(num_bands, state)

    current_local_volume, _ = compute_local_volume_density_proxies(
        cells.x,
        tissue_reference.neighbor_list,
        flat_neighbor_index=tissue_reference.neighbor_flat_index,
        flat_neighbor_owner=tissue_reference.neighbor_owner_index,
        neighbor_counts=tissue_reference.neighbor_counts,
    )
    rest_local_volume = np.maximum(tissue_reference.rest_local_volume_proxy, EPS)
    volume_ratio_per_cell = current_local_volume / rest_local_volume

    com = np.mean(cells.x, axis=0)
    centered = cells.x - com[None, :]
    current_radius = np.linalg.norm(centered, axis=1)
    rest_radius = np.maximum(tissue_reference.rest_radius, EPS)
    radius_ratio_per_cell = current_radius / rest_radius

    band_index = tissue_reference.radial_band_index.astype(np.int64)
    band_volume_ratio = _band_means(volume_ratio_per_cell, band_index, num_bands)
    band_radius_ratio = _band_means(radius_ratio_per_cell, band_index, num_bands)

    compression = np.clip(1.0 - band_volume_ratio, 0.0, None)
    expansion = np.clip(band_volume_ratio - 1.0, 0.0, None)
    sag = np.clip(1.0 - band_radius_ratio, 0.0, None)
    overshoot = np.clip(band_radius_ratio - 1.0, 0.0, None)

    if not state.initialized:
        state.prev_band_volume_ratio = band_volume_ratio.copy()
        state.prev_band_radius_ratio = band_radius_ratio.copy()
        state.initialized = True
    band_volume_rate = (band_volume_ratio - state.prev_band_volume_ratio) / max(dt, 1e-8)
    band_radius_rate = (band_radius_ratio - state.prev_band_radius_ratio) / max(dt, 1e-8)
    deformation_rate = np.abs(band_volume_rate) + 0.7 * np.abs(band_radius_rate)
    state.prev_band_volume_ratio = band_volume_ratio.copy()
    state.prev_band_radius_ratio = band_radius_ratio.copy()

    deform_signal = np.abs(1.0 - band_volume_ratio) + 0.75 * np.abs(1.0 - band_radius_ratio)
    relax_alpha = np.clip(dt / max(stress_relax_tau, 1e-6), 0.0, 1.0)
    state.stress_memory_by_band += relax_alpha * (deform_signal - state.stress_memory_by_band)
    state.stress_memory_by_band = np.clip(state.stress_memory_by_band, 0.0, 2.0)

    gate_signal = gate_compression_weight * compression + gate_sag_weight * sag + gate_rate_weight * deformation_rate
    gate_signal = np.clip(gate_signal, 0.0, 3.0)
    if gating_enabled:
        _update_gate_levels(
            state,
            gate_signal,
            dt,
            gate_on_threshold=gate_on_threshold,
            gate_off_threshold=gate_off_threshold,
            gate_tau_on=gate_tau_on,
            gate_tau_off=gate_tau_off,
        )
    else:
        state.gate_active_by_band[:] = True
        state.gate_level_by_band[:] = 1.0

    gate_level = state.gate_level_by_band

    osmotic_target = np.clip(osmotic_target_gain * (compression + 0.35 * sag), 0.0, 1.75) * gate_level
    contractile_target = np.clip(contractile_target_gain * (0.75 * expansion + 0.50 * overshoot), 0.0, 1.5) * (0.35 + 0.65 * gate_level)
    recovery_target = np.clip(
        recovery_target_gain * (0.40 * state.stress_memory_by_band + 0.35 * np.abs(1.0 - band_volume_ratio) + 0.25 * np.abs(1.0 - band_radius_ratio)),
        0.0,
        1.2,
    ) * (0.2 + 0.8 * gate_level)

    activation_alpha = float(np.clip(dt / max(activation_tau, 1e-6), 0.0, 1.0))
    state.osmotic_activation_by_band += activation_alpha * (osmotic_target - state.osmotic_activation_by_band)
    state.contractile_activation_by_band += activation_alpha * (contractile_target - state.contractile_activation_by_band)
    state.recovery_activation_by_band += activation_alpha * (recovery_target - state.recovery_activation_by_band)

    target_total = (
        0.50 * state.osmotic_activation_by_band
        + 0.15 * state.contractile_activation_by_band
        + 0.20 * state.recovery_activation_by_band
        + 0.15 * state.stress_memory_by_band
    )
    energy_recovered = energy_recovery_rate * (max_energy - state.energy_by_band) * dt
    energy_used = energy_use_rate * target_total * dt
    state.energy_by_band += energy_recovered - energy_used
    state.energy_by_band = np.clip(state.energy_by_band, energy_floor, max_energy)
    state.cumulative_energy_recovered += float(np.sum(np.maximum(energy_recovered, 0.0)))
    state.cumulative_energy_used += float(np.sum(np.maximum(energy_used, 0.0)))

    normalized_energy = np.clip((state.energy_by_band - energy_floor) / max(max_energy - energy_floor, EPS), 0.0, 1.0)
    osmotic_drive = state.osmotic_activation_by_band * normalized_energy
    contractile_drive = state.contractile_activation_by_band * normalized_energy
    recovery_drive = state.recovery_activation_by_band * (0.40 + 0.60 * normalized_energy)

    radial_dir = np.zeros_like(cells.x)
    nonzero = current_radius > 1e-12
    radial_dir[nonzero] = centered[nonzero] / current_radius[nonzero, None]

    band_volume_ratio_per_cell = band_volume_ratio[band_index]
    band_radius_ratio_per_cell = band_radius_ratio[band_index]
    osmotic_drive_per_cell = osmotic_drive[band_index]
    contractile_drive_per_cell = contractile_drive[band_index]
    recovery_drive_per_cell = recovery_drive[band_index]

    compression_per_cell = np.clip(1.0 - volume_ratio_per_cell, 0.0, None)
    local_expansion_per_cell = np.clip(volume_ratio_per_cell - 1.0, 0.0, None)
    radius_error = tissue_reference.rest_radius - current_radius
    surface_weight = np.where(cells.is_surface, 1.0, 0.45)

    osmotic_scalar = osmotic_force_k * osmotic_drive_per_cell * (
        0.7 * compression_per_cell + 0.3 * np.clip(1.0 - band_radius_ratio_per_cell, 0.0, None)
    )
    contractile_scalar = contractile_force_k * contractile_drive_per_cell * (
        0.65 * local_expansion_per_cell + 0.35 * np.clip(band_radius_ratio_per_cell - 1.0, 0.0, None)
    ) * np.where(cells.is_surface, 1.0, 0.35)
    recovery_scalar = recovery_force_k * recovery_drive_per_cell * (radius_error / rest_radius) * surface_weight

    forces = np.zeros_like(cells.x)
    forces += radial_dir * osmotic_scalar[:, None]
    forces -= radial_dir * contractile_scalar[:, None]
    forces += radial_dir * recovery_scalar[:, None]

    active_mask = (np.abs(osmotic_scalar) + np.abs(contractile_scalar) + np.abs(recovery_scalar)) > 1e-12
    diag = ActiveHomeostasisDiagnostics(
        mean_energy=float(np.mean(state.energy_by_band)),
        min_energy=float(np.min(state.energy_by_band)),
        max_energy=float(np.max(state.energy_by_band)),
        osmotic_mean=float(np.mean(state.osmotic_activation_by_band)),
        contractile_mean=float(np.mean(state.contractile_activation_by_band)),
        recovery_mean=float(np.mean(state.recovery_activation_by_band)),
        gate_mean=float(np.mean(state.gate_level_by_band)),
        gate_active_fraction=float(np.mean(state.gate_active_by_band)),
        stress_memory_mean=float(np.mean(state.stress_memory_by_band)),
        cumulative_energy_used=float(state.cumulative_energy_used),
        cumulative_energy_recovered=float(state.cumulative_energy_recovered),
        band_volume_ratio=band_volume_ratio,
        band_radius_ratio=band_radius_ratio,
        band_gate_level=state.gate_level_by_band.copy(),
        band_gate_signal=gate_signal,
        active_cell_fraction=float(np.mean(active_mask)),
    )
    return forces, diag
