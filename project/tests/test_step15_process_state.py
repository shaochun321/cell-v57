from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def _dominant(rows: list[dict]) -> str:
    counts = Counter(row["motion_class"] for row in rows)
    return counts.most_common(1)[0][0] if counts else "none"


def test_step15_writes_motion_state_trace_and_summary(tmp_path: Path):
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
    motion_path = outdir / "motion_state_trace.json"
    assert motion_path.exists()
    trace = json.loads(motion_path.read_text(encoding="utf-8"))
    assert len(trace) >= 1
    first = trace[0]
    for key in [
        "force_magnitude_index",
        "static_index",
        "motion_index",
        "dipole_ratio",
        "quadrupole_ratio",
        "motion_class",
        "phase",
    ]:
        assert key in first
    diag = result.summary["process_state_diagnostics"]
    assert diag["num_samples"] == len(trace)
    assert diag["output_file"] == "motion_state_trace.json"
    assert _dominant(trace) == "static"


def test_step15_translation_and_rotation_dominate_different_classes(tmp_path: Path):
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

    trans_trace = json.loads((trans_dir / "motion_state_trace.json").read_text(encoding="utf-8"))
    rot_trace = json.loads((rot_dir / "motion_state_trace.json").read_text(encoding="utf-8"))
    trans_active = [row for row in trans_trace if row["stimulus_active"]]
    rot_active = [row for row in rot_trace if row["stimulus_active"]]

    assert _dominant(trans_active) == "translation"
    assert _dominant(rot_active) == "rotation"
