from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_step26_protocol_and_analyze_channel_motifs(tmp_path: Path):
    outdir = tmp_path / "step26_protocol"
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    env.setdefault("MPLCONFIGDIR", str(tmp_path / ".mplconfig"))
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_step26_protocol.py"), "--num-cells", "120", "--t-end", "0.18", "--dt", "0.001", "--outdir", str(outdir)], check=True, cwd=ROOT, env=env)
    report = json.loads((outdir / "step26_protocol_report.json").read_text(encoding="utf-8"))
    assert "translation_x_pos" in report and "rotation_z_pos" in report
    subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze_channel_motifs.py"), "--input", str(outdir / "translation_x_pos" / "channel_motif_trace.json"), "--title", "Step 26 channel motif analysis test", "--output", str(outdir / "analysis_translation_x_pos")], check=True, cwd=ROOT, env=env)
    analysis = json.loads((outdir / "analysis_translation_x_pos" / "channel_motif_analysis.json").read_text(encoding="utf-8"))
    for payload in analysis["external_interpretation"].values():
        assert payload["axial_path_motif_count"] >= payload["swirl_loop_motif_count"]
        assert payload["x_axis_balance"] > 0.0
        assert payload["stable_substructure_count"] >= 1
