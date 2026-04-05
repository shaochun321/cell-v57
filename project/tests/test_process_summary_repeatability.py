from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from shutil import copytree

from cell_sphere_core.analysis.process_summary_repeatability import summarize_process_summary_repeatability
from scripts.run_process_summary_repeatability_protocol import run_protocol


def _case_payload(*, mode: str, axis: str, signal_key: str = '', signal: float = 0.0) -> dict:
    active_signature = {signal_key: signal} if signal_key else {}
    return {
        'dominant_mode': mode,
        'dominant_axis': axis,
        'active_dominant_mode': mode,
        'active_dominant_axis': axis,
        'overall_scores': {mode: 0.9},
        'phase_coverage': {'baseline': 1, 'active': 2, 'recovery': 1},
        'phase_summaries': {'active': {'phase_scores': {mode: 0.9}}},
        'active_signature': active_signature,
    }


def test_summarize_process_summary_repeatability_prefers_consistent_cases() -> None:
    report = {
        'metadata': {'seeds': [7, 8]},
        'seed_runs': [
            {'seed': 7, 'analysis': {'cases': {
                'floating_static': _case_payload(mode='static_like', axis='none'),
                'translation_x_pos': _case_payload(mode='translation_like', axis='x', signal_key='mean_polarity_projection', signal=0.12),
                'translation_x_neg': _case_payload(mode='translation_like', axis='x', signal_key='mean_polarity_projection', signal=-0.14),
                'rotation_z_pos': _case_payload(mode='rotation_like', axis='z', signal_key='mean_circulation_projection', signal=0.08),
                'rotation_z_neg': _case_payload(mode='rotation_like', axis='z', signal_key='mean_circulation_projection', signal=-0.09),
            }}},
            {'seed': 8, 'analysis': {'cases': {
                'floating_static': _case_payload(mode='static_like', axis='none'),
                'translation_x_pos': _case_payload(mode='translation_like', axis='x', signal_key='mean_polarity_projection', signal=0.11),
                'translation_x_neg': _case_payload(mode='translation_like', axis='x', signal_key='mean_polarity_projection', signal=-0.13),
                'rotation_z_pos': _case_payload(mode='rotation_like', axis='z', signal_key='mean_circulation_projection', signal=0.07),
                'rotation_z_neg': _case_payload(mode='rotation_like', axis='z', signal_key='mean_circulation_projection', signal=-0.08),
            }}},
        ],
    }
    audit = summarize_process_summary_repeatability(report)
    assert audit['contracts']['passed'] is True, audit['contracts']['failures']
    assert audit['cases']['translation_x_pos']['overall_expected_fraction'] == 1.0
    assert audit['cases']['rotation_z_neg']['axis_expected_fraction'] == 1.0
    assert audit['paired_gates']['translation_polarity']['flip_fraction'] == 1.0
    assert audit['paired_gates']['rotation_circulation']['min_separation'] > 0.01


def test_run_process_summary_repeatability_protocol_reusing_existing_outputs(tmp_path: Path) -> None:
    src = Path('outputs/process_summary_atlas_protocol_r1')
    for seed in (7, 8):
        copytree(src, tmp_path / f'seed_{seed}')
    args = Namespace(
        num_cells=55,
        t_end=0.09,
        dt=0.0011,
        translation_accel=85.0,
        rotation_alpha=400.0,
        onset_fraction=0.24,
        duration_fraction=0.42,
        floating_com_damping=9.9,
        floating_internal_drag=8.7,
        radial_band_damping=7.35,
        translation_center_scale_active=0.12,
        translation_radial_scale_active=0.88,
        window_size=3,
        stride=1,
        seeds='7,8',
        outdir=str(tmp_path),
        reuse_existing=True,
    )
    payload = run_protocol(args)
    audit_path = Path(payload['audit_path'])
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    assert audit['contracts']['passed'] is True, audit['contracts']['failures']
    assert audit['cases']['translation_x_pos']['overall_expected_fraction'] == 1.0
    assert audit['cases']['rotation_z_pos']['active_expected_fraction'] == 1.0
