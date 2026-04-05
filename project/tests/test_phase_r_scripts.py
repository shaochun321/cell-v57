from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


def test_run_phase_r_protocol_and_analyze(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / 'phase_r'
    run_cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'run_phase_r_protocol.py'),
        '--num-cells', '80',
        '--t-end', '0.08',
        '--dt', '0.001',
        '--outdir', str(outdir),
    ]
    proc = subprocess.run(run_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    audit_path = outdir / 'phase_r_audit.json'
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    assert 'overall' in audit
    analyze_cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'analyze_phase_r_audit.py'),
        '--input', str(audit_path),
        '--output', str(outdir / 'analysis'),
    ]
    proc = subprocess.run(analyze_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (outdir / 'analysis' / 'phase_r_analysis.json').exists()
    assert (outdir / 'analysis' / 'phase_r_overview.png').exists()
