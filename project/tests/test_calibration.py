from pathlib import Path
import json
import subprocess
import sys



def test_calibration_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / 'calib'
    cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'calibrate_reference.py'),
        '--counts', '40,60',
        '--tension-grid', '14',
        '--pressure-grid', '700',
        '--radial-bands-grid', '3',
        '--local-pressure-grid', '70',
        '--shell-curvature-grid', '40',
        '--band-interface-grid', '16',
        '--outer-stiffness-grid', '1.4',
        '--inner-damping-grid', '1.6',
        '--outer-shear-grid', '1.5',
        '--band-damping-grid', '4.0',
        '--band-restoring-grid', '20',
        '--shell-reference-grid', '40',
        '--bulk-reference-grid', '6',
        '--gravity-ramp-grid', '0.2',
        '--settle-damping-grid', '2.4',
        '--settle-pressure-grid', '1.2',
        '--settle-shell-grid', '1.1',
        '--t-end', '0.03',
        '--dt', '0.001',
        '--outdir', str(outdir),
    ]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    best_path = outdir / 'best_config.json'
    csv_path = outdir / 'calibration_results.csv'
    assert best_path.exists()
    assert csv_path.exists()

    data = json.loads(best_path.read_text(encoding='utf-8'))
    assert data['tension_k'] == 14.0
    assert data['pressure_k'] == 700.0
    assert data['radial_bands'] == 3
    assert data['local_pressure_k'] == 70.0
    assert data['shell_curvature_k'] == 40.0
    assert data['band_interface_k'] == 16.0
    assert data['outer_stiffness_scale'] == 1.4
    assert data['inner_damping_scale'] == 1.6
    assert data['outer_shear_scale'] == 1.5
    assert data['band_damping_c'] == 4.0
    assert data['band_restoring_k'] == 20.0
    assert data['shell_reference_k'] == 40.0
    assert data['bulk_reference_k'] == 6.0
    assert data['gravity_ramp_fraction'] == 0.2
    assert data['settle_damping_boost'] == 2.4
    assert data['settle_pressure_boost'] == 1.2
    assert data['settle_shell_boost'] == 1.1
