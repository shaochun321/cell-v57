import json
import numpy as np

from cell_sphere_core.cells.state import make_cell_state
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from cell_sphere_core.sensing.mechanical_interface import sample_mechanical_sensors
from cell_sphere_core.tissue.homeostasis import active_homeostasis_forces, init_active_homeostasis_state
from cell_sphere_core.tissue.reference_state import build_tissue_reference


def _make_ref(scale: float = 1.0):
    x_ref = np.array(
        [
            [0.020, 0.000, 0.000],
            [0.000, 0.020, 0.000],
            [0.000, 0.000, 0.020],
            [-0.014, -0.014, -0.014],
        ],
        dtype=np.float64,
    ) * scale
    edges = np.array([[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]], dtype=np.int64)
    is_surface = np.ones(len(x_ref), dtype=bool)
    tissue_ref = build_tissue_reference(x_ref, edges, is_surface, np.zeros(3), num_radial_bands=2)
    return x_ref, tissue_ref


def test_homeostasis_gate_stays_low_near_reference_and_rises_under_compression():
    x_ref, tissue_ref = _make_ref()
    state = init_active_homeostasis_state(tissue_ref.num_radial_bands, initial_energy=1.0)

    cells_ref = make_cell_state(x=x_ref.copy(), cell_radius=0.004)
    cells_ref.is_surface[:] = True
    _, diag_ref = active_homeostasis_forces(cells_ref, tissue_ref, state, dt=0.02, enabled=True)

    cells_compressed = make_cell_state(x=x_ref * 0.78, cell_radius=0.004)
    cells_compressed.is_surface[:] = True
    for _ in range(4):
        _, diag_comp = active_homeostasis_forces(
            cells_compressed,
            tissue_ref,
            state,
            dt=0.02,
            enabled=True,
            osmotic_force_k=32.0,
            recovery_force_k=16.0,
        )

    assert diag_ref.gate_mean <= 0.05
    assert diag_comp.gate_mean > diag_ref.gate_mean
    assert diag_comp.gate_active_fraction > 0.0


def test_mechanical_sensor_snapshot_has_expected_shapes():
    x_ref, tissue_ref = _make_ref(scale=0.9)
    cells = make_cell_state(x=x_ref, cell_radius=0.004)
    cells.is_surface[:] = True
    cells.v[:] = np.array([[0.1, 0.0, -0.2], [0.0, 0.1, -0.1], [0.0, 0.0, -0.15], [0.02, -0.01, -0.05]])
    total_forces = np.tile(np.array([0.0, 0.0, -1.0]), (len(x_ref), 1))
    snap = sample_mechanical_sensors(cells, tissue_ref, total_forces, floor_z=0.0)
    assert snap.band_compression.shape == (tissue_ref.num_radial_bands,)
    assert snap.band_sag.shape == (tissue_ref.num_radial_bands,)
    assert snap.band_force_density.shape == (tissue_ref.num_radial_bands,)
    assert snap.global_accel_norm >= 0.0


def test_step13_summary_contains_sensor_and_gating_fields(tmp_path):
    outdir = tmp_path / 'out'
    result = run_gravity(
        GravityConfig(num_cells=48, t_end=0.03, dt=0.001, active_homeostasis_enabled=True, sensor_enabled=True),
        outdir=outdir,
        save_outputs=True,
    )
    summary = result.summary
    assert 'sensor_config' in summary
    assert 'sensor_diagnostics' in summary
    assert 'gate_mean' in summary['homeostasis_diagnostics']
    assert (outdir / 'sensor_trace.json').exists()
    data = json.loads((outdir / 'sensor_trace.json').read_text(encoding='utf-8'))
    assert isinstance(data, list)
    assert len(data) >= 1
