from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_step16_protocol_and_analysis_scripts_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    protocol_dir = tmp_path / "protocol"
    run_cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_step16_protocol.py"),
        "--num-cells", "120",
        "--t-end", "0.24",
        "--dt", "0.001",
        "--outdir", str(protocol_dir),
    ]
    proc = subprocess.run(run_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    report_path = protocol_dir / "step16_protocol_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["pulse_translation"]["process_state"]["active_summary"]["dominant_motion_class"] == "translation"
    assert report["pulse_translation"]["state_memory"]["recovered_after_last_offset"] is True
    assert report["pulse_rotation"]["process_state"]["active_summary"]["dominant_motion_class"] == "rotation"
    assert report["pulse_rotation"]["state_memory"]["activation_events"] == 1

    input_path = protocol_dir / "pulse_translation" / "motion_state_trace.json"
    analyze_cmd = [
        sys.executable,
        str(project_root / "scripts" / "analyze_state_memory.py"),
        "--input", str(input_path),
        "--title", "Step16 smoke",
    ]
    proc = subprocess.run(analyze_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    out_json = input_path.parent / "motion_state_trace_transition_summary.json"
    out_img = input_path.parent / "motion_state_trace_transition_memory.png"
    assert out_json.exists()
    assert out_img.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["recovered_after_last_offset"] is True
