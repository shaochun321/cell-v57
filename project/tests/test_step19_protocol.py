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


def test_run_step19_protocol_and_analyze_interface_network(tmp_path: Path):
    protocol_dir = tmp_path / "step19_protocol"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_step19_protocol.py",
            "--num-cells",
            "120",
            "--t-end",
            "0.12",
            "--outdir",
            str(protocol_dir),
        ],
        check=True,
    )
    report = json.loads((protocol_dir / "step19_protocol_report.json").read_text(encoding="utf-8"))
    for case in ["floating_static", "floating_translation", "floating_rotation"]:
        track_report = report[case]["track_report"]
        for track_name in TRACKS:
            assert track_name in track_report
    trans = report["floating_translation"]["track_report"]
    rot = report["floating_rotation"]["track_report"]
    for track_name in TRACKS:
        assert trans[track_name]["protocol_aligned_flux_margin"] > 0.0
        assert rot[track_name]["protocol_aligned_flux_margin"] > 0.0

    trace_path = protocol_dir / "floating_translation" / "interface_network_trace.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_interface_network.py",
            "--input",
            str(trace_path),
            "--title",
            "Step19 Interface Network Test",
        ],
        check=True,
    )
    assert (trace_path.parent / "interface_network_overview.png").exists()
    assert (trace_path.parent / "interface_network_analysis.json").exists()
