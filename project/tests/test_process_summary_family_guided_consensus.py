from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from shutil import copy2, copytree

from scripts.run_process_summary_family_guided_consensus_protocol import run_protocol
from scripts.analyze_process_summary_family_guided_consensus import analyze_consensus_file


def test_family_guided_case_consensus_reuses_existing_outputs_and_separates_mode_axis_from_sign_calibration(tmp_path: Path) -> None:
    src = Path('outputs/process_summary_family_repeatability_r1')
    if not src.exists():
        src = Path('/mnt/data')
    # Use shipped outputs directly.
    repeatability_report = Path('outputs/process_summary_repeatability_r1/process_summary_repeatability_protocol_report.json')
    family_audit = Path('/mnt/data/process_summary_family_repeatability_audit.json')
    if not family_audit.exists():
        family_audit = Path('process_summary_family_repeatability_audit.json')
    outdir = tmp_path / 'family_guided_consensus'
    args = Namespace(
        repeatability_report=str(repeatability_report),
        family_audit=str(family_audit),
        outdir=str(outdir),
    )
    payload = run_protocol(args)
    consensus = payload['consensus']
    assert consensus['contracts']['passed'] is True, consensus['contracts']['failures']
    assert consensus['cases']['translation_x_pos']['consensus_mode'] == 'translation_like'
    assert consensus['cases']['translation_x_pos']['consensus_axis'] == 'x'
    assert consensus['cases']['translation_x_pos']['active_signal_expected_sign_fraction'] == 0.5
    assert consensus['cases']['rotation_z_pos']['consensus_mode'] == 'rotation_like'
    assert consensus['cases']['rotation_z_pos']['consensus_axis'] == 'z'
    assert consensus['cases']['rotation_z_pos']['active_signal_expected_sign_fraction'] == 1.0

    analysis = analyze_consensus_file(
        consensus_path=payload['consensus_path'],
        output_dir=outdir / 'analysis',
        title='family-guided case consensus test',
    )
    assert analysis['contracts']['passed'] is True
    assert (outdir / 'analysis' / 'process_summary_family_guided_case_consensus_analysis.json').exists()
    assert (outdir / 'analysis' / 'process_summary_family_guided_case_consensus.png').exists()
