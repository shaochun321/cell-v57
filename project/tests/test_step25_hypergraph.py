from __future__ import annotations

import json
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity

TRACKS = ["discrete_channel_track", "local_propagation_track", "layered_coupling_track"]


def _run_case(tmp_path: Path, name: str, **kwargs):
    return run_gravity(GravityConfig(num_cells=120, t_end=0.18, dt=0.001, disable_gravity=True, sensor_record_every=10, record_every=10, vestibular_onset_fraction=0.2, vestibular_duration_fraction=0.6, **kwargs), outdir=tmp_path / name, save_outputs=True)


def test_step25_trace_contains_hypergraph_payload_and_output_file(tmp_path: Path):
    result = _run_case(tmp_path, "translation_x_pos", vestibular_motion="translation", vestibular_linear_accel=80.0, vestibular_linear_axis="x", vestibular_linear_sign=1.0)
    trace = json.loads((tmp_path / "translation_x_pos" / "channel_hypergraph_trace.json").read_text(encoding="utf-8"))
    first = trace[0]
    assert "hypergraph_structure" in first
    for track_name in TRACKS:
        payload = first["tracks"][track_name]
        assert "nodes" in payload and "edges" in payload and "hyperedges" in payload
        assert any(edge["kind"] == "track_to_family" for edge in payload["edges"])
        assert any(h["kind"] == "family_shell_path" for h in payload["hyperedges"])
    assert result.summary["channel_hypergraph_diagnostics"]["output_file"] == "channel_hypergraph_trace.json"


def test_step25_hypergraph_summary_preserves_translation_rotation_and_signs(tmp_path: Path):
    trans_pos = _run_case(tmp_path, "translation_x_pos", vestibular_motion="translation", vestibular_linear_accel=80.0, vestibular_linear_axis="x", vestibular_linear_sign=1.0)
    trans_neg = _run_case(tmp_path, "translation_x_neg", vestibular_motion="translation", vestibular_linear_accel=80.0, vestibular_linear_axis="x", vestibular_linear_sign=-1.0)
    rot_pos = _run_case(tmp_path, "rotation_z_pos", vestibular_motion="rotation", vestibular_angular_accel=500.0, vestibular_rotation_axis="z", vestibular_rotation_sign=1.0)
    rot_neg = _run_case(tmp_path, "rotation_z_neg", vestibular_motion="rotation", vestibular_angular_accel=500.0, vestibular_rotation_axis="z", vestibular_rotation_sign=-1.0)
    for track_name in TRACKS:
        trans = trans_pos.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]
        rot = rot_pos.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]
        assert trans["active_family_means"]["axial_polar_family"] > trans["active_family_means"]["swirl_circulation_family"]
        assert rot["active_family_means"]["swirl_circulation_family"] > rot["active_family_means"]["axial_polar_family"]
        assert trans_pos.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]["active_axis_balance"]["x"] > 0.01
        assert trans_neg.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]["active_axis_balance"]["x"] < -0.01
        assert rot_pos.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]["active_signed_circulation"] > 0.001
        assert rot_neg.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]["active_signed_circulation"] < -0.001


def test_step25_hypergraph_has_nontrivial_nodes_edges_and_hyperedges(tmp_path: Path):
    result = _run_case(tmp_path, "rotation_z_pos", vestibular_motion="rotation", vestibular_angular_accel=500.0, vestibular_rotation_axis="z", vestibular_rotation_sign=1.0)
    for track_name in TRACKS:
        diag = result.summary["channel_hypergraph_diagnostics"]["tracks"][track_name]
        assert diag["mean_node_count"] > 10.0
        assert diag["mean_edge_count"] > 10.0
        assert diag["mean_hyperedge_count"] >= 4.0
