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


def test_step22_trace_contains_spectra_clusters_and_output_file(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "translation_posx",
        vestibular_motion="translation",
        vestibular_linear_accel=80.0,
        vestibular_linear_axis="x",
        vestibular_linear_sign=1.0,
    )
    trace_path = tmp_path / "translation_posx" / "interface_spectrum_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    first = trace[0]
    assert "family_names" in first["spectrum_structure"]
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "spectral_bundles" in payload
        assert "family_clusters" in payload
        assert "transmission_spectra" in payload
        bundle = payload["spectral_bundles"][0]
        assert "dominant_family" in bundle
        assert "transfer_level" in bundle
    diag = result.summary["interface_spectrum_diagnostics"]
    assert diag["output_file"] == "interface_spectrum_trace.json"


def test_step22_external_cluster_bias_and_signed_spectra(tmp_path: Path):
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
        trans_family = trans_pos.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_family_cluster_means"]
        rot_family = rot_pos.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_family_cluster_means"]
        assert trans_family["axial_polar_family"] > trans_family["swirl_circulation_family"]
        assert rot_family["swirl_circulation_family"] > rot_family["axial_polar_family"]

        pos_balance = trans_pos.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_axis_balance"]["axial_polar_family"]["x"]
        neg_balance = trans_neg.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_axis_balance"]["axial_polar_family"]["x"]
        assert pos_balance < -0.01
        assert neg_balance > 0.01

        pos_circ = rot_pos.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        neg_circ = rot_neg.summary["interface_spectrum_diagnostics"]["tracks"][track_name]["active_mean_signed_circulation"]
        assert pos_circ > 0.001
        assert neg_circ < -0.001


def test_step22_propagation_tracks_reduce_transfer_variability_vs_discrete(tmp_path: Path):
    result = _run_case(
        tmp_path,
        "rotation_z_pos",
        vestibular_motion="rotation",
        vestibular_angular_accel=500.0,
        vestibular_rotation_axis="z",
        vestibular_rotation_sign=1.0,
    )
    tracks = result.summary["interface_spectrum_diagnostics"]["tracks"]
    discrete_var = tracks["discrete_channel_track"]["active_mean_transfer_variability"]
    local_var = tracks["local_propagation_track"]["active_mean_transfer_variability"]
    layered_var = tracks["layered_coupling_track"]["active_mean_transfer_variability"]
    assert local_var < discrete_var
    assert layered_var <= local_var + 1e-6
