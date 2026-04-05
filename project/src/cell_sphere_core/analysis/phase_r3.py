from __future__ import annotations

from typing import Any

import numpy as np

from .phase_r2 import summarize_phase_r2_audit


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rating(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "moderate"
    return "weak"


def _stable_component(rows: list[dict[str, Any]], best: dict[str, Any]) -> dict[str, Any]:
    if not rows:
        return {
            "stable_threshold": 0.0,
            "component_size": 0,
            "boundary_touch": True,
            "closure_score": 0.0,
            "alpha_span": [0.0, 0.0],
            "swirl_gain_span": [0.0, 0.0],
            "mean_score": 0.0,
            "floor_score": 0.0,
            "interior_fraction": 0.0,
            "stable_points": [],
        }
    alphas = sorted({float(r["rotation_alpha"]) for r in rows})
    gains = sorted({float(r["swirl_gain"]) for r in rows})
    stable_threshold = max(float(best.get("rotation_score", 0.0)) - 0.01, 0.90)
    point_map = {(float(r["rotation_alpha"]), float(r["swirl_gain"])): r for r in rows}
    stable = {k for k, r in point_map.items() if float(r["rotation_score"]) >= stable_threshold}
    best_key = (float(best.get("rotation_alpha", 0.0)), float(best.get("swirl_gain", 0.0)))
    if best_key not in stable:
        stable.add(best_key)
    if best_key not in point_map:
        return {
            "stable_threshold": stable_threshold,
            "component_size": 0,
            "boundary_touch": True,
            "closure_score": 0.0,
            "alpha_span": [0.0, 0.0],
            "swirl_gain_span": [0.0, 0.0],
            "mean_score": 0.0,
            "floor_score": 0.0,
            "interior_fraction": 0.0,
            "stable_points": [],
        }
    a_index = {v: i for i, v in enumerate(alphas)}
    g_index = {v: i for i, v in enumerate(gains)}

    def neighbors(key: tuple[float, float]) -> list[tuple[float, float]]:
        ai = a_index[key[0]]
        gi = g_index[key[1]]
        out: list[tuple[float, float]] = []
        for da, dg in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nai = ai + da
            ngi = gi + dg
            if 0 <= nai < len(alphas) and 0 <= ngi < len(gains):
                nk = (alphas[nai], gains[ngi])
                if nk in stable:
                    out.append(nk)
        return out

    stack = [best_key]
    component: set[tuple[float, float]] = set()
    while stack:
        cur = stack.pop()
        if cur in component:
            continue
        component.add(cur)
        stack.extend(neighbors(cur))

    component_rows = [point_map[k] for k in component]
    scores = [float(r["rotation_score"]) for r in component_rows]
    if component:
        a_vals = sorted({k[0] for k in component})
        g_vals = sorted({k[1] for k in component})
        boundary_touch = any(
            a_index[a] in {0, len(alphas) - 1} or g_index[g] in {0, len(gains) - 1}
            for a, g in component
        )
        interior_points = [
            (a, g) for a, g in component
            if a_index[a] not in {0, len(alphas) - 1} and g_index[g] not in {0, len(gains) - 1}
        ]
        interior_fraction = float(len(interior_points) / len(component)) if component else 0.0
    else:
        a_vals = [0.0]
        g_vals = [0.0]
        boundary_touch = True
        interior_fraction = 0.0
    mean_score = float(np.mean(scores)) if scores else 0.0
    floor_score = float(min(scores)) if scores else 0.0
    closure_score = _clip01(
        0.35 * mean_score
        + 0.25 * floor_score
        + 0.20 * interior_fraction
        + 0.20 * (0.0 if boundary_touch else 1.0)
    )
    return {
        "stable_threshold": float(stable_threshold),
        "component_size": int(len(component)),
        "boundary_touch": bool(boundary_touch),
        "closure_score": float(closure_score),
        "alpha_span": [float(a_vals[0]), float(a_vals[-1])],
        "swirl_gain_span": [float(g_vals[0]), float(g_vals[-1])],
        "mean_score": mean_score,
        "floor_score": floor_score,
        "interior_fraction": interior_fraction,
        "stable_points": [
            {
                "rotation_alpha": float(a),
                "swirl_gain": float(g),
                "rotation_score": float(point_map[(a, g)]["rotation_score"]),
            }
            for a, g in sorted(component)
        ],
    }


def _next_scan_suggestion(closure: dict[str, Any], all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not all_rows:
        return {"alpha_hint": [], "swirl_gain_hint": [], "reason": "no rows"}
    alphas = sorted({float(r["rotation_alpha"]) for r in all_rows})
    gains = sorted({float(r["swirl_gain"]) for r in all_rows})
    da = float(np.median(np.diff(alphas))) if len(alphas) >= 2 else 40.0
    dg = float(np.median(np.diff(gains))) if len(gains) >= 2 else 0.1
    a0, a1 = closure.get("alpha_span", [alphas[0], alphas[-1]])
    g0, g1 = closure.get("swirl_gain_span", [gains[0], gains[-1]])
    alpha_hint = [max(0.0, a0 - da), a1 + da]
    gain_hint = [max(0.0, g0 - dg), g1 + dg]
    reason = (
        "stable component still touches boundary; extend one step past current stable span"
        if closure.get("boundary_touch", True)
        else "stable component appears enclosed; optional confirmation sweep around the enclosed span"
    )
    return {
        "alpha_hint": [float(alpha_hint[0]), float(alpha_hint[1])],
        "swirl_gain_hint": [float(gain_hint[0]), float(gain_hint[1])],
        "reason": reason,
    }


def summarize_phase_r3_audit(protocol_report: dict[str, Any]) -> dict[str, Any]:
    base = summarize_phase_r2_audit(protocol_report)
    rows = list(base.get("scan_rows", []))
    best = dict(base.get("best_config", {}))
    closure = _stable_component(rows, best)
    suggestion = _next_scan_suggestion(closure, rows)
    recommendations = list(base.get("recommendations", []))
    if closure.get("boundary_touch", True):
        recommendations.append("Stable component still touches the expanded scan boundary; do not call the rotation region closed yet.")
    elif float(closure.get("closure_score", 0.0)) >= 0.8:
        recommendations.append("Stable component now appears enclosed within the expanded scan; you can freeze this compact region and switch to confirmation runs.")
    else:
        recommendations.append("Stable component is partially enclosed but still shallow; verify with one more local sweep before freezing parameters.")
    return {
        **base,
        "phase": "Phase R.3",
        "principle": "Phase R.3 expands the focused rotation sweep and asks whether the good region is enclosed, rather than just finding a best point on the current boundary.",
        "closure": closure,
        "next_scan_suggestion": suggestion,
        "ratings": {
            **dict(base.get("ratings", {})),
            "closure": _rating(float(closure.get("closure_score", 0.0))),
        },
        "recommendations": recommendations,
    }
