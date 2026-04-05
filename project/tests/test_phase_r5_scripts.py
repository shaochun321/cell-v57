from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_phase_r5_and_analyze(tmp_path: Path) -> None:
    env = dict(os.environ)
    env['PYTHONPATH'] = 'src'
    env.setdefault('MPLCONFIGDIR', str((tmp_path / '.mplconfig').resolve()))
    outdir = tmp_path / 'phase_r5'
    subprocess.run([
        sys.executable, 'scripts/run_phase_r5_protocol.py',
        '--num-cells', '24', '--t-end', '0.03', '--dt', '0.002',
        '--rotation-alphas', '300,320', '--swirl-gains', '1.05,1.10', '--seeds', '7,8',
        '--outdir', str(outdir),
    ], check=True, cwd=Path.cwd(), env=env)
    audit_path = outdir / 'phase_r5_audit.json'
    assert audit_path.exists()
    payload = json.loads(audit_path.read_text(encoding='utf-8'))
    assert 'local_repeatability_plateau' in payload
    analysis_dir = outdir / 'analysis'
    subprocess.run([
        sys.executable, 'scripts/analyze_phase_r5_audit.py',
        '--input', str(audit_path), '--output', str(analysis_dir),
    ], check=True, cwd=Path.cwd(), env=env)
    assert (analysis_dir / 'phase_r5_analysis.json').exists()
