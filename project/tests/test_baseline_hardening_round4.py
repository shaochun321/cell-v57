from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests._assertions import assert_margin, assert_sign_flip


TRACKS = ('discrete_channel_track', 'local_propagation_track', 'layered_coupling_track')


def test_run_and_analyze_baseline_hardening_round4(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str((tmp_path / '.mplconfig').resolve()))
    env['PYTHONPATH'] = str(Path.cwd() / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    outdir = tmp_path / 'hardening4'

    subprocess.run([
        sys.executable, 'scripts/run_baseline_hardening_round4.py',
        '--num-cells', '55', '--t-end', '0.09', '--dt', '0.0011',
        '--translation-accel', '85', '--rotation-alpha', '400',
        '--outdir', str(outdir),
    ], check=True, env=env)

    report_path = outdir / 'baseline_hardening_round4_report.json'
    assert report_path.exists()

    subprocess.run([
        sys.executable, 'scripts/analyze_baseline_hardening_round4.py',
        '--input', str(report_path), '--output', str(outdir / 'analysis')
    ], check=True, env=env)

    analysis_path = outdir / 'analysis' / 'baseline_hardening_round4_analysis.json'
    png_path = outdir / 'analysis' / 'baseline_hardening_round4_overview.png'
    assert analysis_path.exists()
    assert png_path.exists()

    payload = json.loads(analysis_path.read_text(encoding='utf-8'))
    assert_margin(payload['static']['quietness_score'], eps=0.700, label='round4 static quietness')
    assert payload['static']['tail_kinetic_mean'] < 0.43, payload['static']['tail_kinetic_mean']
    assert_margin(payload['static']['shape_score'], eps=0.70, label='round4 static shape score')

    for track in TRACKS:
        t = payload['translation']['tracks'][track]
        r = payload['rotation']['tracks'][track]
        assert_sign_flip(t['x_axis_balance_pos'], t['x_axis_balance_neg'], min_abs=0.0025, min_sep=0.004, label=f'{track} translation x-balance')
        assert_margin(t['x_axis_balance_abs_mean'], eps=0.008, label=f'{track} translation amplitude')
        assert_margin(t['mean_translation_margin'], eps=0.09, label=f'{track} translation margin')
        assert_sign_flip(r['signed_circulation_pos'], r['signed_circulation_neg'], min_abs=0.006, min_sep=0.012, label=f'{track} rotation circulation')
        assert_margin(r['signed_circulation_abs_mean'], eps=0.015, label=f'{track} rotation amplitude')
        assert_margin(r['mean_rotation_margin'], eps=0.08, label=f'{track} rotation margin')
