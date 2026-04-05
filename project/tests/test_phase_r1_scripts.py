from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys


def test_run_phase_r1_protocol_and_analyze(tmp_path: Path):
    outdir = tmp_path / 'phase_r1_case'
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str(tmp_path / '.mplconfig'))
    env['PYTHONPATH'] = str(Path.cwd() / 'src') + os.pathsep + env.get('PYTHONPATH', '')

    subprocess.run(
        [
            sys.executable,
            'scripts/run_phase_r1_protocol.py',
            '--num-cells', '60',
            '--t-end', '0.08',
            '--dt', '0.001',
            '--outdir', str(outdir),
        ],
        check=True,
        env=env,
    )
    protocol_path = outdir / 'phase_r1_protocol_report.json'
    audit_path = outdir / 'phase_r1_audit.json'
    assert protocol_path.exists()
    assert audit_path.exists()

    analysis_dir = outdir / 'analysis'
    subprocess.run(
        [
            sys.executable,
            'scripts/analyze_phase_r1_audit.py',
            '--input', str(audit_path),
            '--title', 'Phase R.1 audit',
            '--output', str(analysis_dir),
        ],
        check=True,
        env=env,
    )
    analysis_json = analysis_dir / 'phase_r1_analysis.json'
    overview_png = analysis_dir / 'phase_r1_overview.png'
    assert analysis_json.exists()
    assert overview_png.exists()
    payload = json.loads(analysis_json.read_text(encoding='utf-8'))
    assert payload['repair_status']['layered_best_rotation_track'] is True
