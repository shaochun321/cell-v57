from __future__ import annotations

from pathlib import Path
import json

from cell_sphere_core.analysis.channel_invariants import summarize_channel_invariants
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def test_step27_invariants_summary_contains_cross_parameter_payload():
    report = json.loads(Path("outputs/step26_protocol_sample/step26_protocol_report.json").read_text(encoding="utf-8"))
    invariants = summarize_channel_invariants(report)
    assert invariants["principle"].startswith("cross-protocol and cross-parameter motif stability audit")
    for track_name in TRACK_NAMES:
        track = invariants["tracks"][track_name]
        assert track["num_cases"] >= 5
        assert "parameter_pair_deltas" in track
        # sample report may not include soft/base pairs, but the field must still exist
        assert track["translation"]["axial_dominance_consistency"] >= 0.75
        assert track["rotation"]["swirl_dominance_consistency"] >= 0.5
        assert track["translation"].get("polarity_separation_consistency", 0.0) >= 0.75
        assert track["rotation"].get("circulation_separation_consistency", 0.0) >= 0.5
        assert track["invariants"]["translation_axial_invariant"]
        assert isinstance(track["invariants"]["rotation_swirl_invariant"], bool)
