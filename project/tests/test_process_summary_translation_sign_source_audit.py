from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from shutil import copytree

from scripts.run_process_summary_translation_sign_source_audit_protocol import run_protocol
from scripts.analyze_process_summary_translation_sign_source_audit import analyze_audit_file


def test_translation_sign_source_audit_identifies_outer_shell_dominance_change(tmp_path: Path) -> None:
    outdir = tmp_path / 'translation_sign_source_audit'
    copytree('outputs/process_summary_repeatability_r1', outdir / 'repeatability')
    calibration = Path('outputs/process_summary_family_polarity_calibration_r1/process_summary_family_polarity_calibration.json')
    args = Namespace(
        repeatability_report=str(outdir / 'repeatability' / 'process_summary_repeatability_protocol_report.json'),
        polarity_calibration=str(calibration),
        outdir=str(outdir),
    )
    payload = run_protocol(args)
    audit = payload['audit']
    assert audit['contracts']['passed'] is True, audit['contracts']['failures']
    assert audit['inferred_primary_source'] == 'outer_shell_dominance_change'
    assert audit['evidence']['family_wide_inversion_detected'] is True
    assert audit['evidence']['outer_shell_shift_detected'] is True
    analysis = analyze_audit_file(
        audit_path=payload['audit_path'],
        output_dir=outdir / 'analysis',
        title='translation sign source audit test',
    )
    assert analysis['contracts']['passed'] is True
    assert (outdir / 'analysis' / 'process_summary_translation_sign_source_audit_analysis.json').exists()
    assert (outdir / 'analysis' / 'process_summary_translation_sign_source_audit.png').exists()
