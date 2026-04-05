from __future__ import annotations

import numpy as np

from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.mechanics.forces_external import vestibular_rotation_inertial_forces


def test_rotation_force_has_tangential_component_and_outer_shell_bias():
    x = np.asarray([
        [0.1, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ], dtype=np.float64)
    cells = make_cell_state(x=x, cell_radius=0.01)
    shell_fraction = np.asarray([0.0, 1.0, 1.0], dtype=np.float64)
    forces = vestibular_rotation_inertial_forces(
        cells,
        x,
        axis_vec=np.asarray([0.0, 0.0, 1.0], dtype=np.float64),
        axis_sign=1.0,
        alpha_val=100.0,
        reference_radius=1.0,
        shell_fraction=shell_fraction,
        tangential_gain=0.05,
        quadrupole_gain=0.0,
        shell_bias=0.5,
        origin=np.zeros(3, dtype=np.float64),
    )
    inner_norm = float(np.linalg.norm(forces[0]))
    outer_norm = float(np.linalg.norm(forces[1]))
    assert outer_norm > inner_norm
    # Force on +x should point toward +y for positive z rotation.
    assert abs(float(forces[1, 0])) < 1e-9
    assert float(forces[1, 1]) > 0.0
