import numpy as np

from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.mechanics.boundary import floor_forces
from cell_sphere_core.tissue.volume_pressure import volume_pressure_forces


def test_floor_tangential_damping_opposes_sliding():
    x = np.array([[0.0, 0.0, 0.0035]], dtype=np.float64)
    cells = make_cell_state(x=x, cell_radius=0.004)
    cells.v[0] = np.array([1.0, -0.5, -0.2], dtype=np.float64)
    f = floor_forces(cells, floor_z=0.0, k_floor=5000.0, c_floor=20.0, tangential_c=10.0, friction_mu=0.5)
    assert f[0, 2] > 0.0
    assert f[0, 0] < 0.0
    assert f[0, 1] > 0.0


def test_volume_pressure_returns_rate_ratio():
    x = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    cells = make_cell_state(x=x, cell_radius=0.1)
    cells.is_surface[:] = True
    f, current_volume, delta_ratio, rate_ratio = volume_pressure_forces(
        cells,
        target_volume=1.5,
        pressure_k=100.0,
        prev_volume=1.0,
        dt=0.1,
        pressure_rate_damping_c=10.0,
    )
    assert np.isfinite(current_volume)
    assert np.isfinite(delta_ratio)
    assert np.isfinite(rate_ratio)
    assert f.shape == x.shape
