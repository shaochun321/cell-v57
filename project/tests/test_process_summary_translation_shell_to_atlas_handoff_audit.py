from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_shell_to_atlas_handoff_audit import (
    audit_translation_shell_to_atlas_handoff_files,
)


def test_translation_shell_to_atlas_handoff_localizes_interface_to_atlas_loss() -> None:
    payload = audit_translation_shell_to_atlas_handoff_files(
        repeatability_report_path=ROOT / 'outputs/process_summary_repeatability_r1/process_summary_repeatability_audit.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'shell_to_atlas_handoff_loss'
    assert payload['evidence']['family_wide_raw_sign_inversion']
    assert payload['evidence']['shell_interface_outer_shift_detected']
    assert payload['evidence']['interface_translation_survives_detected']
    assert payload['evidence']['atlas_pair_collapse_detected']
    assert payload['evidence']['shell_to_atlas_handoff_loss_detected']
    per_seed = {int(r['seed']): r for r in payload['per_seed']}
    seed7 = per_seed[7]
    seed8 = per_seed[8]
    assert not seed7['family_shell_to_atlas_handoff_loss']
    assert seed8['family_shell_to_atlas_handoff_loss']
    assert seed8['cases']['translation_x_pos']['interface_dominant_class'] == 'translation'
    assert seed8['cases']['translation_x_pos']['atlas_strongest_pair_mode'] == 'static_like'
    assert seed8['cases']['translation_x_pos']['axial_family_outer_inner_ratio'] > 4.0
    assert seed8['cases']['translation_x_neg']['shell_to_atlas_handoff_loss'] is True
