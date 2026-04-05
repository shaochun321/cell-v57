from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_step15_protocol_and_analysis_scripts_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    protocol_dir = tmp_path / "protocol"
    run_cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_step15_protocol.py"),
        "--num-cells", "120",
        "--t-end", "0.12",
        "--dt", "0.001",
        "--outdir", str(protocol_dir),
    ]
    proc = subprocess.run(run_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    report_path = protocol_dir / "step15_protocol_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["floating_translation"]["process_state"]["active_summary"]["dominant_motion_class"] == "translation"
    assert report["floating_rotation"]["process_state"]["active_summary"]["dominant_motion_class"] == "rotation"

    input_path = protocol_dir / "floating_translation" / "motion_state_trace.json"
    analyze_cmd = [
        sys.executable,
        str(project_root / "scripts" / "analyze_process_state.py"),
        "--input", str(input_path),
        "--title", "Step15 smoke",
    ]
    proc = subprocess.run(analyze_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    out_json = input_path.parent / "motion_state_trace_summary.json"
    assert out_json.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["active_summary"]["dominant_motion_class"] == "translation"
