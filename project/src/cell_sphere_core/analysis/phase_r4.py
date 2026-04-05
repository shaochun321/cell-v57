from __future__ import annotations

from typing import Any

import numpy as np

from .phase_r3 import summarize_phase_r3_audit


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rating(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "moderate"
    return "weak"


def _group_mean(rows: list[dict[str, Any]], key: str) -> dict[float, float]:
    buckets: dict[float, list[float]] = {}
    for row in rows:
        buckets.setdefault(float(row[key]), []).append(float(row["rotation_score"]))
    return {k: float(np.mean(v)) for k, v in sorted(buckets.items())}


def _directional_extension(rows: list[dict[str, Any]], closure: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not rows:
        return {
            "direction": "unknown",
            "status": "unknown",
            "anchor_value": 0.0,
            "frontier_value": 0.0,
            "anchor_mean": 0.0,
            "frontier_mean": 0.0,
            "support_gap": 0.0,
            "support_ratio": 0.0,
            "edge_stable_fraction": 0.0,
            "directional_score": 0.0,
            "reason": "no rows",
        }
    rows = list(rows)
    stable_threshold = float(closure.get("stable_threshold", 0.0))
    stable_points = {
        (float(p["rotation_alpha"]), float(p["swirl_gain"]))
        for p in closure.get("stable_points", [])
    }
    alphas = sorted({float(r["rotation_alpha"]) for r in rows})
    gains = sorted({float(r["swirl_gain"]) for r in rows})
    alpha_means = _group_mean(rows, "rotation_alpha")
    gain_means = _group_mean(rows, "swirl_gain")

    # Decide which boundary is the active frontier by stable-point contact.
    alpha_frontiers = {
        "lower_alpha": [p for p in stable_points if p[0] == alphas[0]],
        "upper_alpha": [p for p in stable_points if p[0] == alphas[-1]],
    }
    gain_frontiers = {
        "lower_gain": [p for p in stable_points if p[1] == gains[0]],
        "upper_gain": [p for p in stable_points if p[1] == gains[-1]],
    }
    counts = {k: len(v) for k, v in {**alpha_frontiers, **gain_frontiers}.items()}
    hinted_direction = str((metadata or {}).get('frontier_direction', '')).strip()
    if hinted_direction in counts:
        direction = hinted_direction
    else:
        direction = max(counts, key=counts.get) if any(counts.values()) else "lower_alpha"

    if direction == "lower_alpha":
        frontier_value = alphas[0]
        anchor_value = alphas[1] if len(alphas) > 1 else alphas[0]
        frontier_rows = [r for r in rows if float(r["rotation_alpha"]) == frontier_value]
        anchor_rows = [r for r in rows if float(r["rotation_alpha"]) == anchor_value]
        frontier_mean = alpha_means.get(frontier_value, 0.0)
        anchor_mean = alpha_means.get(anchor_value, 0.0)
    elif direction == "upper_alpha":
        frontier_value = alphas[-1]
        anchor_value = alphas[-2] if len(alphas) > 1 else alphas[-1]
        frontier_rows = [r for r in rows if float(r["rotation_alpha"]) == frontier_value]
        anchor_rows = [r for r in rows if float(r["rotation_alpha"]) == anchor_value]
        frontier_mean = alpha_means.get(frontier_value, 0.0)
        anchor_mean = alpha_means.get(anchor_value, 0.0)
    elif direction == "lower_gain":
        frontier_value = gains[0]
        anchor_value = gains[1] if len(gains) > 1 else gains[0]
        frontier_rows = [r for r in rows if float(r["swirl_gain"]) == frontier_value]
        anchor_rows = [r for r in rows if float(r["swirl_gain"]) == anchor_value]
        frontier_mean = gain_means.get(frontier_value, 0.0)
        anchor_mean = gain_means.get(anchor_value, 0.0)
    else:
        frontier_value = gains[-1]
        anchor_value = gains[-2] if len(gains) > 1 else gains[-1]
        frontier_rows = [r for r in rows if float(r["swirl_gain"]) == frontier_value]
        anchor_rows = [r for r in rows if float(r["swirl_gain"]) == anchor_value]
        frontier_mean = gain_means.get(frontier_value, 0.0)
        anchor_mean = gain_means.get(anchor_value, 0.0)

    edge_stable_fraction = float(np.mean([1.0 if float(r["rotation_score"]) >= stable_threshold else 0.0 for r in frontier_rows])) if frontier_rows else 0.0
    support_gap = float(frontier_mean - anchor_mean)
    support_ratio = float(frontier_mean / max(anchor_mean, 1e-6))
    directional_score = _clip01(
        0.45 * frontier_mean
        + 0.25 * edge_stable_fraction
        + 0.15 * (1.0 if support_gap >= -0.01 else 0.0)
        + 0.15 * min(max(support_ratio - 0.9, 0.0) / 0.2, 1.0)
    )

    if edge_stable_fraction >= 0.5 and frontier_mean >= anchor_mean - 0.01:
        status = "continues"
        reason = "frontier band remains as strong as the inner anchor band; the stable region is still extending toward the scanned edge"
    elif edge_stable_fraction <= 0.25 and frontier_mean < anchor_mean - 0.02:
        status = "degrades"
        reason = "frontier band weakens noticeably relative to the inner anchor band; the stable region is starting to roll off"
    else:
        status = "unclear"
        reason = "frontier band is mixed: not clearly continuing, not clearly collapsing"

    return {
        "direction": direction,
        "status": status,
        "anchor_value": float(anchor_value),
        "frontier_value": float(frontier_value),
        "anchor_mean": float(anchor_mean),
        "frontier_mean": float(frontier_mean),
        "support_gap": support_gap,
        "support_ratio": support_ratio,
        "edge_stable_fraction": edge_stable_fraction,
        "directional_score": directional_score,
        "reason": reason,
    }


def summarize_phase_r4_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    base = summarize_phase_r3_audit(protocol_report)
    rows = list(base.get("scan_rows", []))
    closure = dict(base.get("closure", {}))
    directional = _directional_extension(rows, closure, dict(base.get("metadata", {})))
    recommendations = list(base.get("recommendations", []))
    if directional.get("status") == "continues":
        recommendations.append("The stable band still extends along the scanned boundary direction; keep extending the sweep before declaring closure.")
    elif directional.get("status") == "degrades":
        recommendations.append("The stable band is now rolling off at the scanned edge; you can start treating the current region as locally bounded.")
    else:
        recommendations.append("Boundary continuation is still ambiguous; confirm with one more narrow sweep centered on the current frontier band.")
    return {
        **base,
        "phase": "Phase R.4",
        "principle": "Phase R.4 extends the sweep along the active boundary direction and asks whether the stable rotation band continues, degrades, or becomes locally bounded.",
        "directional_extension": directional,
        "ratings": {
            **dict(base.get("ratings", {})),
            "directional_extension": _rating(float(directional.get("directional_score", 0.0))),
        },
        "recommendations": recommendations,
    }
