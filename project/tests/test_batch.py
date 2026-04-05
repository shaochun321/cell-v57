from pathlib import Path
import json
import subprocess
import sys


def test_reference_batch_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / 'batch'
    cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'run_reference_batch.py'),
        '--counts', '40,60',
        '--t-end', '0.03',
        '--dt', '0.001',
        '--outdir', str(outdir),
    ]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    summary_path = outdir / 'batch_summary.json'
    plot_path = outdir / 'batch_metrics.png'
    assert summary_path.exists()
    assert plot_path.exists()

    data = json.loads(summary_path.read_text(encoding='utf-8'))
    assert len(data) == 2
    assert data[0]['num_cells'] == 40
    assert 'near_sphere_score' in data[0]
    assert 'mean_local_volume_ratio' in data[0]
    assert 'mean_local_density_ratio' in data[0]
    assert 'tail_kinetic_mean' in data[0]
    assert 'quasi_static' in data[0]
