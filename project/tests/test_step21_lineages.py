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


def test_step21_trace_contains_lineage_families_and_output_file(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_posx",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trace_path = tmp_path / "translation_posx" / "interface_lineage_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    first = trace[0]
    assert "family_names" in first["lineage_structure"]
    assert "axial_polar_family" in first["lineage_structure"]["family_names"]
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "family_summary" in payload
        assert "shell_spectra" in payload
        assert "sector_spectra" in payload
        bundle = payload["lineage_bundles"][0]
        assert "lineage_id" in bundle
        assert "family_response" in bundle
        assert "bandwidth_proxy" in bundle
    diag = result.summary["interface_lineage_diagnostics"]
    assert diag["output_file"] == "interface_lineage_trace.json"


def test_step21_external_family_bias_and_signed_lineage_projections(tmp_path: Path):
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
        trans_family = trans_pos.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_family_means"]
        rot_family = rot_pos.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_family_means"]
        assert trans_family["axial_polar_family"] > trans_family["swirl_circulation_family"]
        assert rot_family["swirl_circulation_family"] > rot_family["axial_polar_family"]

        pos_balance = trans_pos.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_family_axis_balance"]["axial_polar_family"]["x"]
        neg_balance = trans_neg.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_family_axis_balance"]["axial_polar_family"]["x"]
        assert pos_balance < -0.01
        assert neg_balance > 0.01

        pos_circ = rot_pos.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        neg_circ = rot_neg.summary["interface_lineage_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        assert pos_circ > 0.001
        assert neg_circ < -0.001


def test_step21_propagation_tracks_preserve_transfer_smoothing_metadata(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "rotation_z_pos",
        vestibular_motion="rotation",
        vestibular_angular_accel=500.0,
        vestibular_rotation_axis="z",
        vestibular_rotation_sign=1.0,
    )
    tracks = result.summary["interface_lineage_diagnostics"]["tracks"]
    discrete_std = tracks["discrete_channel_track"]["mean_transfer_std"]
    local_std = tracks["local_propagation_track"]["mean_transfer_std"]
    layered_std = tracks["layered_coupling_track"]["mean_transfer_std"]
    assert local_std < discrete_std
    assert layered_std <= local_std + 1e-6
