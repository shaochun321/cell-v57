from __future__ import annotations

from typing import Any

import numpy as np


def _sign(value: float, eps: float = 1e-6) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rating(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "moderate"
    return "weak"


def _track_report(case_payload: dict[str, Any], track_name: str = "layered_coupling_track") -> dict[str, Any]:
    return dict(case_payload.get("motif_report", {}).get("tracks", {}).get(track_name, {}))


def _rotation_metrics(pos_case: dict[str, Any], neg_case: dict[str, Any], track_name: str = "layered_coupling_track") -> dict[str, float]:
    pos = _track_report(pos_case, track_name)
    neg = _track_report(neg_case, track_name)
    pos_fam = dict(pos.get("active_family_means", {}))
    neg_fam = dict(neg.get("active_family_means", {}))
    pos_swirl = float(pos_fam.get("swirl_circulation_family", 0.0))
    neg_swirl = float(neg_fam.get("swirl_circulation_family", 0.0))
    pos_axial = float(pos_fam.get("axial_polar_family", 0.0))
    neg_axial = float(neg_fam.get("axial_polar_family", 0.0))
    pos_margin = pos_swirl - pos_axial
    neg_margin = neg_swirl - neg_axial
    pos_circ = float(pos.get("active_signed_circulation", 0.0))
    neg_circ = float(neg.get("active_signed_circulation", 0.0))
    swirl_dom = 0.5 * ((1.0 if pos_margin > 0.0 else 0.0) + (1.0 if neg_margin > 0.0 else 0.0))
    sign_sep = 1.0 if _sign(pos_circ) == 1 and _sign(neg_circ) == -1 else 0.0
    sign_mag_balance = abs(abs(pos_circ) - abs(neg_circ)) / max(abs(pos_circ), abs(neg_circ), 1e-6)
    circ_cv = float(np.std([abs(pos_circ), abs(neg_circ)]) / max(np.mean([abs(pos_circ), abs(neg_circ)]), 1e-6))
    score = _clip01(0.45 * swirl_dom + 0.35 * sign_sep + 0.10 * (1.0 - min(circ_cv, 1.0)) + 0.10 * (1.0 - min(sign_mag_balance, 1.0)))
    return {
        "pos_swirl_margin": float(pos_margin),
        "neg_swirl_margin": float(neg_margin),
        "mean_swirl_margin": float(0.5 * (pos_margin + neg_margin)),
        "pos_signed_circulation": pos_circ,
        "neg_signed_circulation": neg_circ,
        "swirl_dominance": float(swirl_dom),
        "sign_separation": float(sign_sep),
        "circulation_cv": float(circ_cv),
        "sign_magnitude_balance": float(1.0 - min(sign_mag_balance, 1.0)),
        "rotation_score": float(score),
    }


def _translation_guard_metrics(case_payload: dict[str, Any], track_name: str = "layered_coupling_track") -> dict[str, float]:
    tr = _track_report(case_payload, track_name)
    fam = dict(tr.get("active_family_means", {}))
    axial = float(fam.get("axial_polar_family", 0.0))
    swirl = float(fam.get("swirl_circulation_family", 0.0))
    x_balance = float(dict(tr.get("active_axis_balance", {})).get("x", 0.0))
    margin = axial - swirl
    score = _clip01(0.75 * (1.0 if margin > 0.0 else 0.0) + 0.25 * (1.0 if _sign(x_balance) != 0 else 0.0))
    return {
        "axial_margin": float(margin),
        "x_balance": float(x_balance),
        "translation_guard_score": float(score),
    }


def _local_robustness(rows_sorted: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows_sorted:
        return {
            "neighbor_count": 0,
            "local_mean": 0.0,
            "local_std": 0.0,
            "local_floor": 0.0,
            "plateau_fraction": 0.0,
            "boundary_best": True,
            "stable_region_score": 0.0,
        }
    best = rows_sorted[0]
    alphas = sorted({float(r["rotation_alpha"]) for r in rows_sorted})
    gains = sorted({float(r["swirl_gain"]) for r in rows_sorted})
    a_idx = alphas.index(float(best["rotation_alpha"]))
    g_idx = gains.index(float(best["swirl_gain"]))
    boundary_best = a_idx in {0, len(alphas)-1} or g_idx in {0, len(gains)-1}
    alpha_neighbors = set(alphas[max(0, a_idx-1): min(len(alphas), a_idx+2)])
    gain_neighbors = set(gains[max(0, g_idx-1): min(len(gains), g_idx+2)])
    neighborhood = [
        r for r in rows_sorted
        if float(r["rotation_alpha"]) in alpha_neighbors and float(r["swirl_gain"]) in gain_neighbors
    ]
    scores = [float(r["rotation_score"]) for r in neighborhood]
    local_mean = float(np.mean(scores)) if scores else 0.0
    local_std = float(np.std(scores)) if scores else 0.0
    local_floor = float(min(scores)) if scores else 0.0
    plateau_fraction = float(np.mean([1.0 if s >= float(best["rotation_score"]) - 0.01 else 0.0 for s in scores])) if scores else 0.0
    stable_region_score = _clip01(
        0.40 * local_mean +
        0.25 * local_floor +
        0.20 * (1.0 - min(local_std / 0.03, 1.0)) +
        0.15 * plateau_fraction
    )
    return {
        "neighbor_count": int(len(scores)),
        "local_mean": local_mean,
        "local_std": local_std,
        "local_floor": local_floor,
        "plateau_fraction": plateau_fraction,
        "boundary_best": bool(boundary_best),
        "stable_region_score": stable_region_score,
        "alpha_neighbors": [float(x) for x in sorted(alpha_neighbors)],
        "swirl_gain_neighbors": [float(x) for x in sorted(gain_neighbors)],
    }


def summarize_phase_r2_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(protocol_report.get("metadata", {}))
    scan_cases = list(protocol_report.get("rotation_scan", []))
    translation_guard = dict(protocol_report.get("translation_guard", {}))
    rows: list[dict[str, Any]] = []
    for case in scan_cases:
        metrics = _rotation_metrics(case.get("rotation_pos", {}), case.get("rotation_neg", {}))
        rows.append({
            "case_id": case.get("case_id", "unknown"),
            "rotation_alpha": float(case.get("rotation_alpha", 0.0)),
            "swirl_gain": float(case.get("swirl_gain", 1.0)),
            "circulation_gain": float(case.get("circulation_gain", 1.0)),
            "axial_base": float(case.get("axial_base", 0.0)),
            "transfer_base": float(case.get("transfer_base", 0.0)),
            "circulation_feed": float(case.get("circulation_feed", 0.0)),
            **metrics,
        })
    rows_sorted = sorted(rows, key=lambda item: item["rotation_score"], reverse=True)
    best = rows_sorted[0] if rows_sorted else {"case_id": "none", "rotation_score": 0.0}
    worst = rows_sorted[-1] if rows_sorted else {"case_id": "none", "rotation_score": 0.0}

    heatmap: dict[str, dict[str, float]] = {}
    by_alpha: dict[float, list[float]] = {}
    by_swirl: dict[float, list[float]] = {}
    for row in rows:
        akey = f"{row['rotation_alpha']:.3f}"
        skey = f"{row['swirl_gain']:.3f}"
        heatmap.setdefault(akey, {})[skey] = float(row["rotation_score"])
        by_alpha.setdefault(float(row["rotation_alpha"]), []).append(float(row["rotation_score"]))
        by_swirl.setdefault(float(row["swirl_gain"]), []).append(float(row["rotation_score"]))

    alpha_means = {f"{k:.3f}": float(np.mean(v)) for k, v in sorted(by_alpha.items())}
    swirl_means = {f"{k:.3f}": float(np.mean(v)) for k, v in sorted(by_swirl.items())}
    guard_metrics = _translation_guard_metrics(translation_guard) if translation_guard else {
        "axial_margin": 0.0,
        "x_balance": 0.0,
        "translation_guard_score": 0.0,
    }
    local = _local_robustness(rows_sorted)

    recommendations: list[str] = []
    if float(best.get("rotation_score", 0.0)) < 0.85:
        recommendations.append("No rotation scan point reached the strong threshold; keep tuning rotation forcing and layered repair together.")
    if float(guard_metrics.get("translation_guard_score", 0.0)) < 0.90:
        recommendations.append("Best layered rotation settings are beginning to erode translation guard clarity; do not widen the sweep before protecting axial response.")
    if local.get("boundary_best", True):
        recommendations.append("Best point still touches the current scan boundary; extend alpha and/or swirl-gain slightly before calling this a settled region.")
    if float(local.get("stable_region_score", 0.0)) < 0.82:
        recommendations.append("Local robustness around the best point is not yet strong; treat the current optimum as a narrow ridge, not a broad plateau.")
    if not recommendations:
        recommendations.append("A compact stable region is emerging; confirm it with one extra sweep before unfreezing broader structure work.")

    return {
        "principle": "Phase R.2 performs a focused rotation-only sensitivity audit over forcing and layered transduction repair, without adding new representation layers.",
        "metadata": metadata,
        "translation_guard": guard_metrics,
        "scan_rows": rows_sorted,
        "best_config": best,
        "worst_config": worst,
        "local_robustness": local,
        "heatmap": heatmap,
        "alpha_mean_scores": alpha_means,
        "swirl_mean_scores": swirl_means,
        "overall": {
            "num_scan_points": int(len(rows)),
            "rotation_score_mean": float(np.mean([row["rotation_score"] for row in rows])) if rows else 0.0,
            "rotation_score_std": float(np.std([row["rotation_score"] for row in rows])) if rows else 0.0,
            "strong_region_fraction": float(np.mean([1.0 if row["rotation_score"] >= 0.8 else 0.0 for row in rows])) if rows else 0.0,
        },
        "recommendations": recommendations,
        "ratings": {
            "best_rotation": _rating(float(best.get("rotation_score", 0.0))),
            "translation_guard": _rating(float(guard_metrics.get("translation_guard_score", 0.0))),
            "local_stability": _rating(float(local.get("stable_region_score", 0.0))),
        },
    }
