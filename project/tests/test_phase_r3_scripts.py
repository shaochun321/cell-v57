from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_run_phase_r3_protocol_and_analyze(tmp_path: Path):
    outdir = tmp_path / 'phase_r3_case'
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str(tmp_path / '.mplconfig'))
    env['PYTHONPATH'] = str(Path.cwd() / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    subprocess.run(
        [
            sys.executable,
            'scripts/run_phase_r3_protocol.py',
            '--num-cells', '36',
            '--t-end', '0.045',
            '--dt', '0.001',
            '--rotation-alphas', '420,460',
            '--swirl-gains', '1.10,1.20',
            '--outdir', str(outdir),
        ],
        check=True,
        env=env,
    )
    audit_path = outdir / 'phase_r3_audit.json'
    assert audit_path.exists()
    analysis_dir = outdir / 'analysis'
    subprocess.run(
        [
            sys.executable,
            'scripts/analyze_phase_r3_audit.py',
            '--input', str(audit_path),
            '--title', 'Phase R.3 audit',
            '--output', str(analysis_dir),
        ],
        check=True,
        env=env,
    )
    payload = json.loads((analysis_dir / 'phase_r3_analysis.json').read_text(encoding='utf-8'))
    assert payload['overall']['num_scan_points'] == 4
    assert 'closure' in payload
    assert (analysis_dir / 'phase_r3_closure_map.png').exists()
    assert (analysis_dir / 'phase_r3_closure_summary.png').exists()
