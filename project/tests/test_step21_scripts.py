from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_step21_protocol_and_analyze_interface_lineages(tmp_path: Path):
    outdir = tmp_path / "step21_protocol"
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    env.setdefault("MPLCONFIGDIR", str(tmp_path / ".mplconfig"))

    run_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_step21_protocol.py"),
        "--num-cells",
        "120",
        "--t-end",
        "0.18",
        "--dt",
        "0.001",
        "--outdir",
        str(outdir),
    ]
    subprocess.run(run_cmd, check=True, cwd=ROOT, env=env)

    report_path = outdir / "step21_protocol_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "translation_x_pos" in report
    assert "rotation_z_pos" in report

    analyze_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "analyze_interface_lineages.py"),
        "--input",
        str(outdir / "translation_x_pos" / "interface_lineage_trace.json"),
        "--title",
        "Step 21 lineage analysis test",
        "--output",
        str(outdir / "analysis_translation_x_pos"),
    ]
    subprocess.run(analyze_cmd, check=True, cwd=ROOT, env=env)

    analysis_path = outdir / "analysis_translation_x_pos" / "interface_lineage_analysis.json"
    assert analysis_path.exists()
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    for track_name, payload in analysis["external_interpretation"].items():
        assert payload["axial_minus_swirl_family"] > 0.0
        assert payload["x_axis_family_balance"] < 0.0
