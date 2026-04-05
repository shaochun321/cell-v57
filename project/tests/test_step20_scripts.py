from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TRACKS = [
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
]


def test_run_step20_protocol_and_analyze_interface_constraints(tmp_path: Path):
    protocol_dir = tmp_path / "step20_protocol"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_step20_protocol.py",
            "--num-cells",
            "120",
            "--t-end",
            "0.12",
            "--outdir",
            str(protocol_dir),
        ],
        check=True,
    )
    report = json.loads((protocol_dir / "step20_protocol_report.json").read_text(encoding="utf-8"))
    for case in ["floating_static", "translation_x_pos", "translation_x_neg", "rotation_z_pos", "rotation_z_neg"]:
        assert case in report
        for track_name in TRACKS:
            assert track_name in report[case]["track_report"]

    for track_name in TRACKS:
        assert report["translation_x_pos"]["track_report"][track_name]["axis_balance"]["x"] < 0.0
        assert report["translation_x_neg"]["track_report"][track_name]["axis_balance"]["x"] > 0.0
        assert report["rotation_z_pos"]["track_report"][track_name]["signed_circulation"] > 0.0002
        assert report["rotation_z_neg"]["track_report"][track_name]["signed_circulation"] < -0.0002

    trace_path = protocol_dir / "translation_x_pos" / "interface_network_trace.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_interface_constraints.py",
            "--input",
            str(trace_path),
            "--title",
            "Step20 Interface Constraint Test",
        ],
        check=True,
    )
    assert (trace_path.parent / "interface_constraint_overview.png").exists()
    assert (trace_path.parent / "interface_constraint_analysis.json").exists()
