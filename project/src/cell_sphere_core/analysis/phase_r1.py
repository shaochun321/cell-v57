from __future__ import annotations

from typing import Any

from cell_sphere_core.analysis.phase_r import summarize_phase_r_audit
from cell_sphere_core.analysis.channel_invariants import summarize_channel_invariants
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def summarize_phase_r1_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    phase_r = summarize_phase_r_audit(protocol_report)
    invariants = summarize_channel_invariants(protocol_report)
    tracks = phase_r.get("tracks", {})

    ranking = sorted(
        (
            {
                "track_name": track_name,
                "rotation_score": float(tracks.get(track_name, {}).get("rotation_score", 0.0)),
                "translation_score": float(tracks.get(track_name, {}).get("translation_score", 0.0)),
            }
            for track_name in TRACK_NAMES
        ),
        key=lambda item: item["rotation_score"],
        reverse=True,
    )
    best_rotation = ranking[0] if ranking else {"track_name": "none", "rotation_score": 0.0, "translation_score": 0.0}
    layered = tracks.get("layered_coupling_track", {})
    local = tracks.get("local_propagation_track", {})
    discrete = tracks.get("discrete_channel_track", {})

    layered_rotation = float(layered.get("rotation_score", 0.0))
    local_rotation = float(local.get("rotation_score", 0.0))
    discrete_rotation = float(discrete.get("rotation_score", 0.0))
    translation_mean = float(phase_r.get("overall", {}).get("translation_consistency_mean", 0.0))
    rotation_mean = float(phase_r.get("overall", {}).get("rotation_consistency_mean", 0.0))

    layered_advantage_vs_local = float(layered_rotation - local_rotation)
    layered_advantage_vs_discrete = float(layered_rotation - discrete_rotation)
    layered_translation_tradeoff = float(layered_rotation - float(layered.get("translation_score", 0.0)))

    repair_status = {
        "layered_rotation_repaired": bool(layered_rotation >= 0.90),
        "layered_best_rotation_track": bool(best_rotation.get("track_name") == "layered_coupling_track"),
        "rotation_now_beats_translation_mean": bool(rotation_mean >= translation_mean),
    }

    cautions: list[str] = []
    if translation_mean < 0.78:
        cautions.append("Translation robustness is only moderate in the current Phase R.1 sweep; do not over-tune toward rotation and lose axial clarity.")
    if layered_advantage_vs_local < 0.03:
        cautions.append("Layered track rotation gain over the local track is still small; layered-specific repair may not yet be decisive.")
    if layered_advantage_vs_discrete < 0.05:
        cautions.append("Layered track is not yet clearly separated from the discrete baseline on rotation robustness.")
    if not cautions:
        cautions.append("Phase R.1 rotation repair is working in the current sweep, but it still needs confirmation across more parameter sets.")

    return {
        "principle": "Phase R.1 focuses on repairing rotation-specific robustness in the layered transduction track without adding new representational layers.",
        "phase_r_audit": phase_r,
        "channel_invariants": invariants,
        "rotation_track_ranking": ranking,
        "focused_metrics": {
            "layered_rotation_score": layered_rotation,
            "local_rotation_score": local_rotation,
            "discrete_rotation_score": discrete_rotation,
            "layered_advantage_vs_local": layered_advantage_vs_local,
            "layered_advantage_vs_discrete": layered_advantage_vs_discrete,
            "layered_translation_tradeoff": layered_translation_tradeoff,
            "translation_consistency_mean": translation_mean,
            "rotation_consistency_mean": rotation_mean,
        },
        "repair_status": repair_status,
        "cautions": cautions,
    }
