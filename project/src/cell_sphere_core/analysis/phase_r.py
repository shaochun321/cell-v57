from __future__ import annotations

from typing import Any
import math

from cell_sphere_core.analysis.channel_invariants import summarize_channel_invariants
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def _rating(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "moderate"
    return "weak"


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def summarize_phase_r_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    invariants = summarize_channel_invariants(protocol_report)
    tracks: dict[str, Any] = {}
    rotation_scores = []
    translation_scores = []
    for track_name in TRACK_NAMES:
        track = invariants["tracks"][track_name]
        translation = track["translation"]
        rotation = track["rotation"]
        translation_score = _clip01(
            0.55 * float(translation.get("axial_dominance_consistency", 0.0))
            + 0.35 * float(translation.get("polarity_separation_consistency", 0.0))
            + 0.10 * (1.0 - min(float(translation.get("axial_margin_cv", 0.0)), 1.0))
        )
        rotation_score = _clip01(
            0.50 * float(rotation.get("swirl_dominance_consistency", 0.0))
            + 0.35 * float(rotation.get("circulation_separation_consistency", 0.0))
            + 0.15 * (1.0 - min(float(rotation.get("signed_circulation_cv", 0.0)), 1.0))
        )
        tracks[track_name] = {
            "translation_score": translation_score,
            "translation_rating": _rating(translation_score),
            "rotation_score": rotation_score,
            "rotation_rating": _rating(rotation_score),
            "translation_metrics": {
                "axial_dominance_consistency": float(translation.get("axial_dominance_consistency", 0.0)),
                "polarity_separation_consistency": float(translation.get("polarity_separation_consistency", 0.0)),
                "axial_margin_cv": float(translation.get("axial_margin_cv", 0.0)),
            },
            "rotation_metrics": {
                "swirl_dominance_consistency": float(rotation.get("swirl_dominance_consistency", 0.0)),
                "circulation_separation_consistency": float(rotation.get("circulation_separation_consistency", 0.0)),
                "signed_circulation_cv": float(rotation.get("signed_circulation_cv", 0.0)),
            },
            "robust_substructures": {
                "translation": int(len(translation.get("robust_substructures", []))),
                "rotation": int(len(rotation.get("robust_substructures", []))),
            },
        }
        translation_scores.append((track_name, translation_score))
        rotation_scores.append((track_name, rotation_score))

    best_translation = max(translation_scores, key=lambda kv: kv[1]) if translation_scores else ("none", 0.0)
    best_rotation = max(rotation_scores, key=lambda kv: kv[1]) if rotation_scores else ("none", 0.0)
    worst_rotation = min(rotation_scores, key=lambda kv: kv[1]) if rotation_scores else ("none", 0.0)

    rotation_consistency_mean = sum(score for _, score in rotation_scores) / max(1, len(rotation_scores))
    translation_consistency_mean = sum(score for _, score in translation_scores) / max(1, len(translation_scores))

    recommendations: list[str] = []
    if worst_rotation[1] < 0.6:
        recommendations.append(
            f"Prioritize rotation repair on {worst_rotation[0]}: swirl/circulation stability is still below the moderate threshold."
        )
    if translation_consistency_mean - rotation_consistency_mean > 0.15:
        recommendations.append(
            "Freeze new representation layers and spend the next iteration budget on rotation-only forcing, damping, and channel-propagation tuning."
        )
    if best_rotation[1] < 0.75:
        recommendations.append(
            "Do not claim mature rotational robustness yet; treat rotation results as provisional until cross-parameter scores improve."
        )
    if not recommendations:
        recommendations.append("Current R1/R2 audit is healthy; proceed carefully and keep representation layers frozen.")

    return {
        "principle": "Phase R freezes representation growth and audits robustness: R1 repairs rotational stability, R2 audits parameter robustness, R3 documents theory alignment, and R4 freezes structure expansion until physical reliability improves.",
        "invariants": invariants,
        "tracks": tracks,
        "overall": {
            "translation_consistency_mean": float(translation_consistency_mean),
            "translation_rating": _rating(translation_consistency_mean),
            "rotation_consistency_mean": float(rotation_consistency_mean),
            "rotation_rating": _rating(rotation_consistency_mean),
            "best_translation_track": {"track_name": best_translation[0], "score": float(best_translation[1])},
            "best_rotation_track": {"track_name": best_rotation[0], "score": float(best_rotation[1])},
            "worst_rotation_track": {"track_name": worst_rotation[0], "score": float(worst_rotation[1])},
            "rotation_gap_vs_translation": float(max(0.0, translation_consistency_mean - rotation_consistency_mean)),
        },
        "recommendations": recommendations,
    }
