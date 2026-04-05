from __future__ import annotations

import json
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


TRACKS = [
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
]


def test_step19_writes_interface_network_trace_without_embedded_semantic_labels(tmp_path: Path):
    outdir = tmp_path / "floating_static"
    result = run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.12,
            dt=0.001,
            disable_gravity=True,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=outdir,
        save_outputs=True,
    )
    trace_path = outdir / "interface_network_trace.json"
    assert trace_path.exists()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace
    first = trace[0]
    assert first["network_structure"]["tracks"] == TRACKS
    assert "deformation_drive" in first["network_structure"]["bundle_channel_names"]
    assert "tracks" in first
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "global_channels" in payload
        assert "layer_summaries" in payload
        assert "local_bundles" in payload
        assert "spatial_metrics" in payload
        assert "global_motion_class" not in payload
        assert "readout_class" not in payload
        assert "interface_class" not in payload
    diag = result.summary["interface_network_diagnostics"]
    assert diag["output_file"] == "interface_network_trace.json"
    assert diag["network_topology"].startswith("concentric interface shells")
    assert diag["tracks"]["discrete_channel_track"]["num_samples"] == len(trace)


def test_step19_external_analysis_can_separate_translation_and_rotation_across_tracks(tmp_path: Path):
    trans_dir = tmp_path / "translation"
    rot_dir = tmp_path / "rotation"

    trans_result = run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.18,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="translation",
            vestibular_linear_accel=80.0,
            vestibular_onset_fraction=0.2,
            vestibular_duration_fraction=0.6,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=trans_dir,
        save_outputs=True,
    )
    rot_result = run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.18,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="rotation",
            vestibular_angular_accel=500.0,
            vestibular_onset_fraction=0.2,
            vestibular_duration_fraction=0.6,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=rot_dir,
        save_outputs=True,
    )

    trans_tracks = trans_result.summary["interface_network_diagnostics"]["tracks"]
    rot_tracks = rot_result.summary["interface_network_diagnostics"]["tracks"]
    for track_name in TRACKS:
        trans_active = trans_tracks[track_name]["active_summary"]["mean_global_channels"]
        rot_active = rot_tracks[track_name]["active_summary"]["mean_global_channels"]
        assert trans_active["axial_flux"] > trans_active["swirl_flux"]
        assert rot_active["swirl_flux"] > rot_active["axial_flux"]
        assert trans_tracks[track_name]["protocol_aligned_flux_margin"] > 0.0
        assert rot_tracks[track_name]["protocol_aligned_flux_margin"] > 0.0
