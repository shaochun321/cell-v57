from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

from cell_sphere_core.core.datatypes import BuildConfig, NeighborGraph, SphereAggregate
from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.aggregate.seed import generate_sphere_points
from cell_sphere_core.aggregate.neighbors import build_neighbor_graph
from cell_sphere_core.aggregate.surface import classify_surface_cells
from cell_sphere_core.aggregate.topology import (
    EDGE_SURFACE_TANGENTIAL,
    EDGE_MIXED_SURFACE,
    classify_edges,
)
from cell_sphere_core.viz.plot_cells import plot_aggregate
from cell_sphere_core.mechanics.forces_external import (
    gravity_forces,
    vestibular_rotation_inertial_forces,
    vestibular_translation_inertial_forces,
    floating_support_forces,
)
from cell_sphere_core.mechanics.forces_internal import spring_damper_forces
from cell_sphere_core.mechanics.contact import contact_repulsion_forces
from cell_sphere_core.mechanics.boundary import floor_forces
from cell_sphere_core.mechanics.integrator import semi_implicit_euler
from cell_sphere_core.tissue.surface_tension import surface_tension_forces
from cell_sphere_core.tissue.volume_pressure import volume_pressure_forces
from cell_sphere_core.tissue.reference_state import build_tissue_reference
from cell_sphere_core.tissue.foam_network import foam_network_forces
from cell_sphere_core.tissue.material_profiles import (
    RadialBandMaterialProfile,
    build_radial_band_material_profile,
    expand_material_profile_to_cells,
)
from cell_sphere_core.tissue.band_damping import band_viscous_damping_forces
from cell_sphere_core.tissue.homeostasis import (
    ActiveHomeostasisDiagnostics,
    init_active_homeostasis_state,
    active_homeostasis_forces,
)
from cell_sphere_core.tissue.settle_controller import (
    SettleControllerDiagnostics,
    compute_settle_controller_intensity,
    settle_to_rest_forces,
)
from cell_sphere_core.tissue.local_volume import (
    compute_local_volume_density_proxies,
    summarize_local_proxy_drift,
)
from cell_sphere_core.reference.sizing import ReferenceSphere, estimate_reference_sphere
from cell_sphere_core.analysis.metrics import compute_metrics
from cell_sphere_core.analysis.scoring import near_sphere_score
from cell_sphere_core.analysis.process_state import (
    compute_process_state_snapshot,
    enrich_process_state_trace,
    summarize_process_state_trace,
    summarize_transition_memory_trace,
)
from cell_sphere_core.analysis.readout import (
    build_external_readout_trace,
    summarize_external_readout_trace,
)
from cell_sphere_core.analysis.interface_bundles import (
    build_mirror_interface_trace,
    summarize_mirror_interface_trace,
)
from cell_sphere_core.analysis.interface_network import (
    build_interface_network_trace,
    summarize_interface_network_trace,
)
from cell_sphere_core.analysis.interface_lineages import (
    build_interface_lineage_trace,
    summarize_interface_lineage_trace,
)
from cell_sphere_core.analysis.interface_spectra import (
    build_interface_spectrum_trace,
    summarize_interface_spectrum_trace,
)
from cell_sphere_core.analysis.interface_topology import (
    build_interface_topology_trace,
    summarize_interface_topology_trace,
)
from cell_sphere_core.analysis.interface_temporal import (
    build_interface_temporal_trace,
    summarize_interface_temporal_trace,
)
from cell_sphere_core.analysis.channel_hypergraph import (
    build_channel_hypergraph_trace,
    summarize_channel_hypergraph_trace,
)
from cell_sphere_core.analysis.channel_motifs import (
    build_channel_motif_trace,
    summarize_channel_motif_trace,
)
from cell_sphere_core.sensing.mechanical_interface import (
    MechanicalSensorSnapshot,
    sample_mechanical_sensors,
    extract_node_sensor_frame,
    write_sensor_nodes_jsonl,
)

@dataclass
class GravityConfig:
    num_cells: int = 300
    sphere_radius: float | None = None
    cell_radius: float = 0.004
    packing_fraction: float = 0.68
    radius_safety_factor: float = 1.02
    rng_seed: int = 7
    t_end: float = 1.5
    dt: float = 5e-4
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)
    initial_clearance_factor: float = 1.2
    k_bulk: float = 240.0
    c_bulk: float = 2.5
    repulsion_k: float = 900.0
    floor_k: float = 5000.0
    floor_c: float = 35.0
    floor_tangential_c: float = 6.0
    floor_friction_mu: float = 0.22
    global_damping: float = 0.8
    surface_radial_gain: float = 1.2
    surface_tangential_gain: float = 2.0
    mixed_surface_gain: float = 1.45
    record_every: int = 20
    sensor_enabled: bool = True
    sensor_record_every: int = 20
    # === 新增：前庭仿生测试配置 ===
    disable_gravity: bool = False  # 是否关闭重力和地板，实现悬浮
    vestibular_motion: str | None = None  # "translation" 或 "rotation"
    enable_tissue: bool = True
    tissue_tension_k: float = 18.0
    tissue_target_shrink: float = 0.975
    tissue_mixed_gain: float = 0.5
    tissue_pressure_k: float = 900.0
    tissue_surface_only_pressure: bool = True
    tissue_pressure_rate_damping_c: float = 18.0

    enable_foam_tissue: bool = True
    tissue_radial_bands: int = 4
    tissue_local_pressure_k: float = 90.0
    tissue_shell_curvature_k: float = 55.0
    tissue_shell_radial_k: float = 65.0
    tissue_bulk_radial_k: float = 14.0
    tissue_band_interface_k: float = 24.0
    tissue_band_restoring_k: float = 30.0
    tissue_shell_reference_k: float = 56.0
    tissue_bulk_reference_k: float = 8.0

    tissue_inner_stiffness_scale: float = 0.85
    tissue_outer_stiffness_scale: float = 1.35
    tissue_inner_damping_scale: float = 1.55
    tissue_outer_damping_scale: float = 0.90
    tissue_inner_shear_scale: float = 0.80
    tissue_outer_shear_scale: float = 1.45
    tissue_band_damping_c: float = 5.0
    tissue_band_radial_damping_c: float = 5.8
    tissue_band_tangential_damping_c: float = 2.4
    tissue_radial_rate_damping_c: float = 3.0
    tissue_shell_tangential_damping_c: float = 2.0
    tissue_shell_neighbor_support_k: float = 8.0

    gravity_ramp_fraction: float = 0.22
    settle_damping_boost: float = 3.0
    settle_pressure_boost: float = 1.40
    settle_shell_boost: float = 1.20
    adaptive_settle_enabled: bool = True
    adaptive_settle_gain: float = 0.12
    adaptive_settle_max_boost: float = 1.6
    adaptive_settle_ke_ref: float = 60.0
    adaptive_settle_floor_ref: float = 0.28

    settle_controller_enabled: bool = True
    settle_controller_activation_floor_contact: float = 0.22
    settle_controller_activation_time_fraction: float = 0.32
    settle_controller_gain: float = 0.50
    settle_controller_max_intensity: float = 1.5
    settle_controller_kinetic_per_cell_target: float = 0.18
    settle_controller_floor_gain: float = 0.9
    settle_controller_global_c: float = 1.0
    settle_controller_contact_c: float = 4.5
    settle_controller_radial_c: float = 1.4
    settle_controller_shell_tangential_c: float = 0.9

    active_homeostasis_enabled: bool = True
    homeostasis_initial_energy: float = 1.0
    homeostasis_osmotic_force_k: float = 14.0
    homeostasis_contractile_force_k: float = 0.0
    homeostasis_recovery_force_k: float = 12.0
    homeostasis_osmotic_target_gain: float = 1.10
    homeostasis_contractile_target_gain: float = 0.70
    homeostasis_recovery_target_gain: float = 0.90
    homeostasis_activation_tau: float = 0.08
    homeostasis_energy_recovery_rate: float = 0.11
    homeostasis_energy_use_rate: float = 0.18
    homeostasis_energy_floor: float = 0.08
    homeostasis_max_energy: float = 1.30
    homeostasis_gating_enabled: bool = True
    homeostasis_gate_on_threshold: float = 0.12
    homeostasis_gate_off_threshold: float = 0.06
    homeostasis_gate_tau_on: float = 0.035
    homeostasis_gate_tau_off: float = 0.16
    homeostasis_gate_compression_weight: float = 1.0
    homeostasis_gate_sag_weight: float = 0.6
    homeostasis_gate_rate_weight: float = 0.25
    homeostasis_stress_relax_tau: float = 0.22

    early_stop_kinetic_energy: float = 1e-3
    early_stop_window: int = 100
    equilibrium_score_window: int = 8
    equilibrium_kinetic_threshold: float = 0.025
    equilibrium_score_threshold: float = 0.003
    max_steps: int | None = None
    # === 前庭测试选项 ===
    disable_gravity_and_floor: bool = False
    vestibular_motion: str | None = None
    vestibular_onset_fraction: float = 0.4
    vestibular_duration_fraction: float = 1.0
    vestibular_linear_accel: float = 500.0   # <--- 新增：线加速度大小
    vestibular_angular_accel: float = 3000.0 # <--- 新增：角加速度大小
    vestibular_linear_axis: str = "x"
    vestibular_linear_sign: float = -1.0
    vestibular_rotation_axis: str = "z"
    vestibular_rotation_sign: float = 1.0
    vestibular_rotation_tangential_gain: float = 0.050
    vestibular_rotation_quadrupole_gain: float = 0.015
    vestibular_rotation_shell_bias: float = 0.35

    interface_layered_rotation_swirl_gain: float = 1.0
    interface_layered_rotation_circulation_gain: float = 1.10
    interface_layered_rotation_axial_base: float = 0.90
    interface_layered_rotation_transfer_base: float = 0.96
    interface_layered_rotation_circulation_feed: float = 0.18

    floating_support_enabled: bool = True
    floating_support_center_k: float = 10.0
    floating_support_com_damping_c: float = 3.5
    floating_support_radial_k: float = 18.0
    floating_support_radial_shell_bias: float = 0.45
    floating_support_internal_drag_c: float = 3.5
    floating_support_center_scale_active: float = 0.22
    floating_support_radial_scale_active: float = 0.85

@dataclass(frozen=True)
class GravityRunResult:
    summary: dict
    times: list[float]
    metrics: list[dict]
    reference: ReferenceSphere


def build_aggregate(
    num_cells: int,
    sphere_radius: float,
    cell_radius: float,
    rng_seed: int,
    tissue_radial_bands: int = 4,
) -> SphereAggregate:
    cfg = BuildConfig(sphere_radius=sphere_radius, cell_radius=cell_radius, rng_seed=rng_seed)
    x = generate_sphere_points(
        num_cells=num_cells,
        sphere_radius=cfg.sphere_radius,
        cell_radius=cfg.cell_radius,
        jitter=cfg.jitter,
        rng_seed=cfg.rng_seed,
    )
    cells = make_cell_state(x=x, cell_radius=cfg.cell_radius)
    center = np.zeros(3, dtype=np.float64)
    edges, degree = build_neighbor_graph(
        x=cells.x,
        cell_radius=cfg.cell_radius,
        neighbor_radius_factor=cfg.neighbor_radius_factor,
        k_min=cfg.k_min,
        k_max=cfg.k_max,
    )
    is_surface, _ = classify_surface_cells(
        x=cells.x,
        center=center,
        target_radius=cfg.sphere_radius,
        edges=edges,
        cell_radius=cfg.cell_radius,
        shell_thickness_factor=cfg.shell_thickness_factor,
        exposure_threshold=cfg.exposure_threshold,
        degree_factor=cfg.degree_factor,
    )
    cells.is_surface = is_surface
    edge_type = classify_edges(x=cells.x, center=center, edges=edges, is_surface=cells.is_surface)
    rest_length = np.linalg.norm(cells.x[edges[:, 1]] - cells.x[edges[:, 0]], axis=1)
    edge_codes = edges[:, 0].astype(np.int64) * np.int64(num_cells) + edges[:, 1].astype(np.int64)
    graph = NeighborGraph(
        edges=edges,
        rest_length=rest_length,
        edge_type=edge_type,
        degree=degree,
        bonded_pair_codes=edge_codes,
    )
    tissue_reference = build_tissue_reference(
        cells.x,
        edges,
        cells.is_surface,
        center,
        num_radial_bands=tissue_radial_bands,
    )
    return SphereAggregate(
        center=center,
        target_radius=cfg.sphere_radius,
        cells=cells,
        graph=graph,
        tissue_reference=tissue_reference,
    )


def resolve_reference(cfg: GravityConfig) -> ReferenceSphere:
    ref = estimate_reference_sphere(
        num_cells=cfg.num_cells,
        cell_radius=cfg.cell_radius,
        packing_fraction=cfg.packing_fraction,
        safety_factor=cfg.radius_safety_factor,
    )
    if cfg.sphere_radius is not None:
        return ReferenceSphere(
            num_cells=ref.num_cells,
            cell_radius=ref.cell_radius,
            packing_fraction=ref.packing_fraction,
            safety_factor=ref.safety_factor,
            target_radius=cfg.sphere_radius,
            target_volume=(4.0 / 3.0) * np.pi * (cfg.sphere_radius ** 3),
            single_cell_volume=ref.single_cell_volume,
            total_cell_volume=ref.total_cell_volume,
        )
    return ref


def build_material_profile(cfg: GravityConfig, effective_bands: int) -> RadialBandMaterialProfile:
    return build_radial_band_material_profile(
        num_bands=effective_bands,
        inner_stiffness_scale=cfg.tissue_inner_stiffness_scale,
        outer_stiffness_scale=cfg.tissue_outer_stiffness_scale,
        inner_damping_scale=cfg.tissue_inner_damping_scale,
        outer_damping_scale=cfg.tissue_outer_damping_scale,
        inner_shear_scale=cfg.tissue_inner_shear_scale,
        outer_shear_scale=cfg.tissue_outer_shear_scale,
    )


def build_edge_material_scales(
    graph: NeighborGraph,
    band_index: np.ndarray,
    cell_stiffness: np.ndarray,
    cell_damping: np.ndarray,
    cell_shear: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    edge_stiffness = np.ones(len(graph.edges), dtype=np.float64)
    edge_damping = np.ones(len(graph.edges), dtype=np.float64)
    for e_idx, (i, j) in enumerate(graph.edges):
        base_stiffness = 0.5 * (float(cell_stiffness[i]) + float(cell_stiffness[j]))
        base_damping = 0.5 * (float(cell_damping[i]) + float(cell_damping[j]))
        base_shear = 0.5 * (float(cell_shear[i]) + float(cell_shear[j]))
        edge_stiffness[e_idx] = base_stiffness
        edge_damping[e_idx] = base_damping
        et = int(graph.edge_type[e_idx])
        if et == EDGE_SURFACE_TANGENTIAL:
            edge_stiffness[e_idx] *= base_shear
        elif et == EDGE_MIXED_SURFACE:
            edge_stiffness[e_idx] *= 0.5 * (1.0 + base_shear)
        if int(band_index[i]) == int(band_index[j]):
            edge_damping[e_idx] *= 1.05
    return edge_stiffness, edge_damping


def plot_metrics(times: list[float], metrics: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sag = [m['sag_ratio'] for m in metrics]
    vol = [m['volume_ratio'] for m in metrics]
    shp = [m['shape_deviation'] for m in metrics]
    asph = [m['asphericity'] for m in metrics]
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs = axs.ravel()
    axs[0].plot(times, sag); axs[0].set_title('Sag ratio'); axs[0].set_xlabel('time')
    axs[1].plot(times, vol); axs[1].set_title('Volume ratio'); axs[1].set_xlabel('time')
    axs[2].plot(times, shp); axs[2].set_title('Shape deviation'); axs[2].set_xlabel('time')
    axs[3].plot(times, asph); axs[3].set_title('Asphericity'); axs[3].set_xlabel('time')
    fig.tight_layout(); fig.savefig(out_path, dpi=180); plt.close(fig)


def _tail_equilibrium_diagnostics(metrics: list[dict], window: int) -> dict:
    if not metrics:
        return {
            'window': 0,
            'tail_kinetic_mean': 0.0,
            'tail_kinetic_max': 0.0,
            'tail_score_mean': 0.0,
            'tail_score_std': 0.0,
            'tail_volume_ratio_mean': 0.0,
            'tail_shape_mean': 0.0,
            'tail_floor_contact_mean': 0.0,
            'tail_sag_mean': 0.0,
            'is_quasi_static': False,
        }
    tail = metrics[-max(1, int(window)):]
    scores = np.array([near_sphere_score(m) for m in tail], dtype=np.float64)
    kinetic = np.array([float(m['kinetic_energy']) for m in tail], dtype=np.float64)
    volume = np.array([float(m['volume_ratio']) for m in tail], dtype=np.float64)
    shape = np.array([float(m['shape_deviation']) for m in tail], dtype=np.float64)
    floor_contact = np.array([float(m['floor_contact_ratio']) for m in tail], dtype=np.float64)
    sag = np.array([float(m['sag_ratio']) for m in tail], dtype=np.float64)
    return {
        'window': int(len(tail)),
        'tail_kinetic_mean': float(np.mean(kinetic)),
        'tail_kinetic_max': float(np.max(kinetic)),
        'tail_score_mean': float(np.mean(scores)),
        'tail_score_std': float(np.std(scores)),
        'tail_volume_ratio_mean': float(np.mean(volume)),
        'tail_shape_mean': float(np.mean(shape)),
        'tail_floor_contact_mean': float(np.mean(floor_contact)),
        'tail_sag_mean': float(np.mean(sag)),
        'is_quasi_static': False,
    }


def _ramp_weight(step: int, steps: int, fraction: float) -> float:
    if steps <= 0 or fraction <= 0.0:
        return 1.0
    ramp_steps = max(1, int(round(steps * fraction)))
    return float(min(1.0, step / ramp_steps))


def _adaptive_settle_multiplier(last_metrics: dict | None, cfg: GravityConfig) -> float:
    if not cfg.adaptive_settle_enabled or last_metrics is None:
        return 1.0
    ke = float(last_metrics.get('kinetic_energy', 0.0))
    floor_contact = float(last_metrics.get('floor_contact_ratio', 0.0))
    ke_term = np.sqrt(max(0.0, ke) / max(cfg.adaptive_settle_ke_ref, 1e-12))
    floor_term = max(0.0, floor_contact - cfg.adaptive_settle_floor_ref) / max(cfg.adaptive_settle_floor_ref, 1e-12)
    gain = 1.0 + cfg.adaptive_settle_gain * (ke_term + 0.45 * floor_term)
    return float(np.clip(gain, 1.0, cfg.adaptive_settle_max_boost))


def run_gravity(cfg: GravityConfig, outdir: str | Path | None = None, save_outputs: bool = True) -> GravityRunResult:
    outdir_path = Path(outdir) if outdir is not None else None
    if save_outputs and outdir_path is None:
        raise ValueError('outdir must be provided when save_outputs is True')
    if save_outputs and outdir_path is not None:
        outdir_path.mkdir(parents=True, exist_ok=True)
    reference = resolve_reference(cfg)
    aggregate = build_aggregate(cfg.num_cells, reference.target_radius, cfg.cell_radius, cfg.rng_seed, tissue_radial_bands=cfg.tissue_radial_bands)
    cells = aggregate.cells
    material_profile = build_material_profile(cfg, aggregate.tissue_reference.num_radial_bands)
    cell_stiffness, cell_damping, cell_shear = expand_material_profile_to_cells(aggregate.tissue_reference.radial_band_index, material_profile)
    edge_stiffness_scale, edge_damping_scale = build_edge_material_scales(aggregate.graph, aggregate.tissue_reference.radial_band_index, cell_stiffness, cell_damping, cell_shear)
    if cfg.disable_gravity:
        z0 = 5.0 * reference.target_radius
    else:
        z0 = reference.target_radius + cfg.initial_clearance_factor * cfg.cell_radius
    cells.x[:, 2] += z0
    target_volume = reference.target_volume
    times: list[float] = []
    metrics: list[dict] = []
    gravity = np.asarray(cfg.gravity, dtype=np.float64)
    last_pressure_delta = 0.0
    last_current_volume = target_volume
    last_pressure_rate_ratio = 0.0
    size_settle_scale = float(np.clip(np.sqrt(cfg.num_cells / 800.0), 0.45, 1.8))
    steps = int(cfg.t_end / cfg.dt)
    if cfg.max_steps is not None:
        steps = min(steps, int(cfg.max_steps))
    recent_ke: list[float] = []
    recent_scores: list[float] = []
    adaptive_boost_history: list[float] = []
    settle_controller_history: list[float] = []
    settle_controller_active_steps = 0
    executed_steps = steps
    last_metrics: dict | None = None
    last_controller_diag = SettleControllerDiagnostics(False, 0.0, 0.0, 0.0, cfg.settle_controller_kinetic_per_cell_target)
    homeostasis_state = init_active_homeostasis_state(aggregate.tissue_reference.num_radial_bands, initial_energy=cfg.homeostasis_initial_energy)
    last_homeostasis_diag = ActiveHomeostasisDiagnostics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, np.ones(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.ones(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), 0.0)
    sensor_trace: list[dict] = []
    sensor_nodes_trace: list[dict] = []
    process_state_trace: list[dict] = []
    last_sensor_snapshot = MechanicalSensorSnapshot(0.0, 0.0, np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64), np.zeros(aggregate.tissue_reference.num_radial_bands, dtype=np.float64))
    for step in range(steps + 1):
        t = step * cfg.dt
        if step % cfg.record_every == 0 or step == steps:
            current_metrics = compute_metrics(
                x=cells.x,
                v=cells.v,
                m=cells.m,
                r=cells.r,
                sphere_radius=reference.target_radius,
                target_volume=target_volume,
            )
            times.append(t)
            metrics.append(current_metrics)
            last_metrics = current_metrics
            current_score = near_sphere_score(current_metrics)
            recent_ke.append(float(current_metrics['kinetic_energy']))
            recent_scores.append(float(current_score))
            if len(recent_ke) > cfg.early_stop_window:
                recent_ke.pop(0)
            if len(recent_scores) > cfg.equilibrium_score_window:
                recent_scores.pop(0)

        ramp = _ramp_weight(step, steps, cfg.gravity_ramp_fraction)
        adaptive_boost = _adaptive_settle_multiplier(last_metrics, cfg)
        adaptive_boost_history.append(adaptive_boost)
        controller_diag = compute_settle_controller_intensity(
            step=step,
            steps=steps,
            kinetic_energy=float(last_metrics.get('kinetic_energy', 0.0)) if last_metrics is not None else 0.0,
            floor_contact_ratio=float(last_metrics.get('floor_contact_ratio', 0.0)) if last_metrics is not None else 0.0,
            num_cells=cfg.num_cells,
            enabled=cfg.settle_controller_enabled,
            activation_floor_contact=cfg.settle_controller_activation_floor_contact,
            activation_time_fraction=cfg.settle_controller_activation_time_fraction,
            gain=cfg.settle_controller_gain,
            max_intensity=cfg.settle_controller_max_intensity,
            kinetic_per_cell_target=cfg.settle_controller_kinetic_per_cell_target,
            floor_gain=cfg.settle_controller_floor_gain,
        )
        settle_controller_history.append(controller_diag.intensity)
        if controller_diag.active and controller_diag.intensity > 0.0:
            settle_controller_active_steps += 1
        last_controller_diag = controller_diag
        settle_boost = (1.0 + (1.0 - ramp) * max(0.0, cfg.settle_damping_boost - 1.0)) * adaptive_boost
        shell_boost = (1.0 + (1.0 - ramp) * max(0.0, cfg.settle_shell_boost - 1.0)) * (1.0 + 0.45 * (adaptive_boost - 1.0))
        pressure_boost = (1.0 + (1.0 - ramp) * max(0.0, cfg.settle_pressure_boost - 1.0)) * (1.0 + 0.30 * (adaptive_boost - 1.0))

# 1. 外部受力：如果是悬浮模式，则关闭重力；否则正常施加重力
        if getattr(cfg, "disable_gravity", False):
            f_ext = np.zeros_like(cells.x)
        else:
            f_ext = gravity_forces(cells, gravity * ramp)

        # 内部受力和接触力保持不变
        f_int = spring_damper_forces(
            cells,
            aggregate.graph,
            k_bulk=cfg.k_bulk,
            c_bulk=cfg.c_bulk * settle_boost,
            surface_radial_gain=cfg.surface_radial_gain,
            surface_tangential_gain=cfg.surface_tangential_gain,
            mixed_surface_gain=cfg.mixed_surface_gain,
            edge_stiffness_scale=edge_stiffness_scale,
            edge_damping_scale=edge_damping_scale,
        )
        f_contact = contact_repulsion_forces(cells, aggregate.graph, repulsion_k=cfg.repulsion_k)
        
        # 2. 地板受力：如果是悬浮模式，则关闭地板碰撞；否则正常计算
        if getattr(cfg, "disable_gravity", False):
            f_floor = np.zeros_like(cells.x)
        else:
            f_floor = floor_forces(
                cells,
                floor_z=0.0,
                k_floor=cfg.floor_k,
                c_floor=cfg.floor_c * settle_boost,
                tangential_c=cfg.floor_tangential_c * size_settle_scale * (1.0 + 0.35 * (adaptive_boost - 1.0)),
                friction_mu=cfg.floor_friction_mu,
            )

        # === 3. 前庭仿生学刺激 (施加虚拟惯性力) ===
        onset_step = int(steps * cfg.vestibular_onset_fraction)
        duration_steps = max(1, int(steps * cfg.vestibular_duration_fraction))
        offset_step = min(steps + 1, onset_step + duration_steps)
        motion_type = getattr(cfg, "vestibular_motion", None)
        stimulus_active = bool(motion_type is not None and onset_step < step <= offset_step)
        anchor_mask = aggregate.tissue_reference.radial_band_index == 0
        band_idx = np.asarray(aggregate.tissue_reference.radial_band_index, dtype=np.float64)
        shell_fraction = band_idx / max(float(np.max(band_idx)), 1.0)

        if stimulus_active:
            if motion_type == "translation":
                a_val = getattr(cfg, "vestibular_linear_accel", 500.0)
                axis_name = str(getattr(cfg, "vestibular_linear_axis", "x")).lower()
                axis_map = {"x": np.array([1.0, 0.0, 0.0], dtype=np.float64), "y": np.array([0.0, 1.0, 0.0], dtype=np.float64), "z": np.array([0.0, 0.0, 1.0], dtype=np.float64)}
                axis_vec = axis_map.get(axis_name, axis_map["x"])
                axis_sign = -1.0 if float(getattr(cfg, "vestibular_linear_sign", -1.0)) < 0.0 else 1.0
                accel = axis_sign * a_val * axis_vec
                f_ext += vestibular_translation_inertial_forces(cells, anchor_mask, accel=accel)
            elif motion_type == "rotation":
                alpha_val = getattr(cfg, "vestibular_angular_accel", 3000.0)
                axis_name = str(getattr(cfg, "vestibular_rotation_axis", "z")).lower()
                axis_map = {"x": np.array([1.0, 0.0, 0.0], dtype=np.float64), "y": np.array([0.0, 1.0, 0.0], dtype=np.float64), "z": np.array([0.0, 0.0, 1.0], dtype=np.float64)}
                axis_vec = axis_map.get(axis_name, axis_map["z"])
                axis_sign = -1.0 if float(getattr(cfg, "vestibular_rotation_sign", 1.0)) < 0.0 else 1.0
                ref_origin = np.mean(cells.x[anchor_mask], axis=0) if np.any(anchor_mask) else np.mean(cells.x, axis=0)
                f_ext += vestibular_rotation_inertial_forces(
                    cells,
                    cells.x,
                    axis_vec=axis_vec,
                    axis_sign=axis_sign,
                    alpha_val=alpha_val,
                    reference_radius=reference.target_radius,
                    shell_fraction=shell_fraction,
                    tangential_gain=float(getattr(cfg, "vestibular_rotation_tangential_gain", 0.050)),
                    quadrupole_gain=float(getattr(cfg, "vestibular_rotation_quadrupole_gain", 0.015)),
                    shell_bias=float(getattr(cfg, "vestibular_rotation_shell_bias", 0.35)),
                    origin=ref_origin,
                )
        if getattr(cfg, "disable_gravity", False) and getattr(cfg, "floating_support_enabled", True):
            center_scale = float(cfg.floating_support_center_scale_active) if stimulus_active else 1.0
            radial_scale = float(cfg.floating_support_radial_scale_active) if stimulus_active else 1.0
            f_float = floating_support_forces(
                cells,
                reference_center=np.asarray([0.0, 0.0, z0], dtype=np.float64),
                target_radius=reference.target_radius,
                shell_fraction=shell_fraction,
                center_k=cfg.floating_support_center_k,
                com_damping_c=cfg.floating_support_com_damping_c,
                radial_k=cfg.floating_support_radial_k,
                radial_shell_bias=cfg.floating_support_radial_shell_bias,
                internal_drag_c=cfg.floating_support_internal_drag_c,
                center_scale=center_scale,
                radial_scale=radial_scale,
            )
        else:
            f_float = np.zeros_like(cells.x)

        f_tissue = np.zeros_like(cells.x)
        f_rest = settle_to_rest_forces(
            cells,
            floor_z=0.0,
            intensity=controller_diag.intensity,
            global_c=cfg.settle_controller_global_c * size_settle_scale,
            contact_c=cfg.settle_controller_contact_c * size_settle_scale,
            radial_c=cfg.settle_controller_radial_c * size_settle_scale,
            shell_tangential_c=cfg.settle_controller_shell_tangential_c * size_settle_scale,
        )
        if cfg.enable_tissue:
            f_tension = surface_tension_forces(
                cells,
                aggregate.graph,
                tension_k=cfg.tissue_tension_k * shell_boost,
                target_shrink=cfg.tissue_target_shrink,
                mixed_gain=cfg.tissue_mixed_gain,
            )
            f_pressure, last_current_volume, last_pressure_delta, last_pressure_rate_ratio = volume_pressure_forces(
                cells,
                target_volume=target_volume,
                pressure_k=cfg.tissue_pressure_k * pressure_boost,
                surface_only=cfg.tissue_surface_only_pressure,
                prev_volume=last_current_volume,
                dt=cfg.dt,
                pressure_rate_damping_c=cfg.tissue_pressure_rate_damping_c * size_settle_scale * pressure_boost,
            )
            f_tissue = f_tension + f_pressure
            if cfg.enable_foam_tissue:
                f_tissue += foam_network_forces(
                    cells,
                    aggregate.graph,
                    aggregate.tissue_reference,
                    local_pressure_k=cfg.tissue_local_pressure_k * pressure_boost,
                    shell_curvature_k=cfg.tissue_shell_curvature_k * shell_boost,
                    shell_radial_k=cfg.tissue_shell_radial_k * shell_boost,
                    bulk_radial_k=cfg.tissue_bulk_radial_k,
                    band_interface_k=cfg.tissue_band_interface_k,
                    band_restoring_k=cfg.tissue_band_restoring_k,
                    shell_reference_k=cfg.tissue_shell_reference_k * shell_boost,
                    bulk_reference_k=cfg.tissue_bulk_reference_k,
                    stiffness_scale_by_cell=cell_stiffness,
                    stiffness_scale_by_band=material_profile.stiffness_scale_by_band,
                    shear_scale_by_cell=cell_shear,
                    radial_rate_damping_c=cfg.tissue_radial_rate_damping_c * size_settle_scale * (1.0 + 0.35 * (adaptive_boost - 1.0)),
                    shell_tangential_damping_c=cfg.tissue_shell_tangential_damping_c * size_settle_scale * (1.0 + 0.35 * (adaptive_boost - 1.0)),
                    shell_neighbor_support_k=cfg.tissue_shell_neighbor_support_k * (1.0 + 0.20 * (adaptive_boost - 1.0)),
                )
                f_tissue += band_viscous_damping_forces(
                    cells,
                    aggregate.tissue_reference,
                    damping_scale_by_cell=cell_damping,
                    base_damping_c=cfg.tissue_band_damping_c * settle_boost,
                    radial_damping_c=cfg.tissue_band_radial_damping_c * settle_boost,
                    tangential_damping_c=cfg.tissue_band_tangential_damping_c * settle_boost,
                )
        f_homeostasis, last_homeostasis_diag = active_homeostasis_forces(
            cells,
            aggregate.tissue_reference,
            homeostasis_state,
            dt=cfg.dt,
            enabled=cfg.active_homeostasis_enabled,
            osmotic_force_k=cfg.homeostasis_osmotic_force_k,
            contractile_force_k=cfg.homeostasis_contractile_force_k,
            recovery_force_k=cfg.homeostasis_recovery_force_k,
            osmotic_target_gain=cfg.homeostasis_osmotic_target_gain,
            contractile_target_gain=cfg.homeostasis_contractile_target_gain,
            recovery_target_gain=cfg.homeostasis_recovery_target_gain,
            activation_tau=cfg.homeostasis_activation_tau,
            energy_recovery_rate=cfg.homeostasis_energy_recovery_rate,
            energy_use_rate=cfg.homeostasis_energy_use_rate,
            energy_floor=cfg.homeostasis_energy_floor,
            max_energy=cfg.homeostasis_max_energy,
            gating_enabled=cfg.homeostasis_gating_enabled,
            gate_on_threshold=cfg.homeostasis_gate_on_threshold,
            gate_off_threshold=cfg.homeostasis_gate_off_threshold,
            gate_tau_on=cfg.homeostasis_gate_tau_on,
            gate_tau_off=cfg.homeostasis_gate_tau_off,
            gate_compression_weight=cfg.homeostasis_gate_compression_weight,
            gate_sag_weight=cfg.homeostasis_gate_sag_weight,
            gate_rate_weight=cfg.homeostasis_gate_rate_weight,
            stress_relax_tau=cfg.homeostasis_stress_relax_tau,
        )
        forces = f_ext + f_int + f_contact + f_floor + f_float + f_tissue + f_rest + f_homeostasis
        if cfg.sensor_enabled and (step % max(1, cfg.sensor_record_every) == 0 or step == steps):
            last_sensor_snapshot = sample_mechanical_sensors(cells, aggregate.tissue_reference, forces, floor_z=0.0)
            sensor_metrics = compute_metrics(
                x=cells.x,
                v=cells.v,
                m=cells.m,
                r=cells.r,
                sphere_radius=reference.target_radius,
                target_volume=target_volume,
            )
            sensor_metrics['near_sphere_score'] = float(near_sphere_score(sensor_metrics))
            _sensor_com = np.sum(cells.x * cells.m[:, None], axis=0) / np.sum(cells.m)
            sensor_metrics['center_of_mass_radius'] = float(np.linalg.norm(_sensor_com))
            sensor_metrics['center_of_mass_xy_radius'] = float(np.linalg.norm(_sensor_com[:2]))
            sensor_trace.append({
                'time': float(t),
                **last_sensor_snapshot.to_dict(),
            })
            node_frame = extract_node_sensor_frame(
                cells,
                aggregate.tissue_reference,
                forces,
                gate_level_by_band=last_homeostasis_diag.band_gate_level,
                gate_signal_by_band=last_homeostasis_diag.band_gate_signal,
                floor_z=0.0,
            )
            process_state = compute_process_state_snapshot(
                node_frame=node_frame,
                sensor_snapshot=last_sensor_snapshot,
                metrics=sensor_metrics,
                stimulus_mode=motion_type,
                stimulus_active=stimulus_active,
                field_name='v_r',
                band='outer',
            ).to_dict()
            sensor_trace[-1]['surface_nodes'] = node_frame['surface_nodes']
            sensor_trace[-1]['reference_frame'] = node_frame['reference_frame']
            sensor_trace[-1]['process_state'] = process_state
            sensor_nodes_trace.append({
                'time': float(t),
                'stimulus': {
                    'mode': motion_type,
                    'active': stimulus_active,
                },
                'process_state': process_state,
                **node_frame,
            })
            process_state_trace.append({
                'time': float(t),
                'stimulus_mode': motion_type,
                'stimulus_active': stimulus_active,
                **process_state,
            })
        semi_implicit_euler(cells, forces, cfg.dt, global_damping=cfg.global_damping * settle_boost)
        if len(recent_ke) >= cfg.early_stop_window and max(recent_ke) < cfg.early_stop_kinetic_energy:
            executed_steps = step
            break
        if len(recent_scores) >= cfg.equilibrium_score_window and len(recent_ke) >= cfg.equilibrium_score_window:
            score_span = max(recent_scores) - min(recent_scores)
            ke_window_max = max(recent_ke[-cfg.equilibrium_score_window:])
            if ke_window_max < cfg.equilibrium_kinetic_threshold and score_span < cfg.equilibrium_score_threshold:
                executed_steps = step
                break
    process_state_trace = enrich_process_state_trace(process_state_trace)
    readout_trace = build_external_readout_trace(process_state_trace)
    interface_trace = build_mirror_interface_trace(sensor_nodes_trace, process_state_trace, readout_trace)
    interface_network_trace = build_interface_network_trace(
        sensor_nodes_trace,
        process_state_trace,
        layered_rotation_repair={
            "swirl_gain": cfg.interface_layered_rotation_swirl_gain,
            "circulation_gain": cfg.interface_layered_rotation_circulation_gain,
            "axial_base": cfg.interface_layered_rotation_axial_base,
            "transfer_base": cfg.interface_layered_rotation_transfer_base,
            "circulation_feed": cfg.interface_layered_rotation_circulation_feed,
        },
    )
    interface_lineage_trace = build_interface_lineage_trace(interface_network_trace)
    interface_spectrum_trace = build_interface_spectrum_trace(interface_lineage_trace)
    interface_topology_trace = build_interface_topology_trace(interface_spectrum_trace)
    interface_temporal_trace = build_interface_temporal_trace(interface_topology_trace)
    channel_hypergraph_trace = build_channel_hypergraph_trace(interface_temporal_trace)
    channel_motif_trace = build_channel_motif_trace(channel_hypergraph_trace)
    for trace_row, readout_row, interface_row, network_row, lineage_row, spectrum_row, topology_row, temporal_row, hyper_row, motif_row, frame_row, sensor_row in zip(process_state_trace, readout_trace, interface_trace, interface_network_trace, interface_lineage_trace, interface_spectrum_trace, interface_topology_trace, interface_temporal_trace, channel_hypergraph_trace, channel_motif_trace, sensor_nodes_trace, sensor_trace):
        frame_row['external_readout'] = {k: v for k, v in readout_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['external_readout'] = {k: v for k, v in readout_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['mirror_interface'] = {k: v for k, v in interface_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['mirror_interface'] = {k: v for k, v in interface_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['interface_network'] = {k: v for k, v in network_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['interface_network'] = {k: v for k, v in network_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['interface_lineages'] = {k: v for k, v in lineage_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['interface_lineages'] = {k: v for k, v in lineage_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['interface_spectra'] = {k: v for k, v in spectrum_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['interface_spectra'] = {k: v for k, v in spectrum_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['interface_topology'] = {k: v for k, v in topology_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['interface_topology'] = {k: v for k, v in topology_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['interface_temporal'] = {k: v for k, v in temporal_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['interface_temporal'] = {k: v for k, v in temporal_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['channel_hypergraph'] = {k: v for k, v in hyper_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['channel_hypergraph'] = {k: v for k, v in hyper_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['channel_motifs'] = {k: v for k, v in motif_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        sensor_row['channel_motifs'] = {k: v for k, v in motif_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active', 'transition_state'}}
        frame_row['process_state'].update({k: v for k, v in trace_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active'}})
        sensor_row['process_state'].update({k: v for k, v in trace_row.items() if k not in {'time', 'stimulus_mode', 'stimulus_active'}})

    final = metrics[-1]
    current_local_volume_proxy, current_local_density_proxy = compute_local_volume_density_proxies(cells.x, aggregate.tissue_reference.neighbor_list)
    local_proxy_diagnostics = summarize_local_proxy_drift(
        aggregate.tissue_reference.rest_local_volume_proxy,
        current_local_volume_proxy,
        aggregate.tissue_reference.rest_local_density_proxy,
        current_local_density_proxy,
    )
    equilibrium = _tail_equilibrium_diagnostics(metrics, cfg.equilibrium_score_window)
    equilibrium['is_quasi_static'] = bool(
        equilibrium['tail_kinetic_max'] < cfg.equilibrium_kinetic_threshold
        and equilibrium['tail_score_std'] < cfg.equilibrium_score_threshold
    )
    summary = {
        'experiment': 'gravity',
        'num_cells': cfg.num_cells,
        'tissue_enabled': cfg.enable_tissue,
        'foam_tissue_enabled': cfg.enable_foam_tissue,
        'packing_fraction': cfg.packing_fraction,
        'target_radius': float(reference.target_radius),
        'target_volume': float(reference.target_volume),
        'final_metrics': final,
        'near_sphere_score': float(near_sphere_score(final)),
        'surface_cell_ratio': float(np.mean(cells.is_surface)),
        'num_edges': int(len(aggregate.graph.edges)),
        'current_volume': float(last_current_volume),
        'pressure_delta_ratio': float(last_pressure_delta),
        'pressure_rate_ratio': float(last_pressure_rate_ratio),
        'tissue_config': {
            'tension_k': cfg.tissue_tension_k,
            'pressure_k': cfg.tissue_pressure_k,
            'pressure_rate_damping_c': cfg.tissue_pressure_rate_damping_c,
            'radial_bands': cfg.tissue_radial_bands,
            'local_pressure_k': cfg.tissue_local_pressure_k,
            'shell_curvature_k': cfg.tissue_shell_curvature_k,
            'shell_radial_k': cfg.tissue_shell_radial_k,
            'bulk_radial_k': cfg.tissue_bulk_radial_k,
            'band_interface_k': cfg.tissue_band_interface_k,
            'band_restoring_k': cfg.tissue_band_restoring_k,
            'shell_reference_k': cfg.tissue_shell_reference_k,
            'bulk_reference_k': cfg.tissue_bulk_reference_k,
            'inner_stiffness_scale': cfg.tissue_inner_stiffness_scale,
            'outer_stiffness_scale': cfg.tissue_outer_stiffness_scale,
            'inner_damping_scale': cfg.tissue_inner_damping_scale,
            'outer_damping_scale': cfg.tissue_outer_damping_scale,
            'inner_shear_scale': cfg.tissue_inner_shear_scale,
            'outer_shear_scale': cfg.tissue_outer_shear_scale,
            'band_damping_c': cfg.tissue_band_damping_c,
            'band_radial_damping_c': cfg.tissue_band_radial_damping_c,
            'band_tangential_damping_c': cfg.tissue_band_tangential_damping_c,
            'radial_rate_damping_c': cfg.tissue_radial_rate_damping_c,
            'shell_tangential_damping_c': cfg.tissue_shell_tangential_damping_c,
            'shell_neighbor_support_k': cfg.tissue_shell_neighbor_support_k,
        },
        'settling_schedule': {
            'gravity_ramp_fraction': cfg.gravity_ramp_fraction,
            'settle_damping_boost': cfg.settle_damping_boost,
            'settle_pressure_boost': cfg.settle_pressure_boost,
            'settle_shell_boost': cfg.settle_shell_boost,
            'adaptive_settle_enabled': cfg.adaptive_settle_enabled,
            'adaptive_settle_gain': cfg.adaptive_settle_gain,
            'adaptive_settle_max_boost': cfg.adaptive_settle_max_boost,
            'adaptive_settle_ke_ref': cfg.adaptive_settle_ke_ref,
            'adaptive_settle_floor_ref': cfg.adaptive_settle_floor_ref,
            'settle_controller_enabled': cfg.settle_controller_enabled,
            'settle_controller_activation_floor_contact': cfg.settle_controller_activation_floor_contact,
            'settle_controller_activation_time_fraction': cfg.settle_controller_activation_time_fraction,
            'settle_controller_gain': cfg.settle_controller_gain,
            'settle_controller_max_intensity': cfg.settle_controller_max_intensity,
            'settle_controller_kinetic_per_cell_target': cfg.settle_controller_kinetic_per_cell_target,
            'settle_controller_floor_gain': cfg.settle_controller_floor_gain,
            'settle_controller_global_c': cfg.settle_controller_global_c,
            'settle_controller_contact_c': cfg.settle_controller_contact_c,
            'settle_controller_radial_c': cfg.settle_controller_radial_c,
            'settle_controller_shell_tangential_c': cfg.settle_controller_shell_tangential_c,
            'floor_tangential_c': cfg.floor_tangential_c,
            'floor_friction_mu': cfg.floor_friction_mu,
            'size_settle_scale': size_settle_scale,
        },
        'tissue_reference': {
            'effective_radial_bands': int(aggregate.tissue_reference.num_radial_bands),
            'radial_band_counts': aggregate.tissue_reference.radial_band_counts.tolist(),
            'radial_band_mean_rest_radius': aggregate.tissue_reference.radial_band_mean_rest_radius.tolist(),
            'radial_band_bounds': aggregate.tissue_reference.radial_band_bounds.tolist(),
        },
        'material_profile': {
            'stiffness_scale_by_band': material_profile.stiffness_scale_by_band.tolist(),
            'damping_scale_by_band': material_profile.damping_scale_by_band.tolist(),
            'shear_scale_by_band': material_profile.shear_scale_by_band.tolist(),
        },
        'local_proxy_diagnostics': local_proxy_diagnostics,
        'equilibrium_diagnostics': equilibrium,
        'simulator_status': {
            'requested_t_end': float(cfg.t_end),
            'executed_t_end': float(times[-1]) if times else 0.0,
            'requested_steps': int(round(cfg.t_end / cfg.dt)),
            'executed_steps': int(executed_steps),
            'early_stopped': bool((times[-1] if times else 0.0) + 1e-12 < cfg.t_end),
            'adaptive_settle_mean_boost': float(np.mean(adaptive_boost_history)) if adaptive_boost_history else 1.0,
            'adaptive_settle_max_boost': float(np.max(adaptive_boost_history)) if adaptive_boost_history else 1.0,
            'settle_controller_mean_intensity': float(np.mean(settle_controller_history)) if settle_controller_history else 0.0,
            'settle_controller_max_intensity': float(np.max(settle_controller_history)) if settle_controller_history else 0.0,
            'settle_controller_active_steps': int(settle_controller_active_steps),
        },
        'settle_controller_diagnostics': {
            'last_active': bool(last_controller_diag.active),
            'last_intensity': float(last_controller_diag.intensity),
            'last_contact_ratio': float(last_controller_diag.contact_ratio),
            'last_kinetic_per_cell': float(last_controller_diag.kinetic_per_cell),
            'target_kinetic_per_cell': float(last_controller_diag.target_kinetic_per_cell),
        },
        'homeostasis_config': {
            'enabled': cfg.active_homeostasis_enabled,
            'initial_energy': cfg.homeostasis_initial_energy,
            'osmotic_force_k': cfg.homeostasis_osmotic_force_k,
            'contractile_force_k': cfg.homeostasis_contractile_force_k,
            'recovery_force_k': cfg.homeostasis_recovery_force_k,
            'osmotic_target_gain': cfg.homeostasis_osmotic_target_gain,
            'contractile_target_gain': cfg.homeostasis_contractile_target_gain,
            'recovery_target_gain': cfg.homeostasis_recovery_target_gain,
            'activation_tau': cfg.homeostasis_activation_tau,
            'energy_recovery_rate': cfg.homeostasis_energy_recovery_rate,
            'energy_use_rate': cfg.homeostasis_energy_use_rate,
            'energy_floor': cfg.homeostasis_energy_floor,
            'max_energy': cfg.homeostasis_max_energy,
            'gating_enabled': cfg.homeostasis_gating_enabled,
            'gate_on_threshold': cfg.homeostasis_gate_on_threshold,
            'gate_off_threshold': cfg.homeostasis_gate_off_threshold,
            'gate_tau_on': cfg.homeostasis_gate_tau_on,
            'gate_tau_off': cfg.homeostasis_gate_tau_off,
            'gate_compression_weight': cfg.homeostasis_gate_compression_weight,
            'gate_sag_weight': cfg.homeostasis_gate_sag_weight,
            'gate_rate_weight': cfg.homeostasis_gate_rate_weight,
            'stress_relax_tau': cfg.homeostasis_stress_relax_tau,
        },
        'homeostasis_diagnostics': {
            'mean_energy': float(last_homeostasis_diag.mean_energy),
            'min_energy': float(last_homeostasis_diag.min_energy),
            'max_energy': float(last_homeostasis_diag.max_energy),
            'osmotic_mean': float(last_homeostasis_diag.osmotic_mean),
            'contractile_mean': float(last_homeostasis_diag.contractile_mean),
            'recovery_mean': float(last_homeostasis_diag.recovery_mean),
            'gate_mean': float(last_homeostasis_diag.gate_mean),
            'gate_active_fraction': float(last_homeostasis_diag.gate_active_fraction),
            'stress_memory_mean': float(last_homeostasis_diag.stress_memory_mean),
            'cumulative_energy_used': float(last_homeostasis_diag.cumulative_energy_used),
            'cumulative_energy_recovered': float(last_homeostasis_diag.cumulative_energy_recovered),
            'band_volume_ratio': last_homeostasis_diag.band_volume_ratio.tolist(),
            'band_radius_ratio': last_homeostasis_diag.band_radius_ratio.tolist(),
            'band_gate_level': last_homeostasis_diag.band_gate_level.tolist(),
            'band_gate_signal': last_homeostasis_diag.band_gate_signal.tolist(),
            'active_cell_fraction': float(last_homeostasis_diag.active_cell_fraction),
        },
        'sensor_config': {
            'enabled': cfg.sensor_enabled,
            'sensor_record_every': cfg.sensor_record_every,
        },
        'sensor_diagnostics': {
            **last_sensor_snapshot.to_dict(),
            'num_samples': int(len(sensor_trace)),
            'node_frame_samples': int(len(sensor_nodes_trace)),
            'node_output_file': 'sensor_nodes.jsonl' if cfg.sensor_enabled else None,
        },
        'process_state_diagnostics': {
            **summarize_process_state_trace(process_state_trace),
            'output_file': 'motion_state_trace.json' if cfg.sensor_enabled else None,
        },
        'state_memory_diagnostics': {
            **summarize_transition_memory_trace(process_state_trace),
            'output_file': 'motion_state_trace.json' if cfg.sensor_enabled else None,
        },
        'external_readout_diagnostics': {
            **summarize_external_readout_trace(readout_trace),
            'output_file': 'readout_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'virtual concentric shell readout outside unified cell sphere',
        },
        'mirror_interface_diagnostics': {
            **summarize_mirror_interface_trace(interface_trace),
            'output_file': 'interface_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'mirror-shell interface bundles outside unified cell sphere',
        },
        'interface_network_diagnostics': {
            **summarize_interface_network_trace(interface_network_trace),
            'output_file': 'interface_network_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'parallel physically constrained transduction-channel comparison outside unified cell sphere',
            'stimulus_axes': {
                'linear_axis': cfg.vestibular_linear_axis,
                'linear_sign': float(cfg.vestibular_linear_sign),
                'rotation_axis': cfg.vestibular_rotation_axis,
                'rotation_sign': float(cfg.vestibular_rotation_sign),
                'rotation_tangential_gain': float(cfg.vestibular_rotation_tangential_gain),
                'rotation_quadrupole_gain': float(cfg.vestibular_rotation_quadrupole_gain),
                'rotation_shell_bias': float(cfg.vestibular_rotation_shell_bias),
            },
        },
        'interface_lineage_diagnostics': {
            **summarize_interface_lineage_trace(interface_lineage_trace),
            'output_file': 'interface_lineage_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'channel-family lineage view of interface transduction outside unified cell sphere',
        },
        'interface_spectrum_diagnostics': {
            **summarize_interface_spectrum_trace(interface_spectrum_trace),
            'output_file': 'interface_spectrum_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'bundle-family plus inter-shell transmission spectrum outside unified cell sphere',
        },
        'interface_topology_diagnostics': {
            **summarize_interface_topology_trace(interface_topology_trace),
            'output_file': 'interface_topology_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'bundle-family topology and response atlas outside unified cell sphere',
        },
        'interface_temporal_diagnostics': {
            **summarize_interface_temporal_trace(interface_temporal_trace),
            'output_file': 'interface_temporal_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'time-varying propagation and attenuation atlas outside unified cell sphere',
        },
        'channel_hypergraph_diagnostics': {
            **summarize_channel_hypergraph_trace(channel_hypergraph_trace),
            'output_file': 'channel_hypergraph_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'temporal attributed hypergraph of channel topology outside unified cell sphere',
        },
        'channel_motif_diagnostics': {
            **summarize_channel_motif_trace(channel_motif_trace),
            'output_file': 'channel_motif_trace.json' if cfg.sensor_enabled else None,
            'architecture': 'stable substructures and repeated higher-order propagation motifs extracted externally from the channel hypergraph',
        },
    }
    if save_outputs and outdir_path is not None:
        plot_metrics(times, metrics, outdir_path / 'metrics.png')
        plot_aggregate(cells.x, cells.is_surface, outdir_path / 'final_state.png', title='Final sphere state')
        with open(outdir_path / 'summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'sensor_trace.json', 'w', encoding='utf-8') as f:
            json.dump(sensor_trace, f, ensure_ascii=False, indent=2)
        write_sensor_nodes_jsonl(outdir_path / 'sensor_nodes.jsonl', sensor_nodes_trace)
        with open(outdir_path / 'motion_state_trace.json', 'w', encoding='utf-8') as f:
            json.dump(process_state_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'readout_trace.json', 'w', encoding='utf-8') as f:
            json.dump(readout_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_network_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_network_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_lineage_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_lineage_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_spectrum_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_spectrum_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_topology_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_topology_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'interface_temporal_trace.json', 'w', encoding='utf-8') as f:
            json.dump(interface_temporal_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'channel_hypergraph_trace.json', 'w', encoding='utf-8') as f:
            json.dump(channel_hypergraph_trace, f, ensure_ascii=False, indent=2)
        with open(outdir_path / 'channel_motif_trace.json', 'w', encoding='utf-8') as f:
            json.dump(channel_motif_trace, f, ensure_ascii=False, indent=2)
    return GravityRunResult(summary=summary, times=times, metrics=metrics, reference=reference)
