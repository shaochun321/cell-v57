from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
import math

import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def _sign(value: float, eps: float = 1e-6) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _cv(values: list[float]) -> float:
    vals = [abs(float(v)) for v in values]
    mean_val = _mean(vals)
    if mean_val <= 1e-9:
        return 0.0
    return float(_std(vals) / mean_val)


def _expected_protocol(case_name: str) -> dict[str, Any]:
    sign = 1 if "_pos_" in case_name or case_name.endswith("_pos") else (-1 if "_neg_" in case_name or case_name.endswith("_neg") else 0)
    variant = "soft" if case_name.endswith("_soft") else "base"
    if case_name.startswith("translation_"):
        axis = "x" if "_x_" in case_name else ("y" if "_y_" in case_name else "z")
        return {"mode": "translation", "axis": axis, "sign": sign, "variant": variant}
    if case_name.startswith("rotation_"):
        axis = "x" if "_x_" in case_name else ("y" if "_y_" in case_name else "z")
        return {"mode": "rotation", "axis": axis, "sign": sign, "variant": variant}
    return {"mode": "static", "axis": None, "sign": 0, "variant": variant}


def _extract_track_metrics(case_name: str, case_payload: dict[str, Any], track_name: str) -> dict[str, Any]:
    expected = _expected_protocol(case_name)
    motif_report = dict(case_payload.get("motif_report", {}).get("tracks", {}).get(track_name, {}))
    active_families = dict(motif_report.get("active_family_means", {}))
    axial_margin = float(active_families.get("axial_polar_family", 0.0) - active_families.get("swirl_circulation_family", 0.0))
    axis_balance = dict(motif_report.get("active_axis_balance", {}))
    stable_substructures = [str(item.get("signature", "")) for item in motif_report.get("stable_substructures", []) if item.get("signature")]
    signature_counts = list(motif_report.get("active_top_repeated_signatures", []))
    top_signature = str(signature_counts[0].get("signature", "")) if signature_counts else ""
    return {
        "case_name": case_name,
        "track_name": track_name,
        "expected": expected,
        "axial_margin": axial_margin,
        "swirl_margin": -axial_margin,
        "axis_balance": {k: float(v) for k, v in axis_balance.items()},
        "signed_circulation": float(motif_report.get("active_signed_circulation", 0.0)),
        "stable_substructures": stable_substructures,
        "top_signature": top_signature,
        "active_motif_counts": dict(motif_report.get("active_motif_counts", {})),
        "active_family_means": {k: float(v) for k, v in active_families.items()},
    }


def _robust_signatures(metrics: list[dict[str, Any]], threshold_fraction: float = 0.6) -> list[dict[str, Any]]:
    if not metrics:
        return []
    counter = Counter(m["top_signature"] for m in metrics if m.get("top_signature"))
    needed = max(1, int(math.ceil(threshold_fraction * len(metrics))))
    return [
        {"signature": key, "count": int(count), "persistence": float(count / len(metrics))}
        for key, count in counter.items()
        if count >= needed
    ]


def _robust_substructures(metrics: list[dict[str, Any]], threshold_fraction: float = 0.6) -> list[dict[str, Any]]:
    if not metrics:
        return []
    counter = Counter(sig for metric in metrics for sig in metric.get("stable_substructures", []))
    needed = max(1, int(math.ceil(threshold_fraction * len(metrics))))
    return [
        {"signature": key, "count": int(count), "persistence": float(count / len(metrics))}
        for key, count in counter.items()
        if count >= needed
    ]


def _paired_separation_consistency(metrics: list[dict[str, Any]], value_getter) -> float:
    if not metrics:
        return 0.0
    by_variant = defaultdict(dict)
    for m in metrics:
        by_variant[m["expected"]["variant"]][int(m["expected"]["sign"])] = m
    scores = []
    for variant, sign_map in by_variant.items():
        if 1 in sign_map and -1 in sign_map:
            pos_val = float(value_getter(sign_map[1]))
            neg_val = float(value_getter(sign_map[-1]))
            scores.append(1.0 if _sign(pos_val) == -_sign(neg_val) and _sign(pos_val) != 0 else 0.0)
    return float(_mean(scores)) if scores else 0.0


def _summarize_group(metrics: list[dict[str, Any]], mode: str, axis: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "num_cases": int(len(metrics)),
        "robust_signatures": _robust_signatures(metrics),
        "robust_substructures": _robust_substructures(metrics),
        "mean_abs_axial_margin": _mean([abs(m["axial_margin"]) for m in metrics]),
        "axial_margin_cv": _cv([m["axial_margin"] for m in metrics]),
        "mean_abs_signed_circulation": _mean([abs(m["signed_circulation"]) for m in metrics]),
        "signed_circulation_cv": _cv([m["signed_circulation"] for m in metrics]),
    }
    if mode == "translation":
        out.update({
            "axial_dominance_consistency": float(_mean([1.0 if m["axial_margin"] > 0.0 else 0.0 for m in metrics])),
            "polarity_consistency": float(_mean([
                1.0 if _sign(float(m["axis_balance"].get(axis or "x", 0.0))) == int(m["expected"]["sign"]) else 0.0
                for m in metrics
            ])),
            "polarity_separation_consistency": _paired_separation_consistency(metrics, lambda m: m["axis_balance"].get(axis or "x", 0.0)),
        })
    elif mode == "rotation":
        out.update({
            "swirl_dominance_consistency": float(_mean([1.0 if m["axial_margin"] < 0.0 else 0.0 for m in metrics])),
            "circulation_sign_consistency": float(_mean([
                1.0 if _sign(m["signed_circulation"]) == int(m["expected"]["sign"]) else 0.0
                for m in metrics
            ])),
            "circulation_separation_consistency": _paired_separation_consistency(metrics, lambda m: m["signed_circulation"]),
        })
    return out


def summarize_channel_invariants(protocol_report: dict[str, Any]) -> dict[str, Any]:
    per_track_metrics: dict[str, list[dict[str, Any]]] = {track_name: [] for track_name in TRACK_NAMES}
    for case_name, case_payload in protocol_report.items():
        for track_name in TRACK_NAMES:
            per_track_metrics[track_name].append(_extract_track_metrics(case_name, case_payload, track_name))

    tracks_summary: dict[str, Any] = {}
    for track_name, metrics in per_track_metrics.items():
        translation_metrics = [m for m in metrics if m["expected"]["mode"] == "translation"]
        rotation_metrics = [m for m in metrics if m["expected"]["mode"] == "rotation"]
        static_metrics = [m for m in metrics if m["expected"]["mode"] == "static"]
        translation_base = [m for m in translation_metrics if m["expected"]["variant"] == "base"]
        translation_soft = [m for m in translation_metrics if m["expected"]["variant"] == "soft"]
        rotation_base = [m for m in rotation_metrics if m["expected"]["variant"] == "base"]
        rotation_soft = [m for m in rotation_metrics if m["expected"]["variant"] == "soft"]

        # Pairwise robustness between base and soft cases with the same mode/sign.
        pair_deltas = []
        by_key = defaultdict(dict)
        for m in metrics:
            key = (m["expected"]["mode"], m["expected"]["sign"])
            by_key[key][m["expected"]["variant"]] = m
        for key, variants in by_key.items():
            if "base" in variants and "soft" in variants:
                base = variants["base"]
                soft = variants["soft"]
                pair_deltas.append({
                    "mode": key[0],
                    "sign": int(key[1]),
                    "axial_margin_delta": float(abs(base["axial_margin"] - soft["axial_margin"])),
                    "axis_balance_delta": float(abs(base["axis_balance"].get("x", 0.0) - soft["axis_balance"].get("x", 0.0))),
                    "signed_circulation_delta": float(abs(base["signed_circulation"] - soft["signed_circulation"])),
                })

        tracks_summary[track_name] = {
            "num_cases": int(len(metrics)),
            "translation": _summarize_group(translation_metrics, "translation", axis="x"),
            "rotation": _summarize_group(rotation_metrics, "rotation", axis="z"),
            "static": {
                "num_cases": int(len(static_metrics)),
                "mean_abs_axial_margin": _mean([abs(m["axial_margin"]) for m in static_metrics]),
                "mean_abs_signed_circulation": _mean([abs(m["signed_circulation"]) for m in static_metrics]),
            },
            "translation_base": _summarize_group(translation_base, "translation", axis="x"),
            "translation_soft": _summarize_group(translation_soft, "translation", axis="x"),
            "rotation_base": _summarize_group(rotation_base, "rotation", axis="z"),
            "rotation_soft": _summarize_group(rotation_soft, "rotation", axis="z"),
            "parameter_pair_deltas": pair_deltas,
            "invariants": {
                "translation_axial_invariant": bool(_summarize_group(translation_metrics, "translation", axis="x").get("axial_dominance_consistency", 0.0) >= 0.75),
                "rotation_swirl_invariant": bool(_summarize_group(rotation_metrics, "rotation", axis="z").get("swirl_dominance_consistency", 0.0) >= 0.5),
                "translation_sign_invariant": bool(_summarize_group(translation_metrics, "translation", axis="x").get("polarity_separation_consistency", 0.0) >= 0.75),
                "rotation_sign_invariant": bool(_summarize_group(rotation_metrics, "rotation", axis="z").get("circulation_separation_consistency", 0.0) >= 0.75),
            },
        }
    return {
        "track_names": TRACK_NAMES,
        "principle": "cross-protocol and cross-parameter motif stability audit; invariants are computed externally from channel motif summaries rather than embedded into the cell sphere or interface channels",
        "tracks": tracks_summary,
    }
