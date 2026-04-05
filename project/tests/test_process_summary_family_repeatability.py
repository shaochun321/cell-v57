from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from shutil import copytree

from scripts.run_process_summary_family_repeatability_protocol import run_protocol
from scripts.analyze_process_summary_family_repeatability import analyze_audit_file


def test_process_summary_family_repeatability_reuses_existing_outputs_and_stays_family_stable(tmp_path: Path) -> None:
    outdir = tmp_path / 'family_repeatability'
    copytree('outputs/process_summary_repeatability_r1', outdir)
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
        outdir=str(outdir),
        reuse_existing=True,
    )
    payload = run_protocol(args)
    audit = payload['family_audit']
    assert audit['contracts']['passed'] is True, audit['contracts']['failures']
    assert audit['families']['translation']['axis_majority'] == 'x'
    assert audit['families']['translation']['expected_axis_fraction'] == 1.0
    assert audit['families']['translation']['flip_fraction'] == 1.0
    assert audit['families']['rotation']['axis_majority'] == 'z'
    assert audit['families']['rotation']['expected_axis_fraction'] == 1.0
    assert audit['families']['rotation']['flip_fraction'] == 1.0

    analysis = analyze_audit_file(
        audit_path=payload['family_audit_path'],
        output_dir=outdir / 'analysis',
        title='Process summary family repeatability test',
    )
    assert analysis['contracts']['passed'] is True
    assert (outdir / 'analysis' / 'process_summary_family_repeatability_analysis.json').exists()
    assert (outdir / 'analysis' / 'process_summary_family_repeatability_consistency.png').exists()
    assert (outdir / 'analysis' / 'process_summary_family_repeatability_separation.png').exists()
