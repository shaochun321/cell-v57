from pathlib import Path
import json
import subprocess
import sys


def test_run_gravity_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / 'out'
    cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'run_gravity.py'),
        '--num-cells', '120',
        '--t-end', '0.05',
        '--dt', '0.001',
        '--outdir', str(outdir),
    ]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    summary_path = outdir / 'gravity_N120' / 'summary.json'
    metrics_path = outdir / 'gravity_N120' / 'metrics.png'
    final_path = outdir / 'gravity_N120' / 'final_state.png'
    assert summary_path.exists()
    assert metrics_path.exists()
    assert final_path.exists()

    data = json.loads(summary_path.read_text(encoding='utf-8'))
    assert data['experiment'] == 'gravity'
    assert data['num_cells'] == 120
    assert data['foam_tissue_enabled'] is True
