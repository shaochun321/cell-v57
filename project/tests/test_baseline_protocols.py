from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests._assertions import assert_margin, assert_sign_flip, assert_flip_or_one_sided


def test_run_and_analyze_baseline_protocols(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str((tmp_path / '.mplconfig').resolve()))
    env['PYTHONPATH'] = str(Path.cwd() / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    outdir = tmp_path / 'baseline'
    subprocess.run([
        sys.executable, 'scripts/run_baseline_protocols.py',
        '--num-cells', '36', '--t-end', '0.05', '--dt', '0.0015',
        '--translation-accel', '70', '--rotation-alpha', '360',
        '--onset-fraction', '0.25', '--duration-fraction', '0.40',
        '--outdir', str(outdir),
    ], check=True, env=env)
    report_path = outdir / 'baseline_protocol_report.json'
    assert report_path.exists()
    subprocess.run([
        sys.executable, 'scripts/analyze_baseline_protocols.py',
        '--input', str(report_path), '--output', str(outdir / 'analysis')
    ], check=True, env=env)
    analysis_path = outdir / 'analysis' / 'baseline_protocol_analysis.json'
    png_path = outdir / 'analysis' / 'baseline_protocol_overview.png'
    assert analysis_path.exists()
    assert png_path.exists()

    payload = json.loads(analysis_path.read_text(encoding='utf-8'))
    assert 'static' in payload and 'translation' in payload and 'rotation' in payload
    for track in ('discrete_channel_track', 'local_propagation_track', 'layered_coupling_track'):
        t = payload['translation']['tracks'][track]
        r = payload['rotation']['tracks'][track]
        assert_margin(r['mean_rotation_margin'], eps=1e-4, label=f'{track} rotation margin')
        assert_margin(t['x_axis_balance_abs_mean'], eps=1e-4, label=f'{track} x-balance amplitude')
        assert abs(t['x_axis_balance_pos'] - t['x_axis_balance_neg']) > 1e-5, f'{track} x-balance separation too small'
        if t['sign_flip']:
            assert_sign_flip(t['x_axis_balance_pos'], t['x_axis_balance_neg'], min_abs=1e-5, min_sep=1e-5, label=f'{track} x-balance')
        else:
            assert_flip_or_one_sided(t['x_axis_balance_pos'], t['x_axis_balance_neg'], min_abs=1e-4, near_zero=0.015, min_sep=0.007, label=f'{track} x-balance bias')
        assert_sign_flip(r['signed_circulation_pos'], r['signed_circulation_neg'], min_abs=1e-5, min_sep=1e-5, label=f'{track} z-circulation')
        assert_margin(r['signed_circulation_abs_mean'], eps=1e-4, label=f'{track} circulation amplitude')
