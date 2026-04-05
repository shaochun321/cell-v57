from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_analyze_multipole_script_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    protocol_dir = tmp_path / "protocol"
    run_cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_step14_protocol.py"),
        "--num-cells", "120",
        "--t-end", "0.12",
        "--dt", "0.001",
        "--outdir", str(protocol_dir),
    ]
    proc = subprocess.run(run_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    input_path = protocol_dir / "floating_translation" / "sensor_nodes.jsonl"
    analyze_cmd = [
        sys.executable,
        str(project_root / "scripts" / "analyze_multipole.py"),
        "--input", str(input_path),
        "--field", "v_r",
        "--band", "outer",
        "--title", "Step14 smoke",
    ]
    proc = subprocess.run(analyze_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    out_json = input_path.parent / "sensor_nodes_v_r_band-outer_multipole.json"
    assert out_json.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["active_summary"]["l1_over_l2"] > 1.1
