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


def test_step20_trace_contains_signed_directional_channels_and_constraint_metadata(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_posx",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trace_path = tmp_path / "translation_posx" / "interface_network_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    first = trace[0]
    assert "circulation_projection" in first["network_structure"]["bundle_channel_names"]
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "circulation_vector" in payload
        assert "propagation_constraints" in payload
        bundle = payload["local_bundles"][0]
        assert "propagation_constraints" in bundle
        assert "circulation_projection" in bundle["channels"]
    diag = result.summary["interface_network_diagnostics"]
    assert diag["stimulus_axes"]["linear_axis"] == "x"
    assert diag["stimulus_axes"]["linear_sign"] == 1.0


def test_step20_preserves_translation_axis_balance_and_rotation_circulation_sign(tmp_path: Path):
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
        pos_balance = trans_pos.summary["interface_network_diagnostics"]["tracks"][track_name]["active_summary"]["axis_balance"]["x"]
        neg_balance = trans_neg.summary["interface_network_diagnostics"]["tracks"][track_name]["active_summary"]["axis_balance"]["x"]
        assert pos_balance < -0.02
        assert neg_balance > 0.02

        pos_circ = rot_pos.summary["interface_network_diagnostics"]["tracks"][track_name]["active_summary"]["mean_global_channels"]["mean_signed_circulation"]
        neg_circ = rot_neg.summary["interface_network_diagnostics"]["tracks"][track_name]["active_summary"]["mean_global_channels"]["mean_signed_circulation"]
        assert pos_circ > 0.001
        assert neg_circ < -0.001


def test_step20_constrained_tracks_reduce_transfer_variability_vs_discrete(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "rotation_z_pos",
        vestibular_motion="rotation",
        vestibular_angular_accel=500.0,
        vestibular_rotation_axis="z",
        vestibular_rotation_sign=1.0,
    )
    tracks = result.summary["interface_network_diagnostics"]["tracks"]
    discrete_std = tracks["discrete_channel_track"]["mean_transfer_std"]
    local_std = tracks["local_propagation_track"]["mean_transfer_std"]
    layered_std = tracks["layered_coupling_track"]["mean_transfer_std"]
    assert local_std < discrete_std
    assert layered_std <= local_std + 1e-6
