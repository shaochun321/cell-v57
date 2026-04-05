from __future__ import annotations

from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from cell_sphere_core.analysis.multipole import load_sensor_nodes_jsonl, analyze_sensor_frames, summarize_energy_series


def test_step14_writes_node_level_sensor_frames(tmp_path: Path):
    outdir = tmp_path / "floating_static"
    run_gravity(
        GravityConfig(
            num_cells=64,
            t_end=0.05,
            dt=0.001,
            disable_gravity=True,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=outdir,
        save_outputs=True,
    )
    trace_path = outdir / "sensor_trace.json"
    nodes_path = outdir / "sensor_nodes.jsonl"
    assert trace_path.exists()
    assert nodes_path.exists()

    frames = load_sensor_nodes_jsonl(nodes_path)
    assert len(frames) >= 1
    first = frames[0]
    assert "reference_frame" in first
    assert "layers" in first
    assert len(first["layers"]) >= 1
    outer = first["layers"][-1]
    assert outer["node_count"] >= 1
    node = outer["nodes"][0]
    for key in ["pos_abs", "pos_rel", "u_r", "v_r", "accel_r", "force_density", "gate"]:
        assert key in node


def test_step14_floating_static_stays_off_floor(tmp_path: Path):
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
    final = result.summary["final_metrics"]
    assert final["floor_contact_ratio"] == 0.0
    assert result.summary["sensor_diagnostics"]["node_frame_samples"] >= 1
    assert (outdir / "sensor_nodes.jsonl").exists()


def test_step14_translation_and_rotation_have_distinct_multipole_signatures(tmp_path: Path):
    trans_dir = tmp_path / "translation"
    rot_dir = tmp_path / "rotation"
    run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.12,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="translation",
            vestibular_linear_accel=80.0,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=trans_dir,
        save_outputs=True,
    )
    run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.12,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="rotation",
            vestibular_angular_accel=500.0,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=rot_dir,
        save_outputs=True,
    )

    trans_frames = [fr for fr in load_sensor_nodes_jsonl(trans_dir / "sensor_nodes.jsonl") if fr.get("stimulus", {}).get("active")]
    rot_frames = [fr for fr in load_sensor_nodes_jsonl(rot_dir / "sensor_nodes.jsonl") if fr.get("stimulus", {}).get("active")]

    trans_summary = summarize_energy_series(analyze_sensor_frames(trans_frames, band="outer", field_name="v_r"))
    rot_summary = summarize_energy_series(analyze_sensor_frames(rot_frames, band="outer", field_name="v_r"))

    assert trans_summary["l1_over_l2"] > 1.1
    assert rot_summary["l2_over_l1"] > 2.0
