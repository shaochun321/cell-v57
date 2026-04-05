from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_interface_family_carrier_audit import (
    audit_translation_interface_family_carriers_files,
)


def test_translation_interface_family_carrier_audit_localizes_common_carrier_break() -> None:
    payload = audit_translation_interface_family_carriers_files(
        repeatability_report_path=ROOT / 'outputs/process_summary_repeatability_r1/process_summary_repeatability_audit.json'
    )
    assert payload['contracts']['passed']
    assert payload['inferred_primary_source'] == 'common_mirrored_translation_carrier_polarity_break'
    assert payload['evidence']['translation_family_survives_across_tracks']
    assert payload['evidence']['common_carrier_break_detected']
    assert payload['evidence']['x_pos_all_tracks_break_detected']
    assert payload['evidence']['x_neg_all_tracks_break_detected']
    assert payload['evidence']['discrete_track_specific_only'] is False

    rows = {int(r['seed']): r for r in payload['per_seed']}
    seed7 = rows[7]
    seed8 = rows[8]
    assert not seed7['family_common_carrier_break']
    assert seed8['family_common_carrier_break']

    for track in ('discrete_channel_track', 'local_propagation_track', 'layered_coupling_track'):
        assert seed8['cases']['translation_x_pos']['tracks'][track]['translation_family_survives'] is True
        assert seed8['cases']['translation_x_pos']['tracks'][track]['carrier_ok'] is False
        assert seed8['cases']['translation_x_neg']['tracks'][track]['translation_family_survives'] is True
        assert seed8['cases']['translation_x_neg']['tracks'][track]['carrier_ok'] is False
