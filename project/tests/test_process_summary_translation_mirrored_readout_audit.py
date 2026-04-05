from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_mirrored_readout_audit import audit_translation_mirrored_readout_files


def test_translation_mirrored_readout_audit_localizes_signal_mass_relocation() -> None:
    payload = audit_translation_mirrored_readout_files(
        seed_profiles_path=ROOT / 'outputs/process_summary_translation_mirrored_readout_audit_r1/process_summary_translation_mirrored_readout_seed_profiles.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'translation_signal_mass_relocation'
    assert payload['evidence']['family_wide_raw_sign_inversion']
    assert payload['evidence']['translation_mass_relocation_detected']
    assert payload['evidence']['pair_weighting_disagreement_detected']
    per_seed = {int(r['seed']): r for r in payload['per_seed']}
    seed8 = per_seed[8]
    assert seed8['family_raw_inversion']
    assert seed8['family_mass_relocation']
    assert seed8['cases']['translation_x_pos']['inner_translation_share'] < 0.05
    assert seed8['cases']['translation_x_pos']['outer_translation_share'] > 0.80
    assert seed8['cases']['translation_x_neg']['strongest_shell_by_translation_mass'] == 2
    assert seed8['cases']['translation_x_neg']['strongest_shell_by_pair_strength'] == 3
