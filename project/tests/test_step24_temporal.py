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


def test_step24_trace_contains_temporal_payload_and_output_file(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_x_pos",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trace_path = tmp_path / "translation_x_pos" / "interface_temporal_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    first = trace[0]
    assert "temporal_structure" in first
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "family_trajectories" in payload
        assert "transfer_shell_profile" in payload
        assert "bandwidth_shell_profile" in payload
        assert "axis_polarity_balance" in payload
        assert "signed_circulation" in payload
    diag = result.summary["interface_temporal_diagnostics"]
    assert diag["output_file"] == "interface_temporal_trace.json"


def test_step24_temporal_summary_preserves_translation_rotation_and_signs(tmp_path: Path):
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
        trans_family = trans_pos.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_families"]
        rot_family = rot_pos.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_families"]
        assert sum(trans_family["axial_polar_family"]["shell_profile_mean"]) > sum(trans_family["swirl_circulation_family"]["shell_profile_mean"])
        assert sum(rot_family["swirl_circulation_family"]["shell_profile_mean"]) > sum(rot_family["axial_polar_family"]["shell_profile_mean"])

        pos_balance = trans_pos.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_mean_axis_polarity_balance"]["x"]
        neg_balance = trans_neg.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_mean_axis_polarity_balance"]["x"]
        assert pos_balance > 0.01
        assert neg_balance < -0.01

        pos_circ = rot_pos.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        neg_circ = rot_neg.summary["interface_temporal_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        assert pos_circ > 0.001
        assert neg_circ < -0.001


def test_step24_coupled_tracks_flatten_transfer_attenuation(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_x_pos",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    tracks = result.summary["interface_temporal_diagnostics"]["tracks"]
    discrete_att = tracks["discrete_channel_track"]["active_transfer"]["mean_attenuation_index"]
    local_att = tracks["local_propagation_track"]["active_transfer"]["mean_attenuation_index"]
    layered_att = tracks["layered_coupling_track"]["active_transfer"]["mean_attenuation_index"]
    assert local_att <= discrete_att + 1e-6
    assert layered_att <= local_att + 1e-6
