from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_step18_protocol_and_analyze_interface(tmp_path: Path):
    protocol_dir = tmp_path / "step18_protocol"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_step18_protocol.py",
            "--num-cells",
            "120",
            "--t-end",
            "0.12",
            "--outdir",
            str(protocol_dir),
        ],
        check=True,
    )
    report = json.loads((protocol_dir / "step18_protocol_report.json").read_text(encoding="utf-8"))
    assert report["floating_static"]["mirror_interface_summary"]["dominant_interface_class"] == "static"
    assert report["floating_translation"]["mirror_interface_summary"]["active_summary"]["dominant_interface_class"] == "translation"
    assert report["floating_rotation"]["mirror_interface_summary"]["active_summary"]["dominant_interface_class"] == "rotation"

    interface_path = protocol_dir / "floating_translation" / "interface_trace.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_interface.py",
            "--input",
            str(interface_path),
            "--title",
            "Step18 Interface Test",
        ],
        check=True,
    )
    assert (interface_path.parent / "interface_trace_overview.png").exists()
    assert (interface_path.parent / "interface_trace_summary.json").exists()
