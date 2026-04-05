from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_step27_protocol_and_analyze_channel_invariants(tmp_path: Path):
    outdir = tmp_path / "step27_protocol"
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    env.setdefault("MPLCONFIGDIR", str(tmp_path / ".mplconfig"))
    subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "run_step27_protocol.py"),
        "--num-cells", "70",
        "--t-end", "0.08",
        "--dt", "0.001",
        "--outdir", str(outdir),
    ], check=True, cwd=ROOT, env=env)
    protocol = json.loads((outdir / "step27_protocol_report.json").read_text(encoding="utf-8"))
    invariants = json.loads((outdir / "step27_invariants.json").read_text(encoding="utf-8"))
    assert "translation_x_pos_base" in protocol and "rotation_z_neg_soft" in protocol
    subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "analyze_channel_invariants.py"),
        "--input", str(outdir / "step27_protocol_report.json"),
        "--title", "Step 27 channel invariant analysis test",
        "--output", str(outdir / "analysis_step27"),
    ], check=True, cwd=ROOT, env=env)
    analysis = json.loads((outdir / "analysis_step27" / "channel_invariant_analysis.json").read_text(encoding="utf-8"))
    for payload in analysis["external_readout"].values():
        assert payload["translation_axial_consistency"] >= 0.75
        assert payload["rotation_swirl_consistency"] >= 0.5
        assert payload["translation_sign_consistency"] >= 0.75
        assert payload["rotation_sign_consistency"] >= 0.5
    assert invariants["principle"].startswith("cross-protocol and cross-parameter motif stability audit")
