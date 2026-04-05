from __future__ import annotations

import json
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

TRACKS = [
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
]


def _run_case(tmp_path: Path, name: str, **kwargs):
    return run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.18,
            dt=0.001,
            disable_gravity=True,
            sensor_record_every=10,
            record_every=10,
            vestibular_onset_fraction=0.2,
            vestibular_duration_fraction=0.6,
            **kwargs,
        ),
        outdir=tmp_path / name,
        save_outputs=True,
    )


def test_step23_trace_contains_topology_and_output_file(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_posx",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trace_path = tmp_path / "translation_posx" / "interface_topology_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    first = trace[0]
    assert "sector_order" in first["topology_structure"]
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "response_atlas" in payload
        assert "topology_nodes" in payload
        assert "topology_edges" in payload
        assert "family_topology" in payload
        assert payload["topology_nodes"]
    diag = result.summary["interface_topology_diagnostics"]
    assert diag["output_file"] == "interface_topology_trace.json"


def test_step23_topology_preserves_translation_rotation_and_signs(tmp_path: Path):
    trans_pos = _run_case(
        tmp_path,
        "translation_x_pos",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trans_neg = _run_case(
        tmp_path,
        "translation_x_neg",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=-1.0,
    )
    rot_pos = _run_case(
        tmp_path,
        "rotation_z_pos",
        vestibular_motion="rotation",
        vestibular_angular_accel=500.0,
        vestibular_rotation_axis="z",
        vestibular_rotation_sign=1.0,
    )
    rot_neg = _run_case(
        tmp_path,
        "rotation_z_neg",
        vestibular_motion="rotation",
        vestibular_angular_accel=500.0,
        vestibular_rotation_axis="z",
        vestibular_rotation_sign=-1.0,
    )
    for track_name in TRACKS:
        trans_family = trans_pos.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_family_shell_mean"]
        rot_family = rot_pos.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_family_shell_mean"]
        assert trans_family["axial_polar_family"] > trans_family["swirl_circulation_family"]
        assert rot_family["swirl_circulation_family"] > rot_family["axial_polar_family"]

        pos_balance = trans_pos.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_axis_polarity_balance"]["x"]
        neg_balance = trans_neg.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_axis_polarity_balance"]["x"]
        assert pos_balance > 0.01
        assert neg_balance < -0.01

        pos_circ = rot_pos.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        neg_circ = rot_neg.summary["interface_topology_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        assert pos_circ > 0.001
        assert neg_circ < -0.001


def test_step23_coupled_tracks_reduce_axial_topology_roughness(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_x_pos",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    tracks = result.summary["interface_topology_diagnostics"]["tracks"]
    discrete_r = tracks["discrete_channel_track"]["active_family_response_roughness"]["axial_polar_family"]
    local_r = tracks["local_propagation_track"]["active_family_response_roughness"]["axial_polar_family"]
    layered_r = tracks["layered_coupling_track"]["active_family_response_roughness"]["axial_polar_family"]
    assert local_r <= discrete_r + 1e-6
    assert layered_r <= local_r + 1e-6
