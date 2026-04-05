from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys


def test_run_phase_r2_protocol_and_analyze(tmp_path: Path):
    outdir = tmp_path / 'phase_r2_case'
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str(tmp_path / '.mplconfig'))
    env['PYTHONPATH'] = str(Path.cwd() / 'src') + os.pathsep + env.get('PYTHONPATH', '')

    subprocess.run(
        [
            sys.executable,
            'scripts/run_phase_r2_protocol.py',
            '--num-cells', '40',
            '--t-end', '0.05',
            '--dt', '0.001',
            '--rotation-alphas', '460,520',
            '--swirl-gains', '1.00,1.20',
            '--outdir', str(outdir),
        ],
        check=True,
        env=env,
    )
    report_path = outdir / 'phase_r2_protocol_report.json'
    audit_path = outdir / 'phase_r2_audit.json'
    assert report_path.exists()
    assert audit_path.exists()

    analysis_dir = outdir / 'analysis'
    subprocess.run(
        [
            sys.executable,
            'scripts/analyze_phase_r2_audit.py',
            '--input', str(audit_path),
            '--title', 'Phase R.2 audit',
            '--output', str(analysis_dir),
        ],
        check=True,
        env=env,
    )
    analysis_json = analysis_dir / 'phase_r2_analysis.json'
    png = analysis_dir / 'phase_r2_sensitivity_map.png'
    local_png = analysis_dir / 'phase_r2_local_robustness.png'
    assert analysis_json.exists()
    assert png.exists()
    assert local_png.exists()
    payload = json.loads(analysis_json.read_text(encoding='utf-8'))
    assert payload['overall']['num_scan_points'] == 4
    assert payload['best_config']['rotation_score'] >= payload['worst_config']['rotation_score']
    assert 'local_robustness' in payload
