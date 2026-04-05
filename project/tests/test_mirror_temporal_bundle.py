from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from cell_sphere_core.analysis.mirror_channel_atlas import build_mirror_channel_atlas_trace
from cell_sphere_core.analysis.mirror_shell_interface import build_mirror_shell_interface_trace
from cell_sphere_core.analysis.mirror_temporal_bundle import (
    build_mirror_temporal_bundle_trace,
    summarize_mirror_temporal_bundle_trace,
)
from cell_sphere_core.analysis.mirror_temporal_bundle_contract import validate_mirror_temporal_bundle_analysis
from cell_sphere_core.analysis.process_calculator import build_process_calculator_trace
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity
from scripts.analyze_mirror_temporal_bundle import analyze_report_file
from scripts.run_mirror_temporal_bundle_protocol import run_protocol
from tests._assertions import assert_case_mode, assert_phase_coverage, assert_required_keys, assert_sign_flip

REQUIRED_CASE_KEYS = (
    'dominant_mode',
    'dominant_axis',
    'phase_coverage',
    'overall_scores',
    'active_dominant_mode',
    'active_dominant_axis',
    'mean_active_pair_strength',
    'strongest_bundle',
)


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def test_mirror_temporal_bundle_trace_builds_cross_window_bundles(tmp_path: Path) -> None:
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
    bundle_trace = build_mirror_temporal_bundle_trace(atlas_trace)
    summary = summarize_mirror_temporal_bundle_trace(bundle_trace)

    assert bundle_trace
    assert summary['active_summary']['dominant_mode'] == 'translation_like'
    assert summary['active_summary']['dominant_axis'] == 'x'
    assert_phase_coverage(summary['phase_coverage'], ('baseline', 'active', 'recovery'), label='temporal bundle translation phase_coverage')
    first = bundle_trace[0]
    assert_required_keys(first, ('pair_key', 'phase_counts', 'mode_scores', 'dominant_mode', 'active_polarity_projection'), label='temporal bundle')


def test_run_and_analyze_mirror_temporal_bundle_protocol_without_subprocess(tmp_path: Path) -> None:
    outdir = tmp_path / 'mirror_temporal_bundle_protocol'
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
    report_path = outdir / 'mirror_temporal_bundle_protocol_report.json'
    assert Path(report['report_path']) == report_path
    assert report_path.exists()

    analysis = analyze_report_file(report_path=report_path, output_dir=outdir / 'analysis')
    assert (outdir / 'analysis' / 'mirror_temporal_bundle_analysis.json').exists()
    assert (outdir / 'analysis' / 'mirror_temporal_bundle_overview.png').exists()

    for case_name, case_payload in analysis['cases'].items():
        assert_required_keys(case_payload, REQUIRED_CASE_KEYS, label=f'temporal bundle analysis case {case_name}')

    assert_case_mode(analysis['cases']['floating_static'], expected_overall='static_like', label='floating_static temporal bundle')
    assert_case_mode(analysis['cases']['translation_x_pos'], expected_active='translation_like', label='translation_x_pos temporal bundle')
    assert_case_mode(analysis['cases']['translation_x_neg'], expected_active='translation_like', label='translation_x_neg temporal bundle')
    assert_case_mode(analysis['cases']['rotation_z_pos'], expected_overall='rotation_like', expected_active='rotation_like', label='rotation_z_pos temporal bundle')
    assert_case_mode(analysis['cases']['rotation_z_neg'], expected_overall='rotation_like', expected_active='rotation_like', label='rotation_z_neg temporal bundle')
    assert analysis['cases']['translation_x_pos']['active_dominant_axis'] == 'x'
    assert analysis['cases']['translation_x_neg']['active_dominant_axis'] == 'x'
    assert analysis['cases']['rotation_z_pos']['active_dominant_axis'] == 'z'
    assert analysis['cases']['rotation_z_neg']['active_dominant_axis'] == 'z'
    assert_phase_coverage(analysis['cases']['translation_x_pos']['phase_coverage'], ('baseline', 'active', 'recovery'), label='temporal bundle translation_x_pos phase_coverage')
    assert_phase_coverage(analysis['cases']['rotation_z_pos']['phase_coverage'], ('baseline', 'active', 'recovery'), label='temporal bundle rotation_z_pos phase_coverage')

    tx_pos = float(analysis['cases']['translation_x_pos']['strongest_bundle'].get('active_polarity_projection', 0.0))
    tx_neg = float(analysis['cases']['translation_x_neg']['strongest_bundle'].get('active_polarity_projection', 0.0))
    rz_pos = float(analysis['cases']['rotation_z_pos']['strongest_bundle'].get('active_circulation_projection', 0.0))
    rz_neg = float(analysis['cases']['rotation_z_neg']['strongest_bundle'].get('active_circulation_projection', 0.0))
    assert_sign_flip(tx_pos, tx_neg, min_abs=1e-3, min_sep=1e-2, label='temporal bundle translation polarity')
    assert_sign_flip(rz_pos, rz_neg, min_abs=1e-3, min_sep=1e-2, label='temporal bundle rotation circulation')

    contract = validate_mirror_temporal_bundle_analysis(analysis)
    assert contract['passed'] is True, contract['failures']
    assert analysis['contracts']['passed'] is True, analysis['contracts']['failures']
