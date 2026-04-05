from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def _dominant(rows: list[dict], key: str) -> str:
    counts = Counter(str(row.get(key, "unknown")) for row in rows)
    return counts.most_common(1)[0][0] if counts else "none"


def test_step18_writes_mirror_interface_trace_and_summary(tmp_path: Path):
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
    trace_path = outdir / "interface_trace.json"
    assert trace_path.exists()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace
    first = trace[0]
    for key in ["aggregate_channels", "direction_vector", "interface_class", "interface_bundles", "mirror_structure"]:
        assert key in first
    assert first["mirror_structure"]["topology"] == "concentric mirror shells x directional sectors"
    assert "slow_tonic" in first["mirror_structure"]["bundle_channel_names"]
    assert len(first["interface_bundles"]) > 0
    diag = result.summary["mirror_interface_diagnostics"]
    assert diag["num_samples"] == len(trace)
    assert diag["output_file"] == "interface_trace.json"
    assert diag["dominant_interface_class"] == "static"
    assert diag["matched_channel_advantage"] > 0.05
    assert "electrical_potential" in diag["bundle_channels"]


def test_step18_unified_sphere_and_mirror_interface_separate_translation_and_rotation(tmp_path: Path):
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

    trans_trace = json.loads((trans_dir / "interface_trace.json").read_text(encoding="utf-8"))
    rot_trace = json.loads((rot_dir / "interface_trace.json").read_text(encoding="utf-8"))
    trans_active = [row for row in trans_trace if row["stimulus_active"]]
    rot_active = [row for row in rot_trace if row["stimulus_active"]]

    assert _dominant(trans_active, "interface_class") == "translation"
    assert _dominant(rot_active, "interface_class") == "rotation"

    trans_diag = trans_result.summary["mirror_interface_diagnostics"]
    rot_diag = rot_result.summary["mirror_interface_diagnostics"]
    assert trans_diag["active_summary"]["mean_translation_channel"] > trans_diag["active_summary"]["mean_rotation_channel"]
    assert rot_diag["active_summary"]["mean_rotation_channel"] > rot_diag["active_summary"]["mean_translation_channel"]
    assert trans_diag["matched_channel_advantage"] > 0.01
    assert rot_diag["matched_channel_advantage"] > 0.01
