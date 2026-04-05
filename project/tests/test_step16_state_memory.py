from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def _dominant(rows: list[dict], key: str) -> str:
    counts = Counter(str(row.get(key, "unknown")) for row in rows)
    return counts.most_common(1)[0][0] if counts else "none"


def test_step16_translation_pulse_recovers_to_recovered_static(tmp_path: Path):
    outdir = tmp_path / "pulse_translation"
    result = run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.24,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="translation",
            vestibular_linear_accel=80.0,
            vestibular_onset_fraction=0.25,
            vestibular_duration_fraction=0.25,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=outdir,
        save_outputs=True,
    )
    trace = json.loads((outdir / "motion_state_trace.json").read_text(encoding="utf-8"))
    active_rows = [row for row in trace if row["stimulus_active"]]
    post_rows = [row for row in trace if row["time"] >= max(r["time"] for r in active_rows)]

    assert _dominant(active_rows, "motion_class") == "translation"
    assert any(row["transition_state"] == "recovered_static" for row in post_rows)

    diag = result.summary["state_memory_diagnostics"]
    assert diag["activation_events"] == 1
    assert diag["deactivation_events"] == 1
    assert diag["recovered_after_last_offset"] is True
    assert diag["last_stimulus_class"] == "translation"
    assert diag["time_to_first_recovered_static"] is not None


def test_step16_rotation_pulse_keeps_memory_trace_after_offset(tmp_path: Path):
    outdir = tmp_path / "pulse_rotation"
    result = run_gravity(
        GravityConfig(
            num_cells=120,
            t_end=0.24,
            dt=0.001,
            disable_gravity=True,
            vestibular_motion="rotation",
            vestibular_angular_accel=500.0,
            vestibular_onset_fraction=0.25,
            vestibular_duration_fraction=0.25,
            sensor_record_every=10,
            record_every=10,
        ),
        outdir=outdir,
        save_outputs=True,
    )
    trace = json.loads((outdir / "motion_state_trace.json").read_text(encoding="utf-8"))
    active_rows = [row for row in trace if row["stimulus_active"]]
    recovery_rows = [row for row in trace if row["transition_state"] in {"recovery", "post_stimulus_drift", "recovered_static"}]

    assert _dominant(active_rows, "motion_class") == "rotation"
    assert recovery_rows
    assert max(float(row["memory_trace_strength"]) for row in recovery_rows) > 0.20
    assert float(recovery_rows[-1]["recovery_index"]) > 0.45

    diag = result.summary["state_memory_diagnostics"]
    assert diag["activation_events"] == 1
    assert diag["deactivation_events"] == 1
    assert diag["last_stimulus_class"] == "rotation"
