from pathlib import Path
import json
import subprocess
import sys



def test_run_gravity_with_tissue_smoke(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    outdir = tmp_path / 'out'
    cmd = [
        sys.executable,
        str(project_root / 'scripts' / 'run_gravity.py'),
        '--num-cells', '120',
        '--t-end', '0.05',
        '--dt', '0.001',
        '--tissue-radial-bands', '4',
        '--tissue-band-interface-k', '20',
        '--tissue-outer-stiffness-scale', '1.4',
        '--tissue-inner-damping-scale', '1.6',
        '--tissue-outer-shear-scale', '1.5',
        '--tissue-band-damping-c', '4.0',
        '--outdir', str(outdir),
    ]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    summary_path = outdir / 'gravity_N120' / 'summary.json'
    assert summary_path.exists()
    data = json.loads(summary_path.read_text(encoding='utf-8'))
    assert data['experiment'] == 'gravity'
    assert data['num_cells'] == 120
    assert data['tissue_enabled'] is True
    assert data['foam_tissue_enabled'] is True
    assert 'pressure_delta_ratio' in data
    assert 'tissue_config' in data
    assert data['tissue_config']['radial_bands'] == 4
    assert data['tissue_reference']['effective_radial_bands'] >= 2
    assert len(data['tissue_reference']['radial_band_counts']) == data['tissue_reference']['effective_radial_bands']
    assert 'material_profile' in data
    assert len(data['material_profile']['stiffness_scale_by_band']) == data['tissue_reference']['effective_radial_bands']
    assert 'local_proxy_diagnostics' in data
    assert data['local_proxy_diagnostics']['proxy_model'] == 'volume_density_proxy'

    assert 'equilibrium_diagnostics' in data
    assert 'settling_schedule' in data
    assert 'band_restoring_k' in data['tissue_config']
    assert 'shell_reference_k' in data['tissue_config']
