from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from cell_sphere_core.analysis.mirror_channel_atlas import (
    build_mirror_channel_atlas_trace,
    summarize_mirror_channel_atlas_trace,
)
from cell_sphere_core.analysis.mirror_channel_atlas_contract import validate_mirror_channel_atlas_analysis
from cell_sphere_core.analysis.mirror_shell_interface import build_mirror_shell_interface_trace
from cell_sphere_core.analysis.process_calculator import build_process_calculator_trace
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from scripts.analyze_mirror_channel_atlas import analyze_report_file
from scripts.run_mirror_channel_atlas_protocol import run_protocol
from tests._assertions import assert_case_mode, assert_phase_coverage, assert_required_keys, assert_sign_flip

REQUIRED_CASE_KEYS = (
    'dominant_mode',
    'dominant_axis',
    'dominant_phase',
    'phase_counts',
    'phase_dominant_modes',
    'active_dominant_mode',
    'active_dominant_axis',
    'mean_pair_strength',
    'strongest_pair',
)


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def test_mirror_channel_atlas_trace_builds_pairwise_multichannel_windows(tmp_path: Path) -> None:
    common = dict(
        num_cells=55,
        t_end=0.09,
        dt=0.0011,
        disable_gravity=True,
        sensor_record_every=8,
        record_every=8,
        vestibular_onset_fraction=0.24,
        vestibular_duration_fraction=0.42,
        floating_support_center_k=22.0,
        floating_support_com_damping_c=9.9,
        floating_support_radial_k=34.0,
        floating_support_radial_shell_bias=0.70,
        floating_support_internal_drag_c=8.7,
        floating_support_center_scale_active=0.12,
        floating_support_radial_scale_active=0.88,
        tissue_inner_damping_scale=1.75,
        tissue_outer_damping_scale=0.82,
        tissue_outer_shear_scale=1.60,
        tissue_band_radial_damping_c=7.35,
        tissue_band_tangential_damping_c=2.0,
        tissue_radial_rate_damping_c=3.6,
        tissue_shell_tangential_damping_c=1.6,
        tissue_shell_neighbor_support_k=12.0,
    )
    outdir = tmp_path / 'translation'
    trans_kwargs = dict(common)
    trans_kwargs.update({
        'vestibular_motion': 'translation',
        'vestibular_linear_accel': 85.0,
        'vestibular_linear_axis': 'x',
        'vestibular_linear_sign': 1.0,
    })
    run_gravity(GravityConfig(**trans_kwargs), outdir=outdir, save_outputs=True)
    process_trace = build_process_calculator_trace(
        _load_json(outdir / 'motion_state_trace.json'),
        _load_json(outdir / 'readout_trace.json'),
        _load_json(outdir / 'interface_network_trace.json'),
        window_size=3,
        stride=1,
    )
    shell_trace = build_mirror_shell_interface_trace(process_trace, _load_json(outdir / 'interface_network_trace.json'))
    atlas_trace = build_mirror_channel_atlas_trace(shell_trace)
    summary = summarize_mirror_channel_atlas_trace(atlas_trace)

    assert atlas_trace
    assert summary['active_summary']['dominant_mode'] == 'translation_like'
    assert summary['active_summary']['dominant_axis'] == 'x'
    assert_phase_coverage(summary['phase_counts'], ('baseline', 'active', 'recovery'), label='atlas translation phase_counts')
    first = atlas_trace[0]
    assert 'pair_summaries' in first and first['pair_summaries']
    pair = first['pair_summaries'][0]
    assert_required_keys(pair, ('shell_index', 'axis', 'symmetric_channels', 'differential_channels', 'dominant_mode', 'pair_common_mode', 'pair_differential_mode', 'handoff_gate_score', 'pair_gate_passed'), label='atlas pair')


def test_run_and_analyze_mirror_channel_atlas_protocol_without_subprocess(tmp_path: Path) -> None:
    outdir = tmp_path / 'mirror_channel_atlas_protocol'
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
        outdir=str(outdir),
    )
    report = run_protocol(args)
    report_path = outdir / 'mirror_channel_atlas_protocol_report.json'
    assert Path(report['report_path']) == report_path
    assert report_path.exists()

    analysis = analyze_report_file(report_path=report_path, output_dir=outdir / 'analysis')
    assert (outdir / 'analysis' / 'mirror_channel_atlas_analysis.json').exists()
    assert (outdir / 'analysis' / 'mirror_channel_atlas_overview.png').exists()

    for case_name, case_payload in analysis['cases'].items():
        assert_required_keys(case_payload, REQUIRED_CASE_KEYS, label=f'atlas analysis case {case_name}')

    assert_case_mode(analysis['cases']['floating_static'], expected_overall='static_like', label='floating_static atlas')
    assert_case_mode(analysis['cases']['translation_x_pos'], expected_active='translation_like', label='translation_x_pos atlas')
    assert_case_mode(analysis['cases']['translation_x_neg'], expected_active='translation_like', label='translation_x_neg atlas')
    assert_case_mode(analysis['cases']['rotation_z_pos'], expected_active='rotation_like', label='rotation_z_pos atlas')
    assert_case_mode(analysis['cases']['rotation_z_neg'], expected_active='rotation_like', label='rotation_z_neg atlas')
    assert analysis['cases']['translation_x_pos']['active_dominant_axis'] == 'x'
    assert analysis['cases']['translation_x_neg']['active_dominant_axis'] == 'x'
    assert analysis['cases']['rotation_z_pos']['active_dominant_axis'] == 'z'
    assert analysis['cases']['rotation_z_neg']['active_dominant_axis'] == 'z'
    assert_phase_coverage(analysis['cases']['translation_x_pos']['phase_counts'], ('baseline', 'active', 'recovery'), label='atlas translation_x_pos phase_counts')
    assert_phase_coverage(analysis['cases']['rotation_z_pos']['phase_counts'], ('baseline', 'active', 'recovery'), label='atlas rotation_z_pos phase_counts')

    tx_pos = float(analysis['cases']['translation_x_pos']['strongest_pair'].get('differential_channels', {}).get('polarity_projection', 0.0))
    tx_neg = float(analysis['cases']['translation_x_neg']['strongest_pair'].get('differential_channels', {}).get('polarity_projection', 0.0))
    rz_pos = float(analysis['cases']['rotation_z_pos']['strongest_pair'].get('differential_channels', {}).get('circulation_projection', 0.0))
    rz_neg = float(analysis['cases']['rotation_z_neg']['strongest_pair'].get('differential_channels', {}).get('circulation_projection', 0.0))
    assert_sign_flip(tx_pos, tx_neg, min_abs=1e-3, min_sep=1e-2, label='atlas translation polarity')
    assert_sign_flip(rz_pos, rz_neg, min_abs=1e-3, min_sep=1e-2, label='atlas rotation circulation')

    contract = validate_mirror_channel_atlas_analysis(analysis)
    assert contract['passed'] is True, contract['failures']
    assert analysis['contracts']['passed'] is True, analysis['contracts']['failures']
