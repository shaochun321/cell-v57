import numpy as np

from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from cell_sphere_core.tissue.settle_controller import (
    compute_settle_controller_intensity,
    settle_to_rest_forces,
)


def test_settle_controller_force_opposes_residual_motion():
    x = np.array([[0.0, 0.0, 0.004], [0.01, 0.0, 0.012]], dtype=np.float64)
    cells = make_cell_state(x=x, cell_radius=0.004)
    cells.is_surface[:] = True
    cells.v[:] = np.array([[0.6, -0.1, -0.2], [0.3, 0.2, 0.1]], dtype=np.float64)
    f = settle_to_rest_forces(
        cells,
        intensity=1.0,
        global_c=2.0,
        contact_c=8.0,
        radial_c=1.0,
        shell_tangential_c=1.5,
    )
    assert f.shape == x.shape
    assert f[0, 0] < 0.0
    assert np.linalg.norm(f[0]) > 0.0


def test_settle_controller_intensity_activates_after_contact_or_time():
    diag = compute_settle_controller_intensity(
        step=50,
        steps=100,
        kinetic_energy=20.0,
        floor_contact_ratio=0.15,
        num_cells=100,
        enabled=True,
        activation_floor_contact=0.10,
        activation_time_fraction=0.9,
        gain=1.0,
        max_intensity=3.0,
        kinetic_per_cell_target=0.05,
        floor_gain=1.0,
    )
    assert diag.active is True
    assert diag.intensity > 0.0


def test_step11_summary_contains_settle_controller_fields():
    result = run_gravity(
        GravityConfig(num_cells=48, t_end=0.03, dt=0.001, settle_controller_enabled=True),
        save_outputs=False,
    )
    summary = result.summary
    assert 'settle_controller_diagnostics' in summary
    assert 'settle_controller_enabled' in summary['settling_schedule']
    assert 'settle_controller_mean_intensity' in summary['simulator_status']
