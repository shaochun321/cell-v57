from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_step17_protocol_and_analyze_readout(tmp_path: Path):
    protocol_dir = tmp_path / "step17_protocol"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_step17_protocol.py",
            "--num-cells",
            "120",
            "--t-end",
            "0.12",
            "--outdir",
            str(protocol_dir),
        ],
        check=True,
    )
    report = json.loads((protocol_dir / "step17_protocol_report.json").read_text(encoding="utf-8"))
    assert report["floating_static"]["readout_summary"]["dominant_readout_class"] == "static"
    assert report["floating_translation"]["readout_summary"]["active_summary"]["dominant_readout_class"] == "translation"
    assert report["floating_rotation"]["readout_summary"]["active_summary"]["dominant_readout_class"] == "rotation"

    readout_path = protocol_dir / "floating_translation" / "readout_trace.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_readout.py",
            "--input",
            str(readout_path),
            "--title",
            "Step17 Readout Test",
        ],
        check=True,
    )
    assert (readout_path.parent / "readout_trace_channels.png").exists()
    assert (readout_path.parent / "readout_trace_summary.json").exists()
