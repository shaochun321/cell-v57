
from __future__ import annotations

from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit import (
    build_m2_4_material_baseline_recheck,
)

def test_m2_4_material_baseline_recheck_freezes_candidate() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    audit = build_m2_4_material_baseline_recheck(repo_root)

    assert audit["decision"] == "freeze_m2_4_as_project_baseline"
    assert audit["evidence"]["gap_to_frozen_round52"] <= audit["thresholds"]["max_gap_to_frozen_round52"]
    assert all(audit["guardrails"].values())
    assert audit["round60_m2_4_candidate"]["translation_carrier_pair_count"] >= audit["round52_frozen_reference"]["translation_carrier_pair_count"]
    assert audit["round60_m2_4_candidate"]["translation_support"] >= audit["round52_frozen_reference"]["translation_support"]
