import numpy as np

from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from cell_sphere_core.tissue.homeostasis import (
    active_homeostasis_forces,
    init_active_homeostasis_state,
)
from cell_sphere_core.tissue.reference_state import build_tissue_reference


def test_homeostasis_pushes_outward_under_compression():
    x_ref = np.array(
        [
            [0.020, 0.000, 0.000],
            [0.000, 0.020, 0.000],
            [0.000, 0.000, 0.020],
            [-0.014, -0.014, -0.014],
        ],
        dtype=np.float64,
    )
    edges = np.array([[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]], dtype=np.int64)
    is_surface = np.ones(len(x_ref), dtype=bool)
    tissue_ref = build_tissue_reference(x_ref, edges, is_surface, np.zeros(3), num_radial_bands=2)

    cells = make_cell_state(x=x_ref * 0.82, cell_radius=0.004)
    cells.is_surface[:] = True
    state = init_active_homeostasis_state(tissue_ref.num_radial_bands, initial_energy=1.0)
    forces, diag = active_homeostasis_forces(
        cells,
        tissue_ref,
        state,
        dt=0.02,
        enabled=True,
        osmotic_force_k=40.0,
        recovery_force_k=12.0,
    )
    radial_dir = cells.x / np.maximum(np.linalg.norm(cells.x, axis=1, keepdims=True), 1e-12)
    radial_component = np.sum(forces * radial_dir, axis=1)
    assert np.mean(radial_component) > 0.0
    assert diag.osmotic_mean >= 0.0


def test_homeostasis_energy_stays_bounded_over_updates():
    x_ref = np.array(
        [
            [0.020, 0.000, 0.000],
            [0.000, 0.020, 0.000],
            [0.000, 0.000, 0.020],
            [-0.014, -0.014, -0.014],
        ],
        dtype=np.float64,
    )
    edges = np.array([[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]], dtype=np.int64)
    is_surface = np.ones(len(x_ref), dtype=bool)
    tissue_ref = build_tissue_reference(x_ref, edges, is_surface, np.zeros(3), num_radial_bands=2)
    cells = make_cell_state(x=x_ref * 0.88, cell_radius=0.004)
    cells.is_surface[:] = True
    state = init_active_homeostasis_state(tissue_ref.num_radial_bands, initial_energy=0.9)
    for _ in range(20):
        active_homeostasis_forces(
            cells,
            tissue_ref,
            state,
            dt=0.01,
            enabled=True,
            max_energy=1.25,
            energy_floor=0.1,
        )
    assert np.all(state.energy_by_band >= 0.1 - 1e-9)
    assert np.all(state.energy_by_band <= 1.25 + 1e-9)


def test_step12_summary_contains_homeostasis_fields():
    result = run_gravity(
        GravityConfig(num_cells=48, t_end=0.03, dt=0.001, active_homeostasis_enabled=True),
        save_outputs=False,
    )
    summary = result.summary
    assert 'homeostasis_config' in summary
    assert 'homeostasis_diagnostics' in summary
    assert summary['homeostasis_config']['enabled'] is True
