from __future__ import annotations

from pathlib import Path
import json

from cell_sphere_core.analysis.phase_r import summarize_phase_r_audit
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def test_phase_r_audit_summary_contains_rotation_gap_and_recommendations():
    report = json.loads(Path('outputs/phase_r_sample/phase_r_protocol_report.json').read_text(encoding='utf-8'))
    audit = summarize_phase_r_audit(report)
    assert 'overall' in audit
    assert 'recommendations' in audit
    assert isinstance(audit['recommendations'], list)
    assert audit['overall']['translation_consistency_mean'] >= 0.75
    for track_name in TRACK_NAMES:
        assert track_name in audit['tracks']
        track = audit['tracks'][track_name]
        assert 'translation_score' in track
        assert 'rotation_score' in track
        assert track['translation_rating'] in {'strong', 'moderate', 'weak'}
        assert track['rotation_rating'] in {'strong', 'moderate', 'weak'}
