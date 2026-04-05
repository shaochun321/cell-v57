from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from cell_sphere_core.analysis.process_summary_atlas import build_process_summary_atlas
from cell_sphere_core.analysis.process_summary_atlas_contract import validate_process_summary_atlas_analysis
from scripts.analyze_process_summary_atlas import analyze_report_file
from scripts.run_process_summary_atlas_protocol import run_protocol
from tests._assertions import assert_case_mode, assert_phase_coverage, assert_required_keys, assert_sign_flip

REQUIRED_CASE_KEYS = (
    'dominant_mode',
    'dominant_axis',
    'phase_coverage',
    'overall_scores',
    'active_dominant_mode',
    'active_dominant_axis',
    'phase_summaries',
    'active_signature',
)


def test_build_process_summary_atlas_from_existing_atlas_trace() -> None:
    import json
    atlas_trace = json.loads(Path('outputs/mirror_temporal_bundle_protocol_r2/translation_x_pos/mirror_channel_atlas_trace.json').read_text(encoding='utf-8'))
    summary = build_process_summary_atlas(atlas_trace)
    assert summary['dominant_mode'] == 'translation_like'
    assert summary['active_dominant_mode'] == 'translation_like'
    assert summary['active_dominant_axis'] == 'x'
    assert_phase_coverage(summary['phase_coverage'], ('baseline', 'active', 'recovery'), label='process summary atlas translation phase_coverage')
    assert_required_keys(summary['active_signature'], ('axis', 'mean_polarity_projection', 'support_scores'), label='process summary atlas active signature')


def test_run_and_analyze_process_summary_atlas_protocol_reusing_existing_outputs(tmp_path: Path) -> None:
    outdir = tmp_path / 'process_summary_atlas_protocol'
    from shutil import copytree
    copytree('outputs/mirror_temporal_bundle_protocol_r2', outdir)
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
        reuse_existing=True,
    )
    report = run_protocol(args)
    report_path = outdir / 'process_summary_atlas_protocol_report.json'
    assert Path(report['report_path']) == report_path
    assert report_path.exists()

    analysis = analyze_report_file(report_path=report_path, output_dir=outdir / 'analysis')
    assert (outdir / 'analysis' / 'process_summary_atlas_analysis.json').exists()
    assert (outdir / 'analysis' / 'process_summary_atlas_overview.png').exists()

    for case_name, case_payload in analysis['cases'].items():
        assert_required_keys(case_payload, REQUIRED_CASE_KEYS, label=f'process summary atlas analysis case {case_name}')

    assert_case_mode(analysis['cases']['floating_static'], expected_overall='static_like', label='floating_static process summary atlas')
    assert_case_mode(analysis['cases']['translation_x_pos'], expected_overall='translation_like', expected_active='translation_like', label='translation_x_pos process summary atlas')
    assert_case_mode(analysis['cases']['translation_x_neg'], expected_overall='translation_like', expected_active='translation_like', label='translation_x_neg process summary atlas')
    assert_case_mode(analysis['cases']['rotation_z_pos'], expected_overall='rotation_like', expected_active='rotation_like', label='rotation_z_pos process summary atlas')
    assert_case_mode(analysis['cases']['rotation_z_neg'], expected_overall='rotation_like', expected_active='rotation_like', label='rotation_z_neg process summary atlas')
    assert analysis['cases']['translation_x_pos']['active_dominant_axis'] == 'x'
    assert analysis['cases']['translation_x_neg']['active_dominant_axis'] == 'x'
    assert analysis['cases']['rotation_z_pos']['active_dominant_axis'] == 'z'
    assert analysis['cases']['rotation_z_neg']['active_dominant_axis'] == 'z'
    assert_phase_coverage(analysis['cases']['translation_x_pos']['phase_coverage'], ('baseline', 'active', 'recovery'), label='process summary atlas translation_x_pos phase_coverage')
    assert_phase_coverage(analysis['cases']['rotation_z_pos']['phase_coverage'], ('baseline', 'active', 'recovery'), label='process summary atlas rotation_z_pos phase_coverage')

    tx_pos = float(analysis['cases']['translation_x_pos']['active_signature'].get('mean_polarity_projection', 0.0))
    tx_neg = float(analysis['cases']['translation_x_neg']['active_signature'].get('mean_polarity_projection', 0.0))
    rz_pos = float(analysis['cases']['rotation_z_pos']['active_signature'].get('mean_circulation_projection', 0.0))
    rz_neg = float(analysis['cases']['rotation_z_neg']['active_signature'].get('mean_circulation_projection', 0.0))
    assert_sign_flip(tx_pos, tx_neg, min_abs=1e-3, min_sep=1e-2, label='process summary atlas translation polarity')
    assert_sign_flip(rz_pos, rz_neg, min_abs=1e-3, min_sep=1e-2, label='process summary atlas rotation circulation')

    contract = validate_process_summary_atlas_analysis(analysis)
    assert contract['passed'] is True, contract['failures']
    assert analysis['contracts']['passed'] is True, analysis['contracts']['failures']
