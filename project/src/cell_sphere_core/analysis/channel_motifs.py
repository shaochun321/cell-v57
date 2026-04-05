from __future__ import annotations

from collections import Counter
from typing import Any
import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES, FAMILY_NAMES

AXES = ("x", "y", "z")


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _sign_label(value: float, pos: str, neg: str, eps: float = 1e-6) -> str | None:
    if value > eps:
        return pos
    if value < -eps:
        return neg
    return None


def _dominant_axis(balance: dict[str, Any]) -> str:
    vals = {axis: abs(float(balance.get(axis, 0.0))) for axis in AXES}
    return max(vals, key=vals.get) if vals else "x"


def _family_shell_signature(hyperedges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    motifs: list[dict[str, Any]] = []
    stable_candidates: list[dict[str, Any]] = []
    for hyper in hyperedges:
        if hyper.get("kind") != "family_shell_path":
            continue
        family_name = str(hyper.get("family_name", ""))
        peak_shell = int(hyper.get("peak_shell_index", 0))
        centroid = float(hyper.get("centroid_shell_index", 0.0))
        weights = [float(v) for v in hyper.get("shell_weights", [])]
        avg_weight = _mean(weights)
        signature = f"{family_name}@peak{peak_shell}"
        motifs.append({
            "motif_type": "family_shell_path",
            "signature": signature,
            "family_name": family_name,
            "peak_shell_index": peak_shell,
            "centroid_shell_index": centroid,
            "mean_shell_weight": avg_weight,
        })
        if avg_weight > 0.05:
            stable_candidates.append({
                "substructure_type": "family_shell_core",
                "signature": signature,
                "family_name": family_name,
                "peak_shell_index": peak_shell,
                "strength": avg_weight,
            })
    return motifs, stable_candidates


def _edge_attenuation_summary(edges: list[dict[str, Any]]) -> dict[str, float]:
    vals = [float(edge.get("attenuation", 0.0)) for edge in edges if edge.get("kind") == "shell_to_shell"]
    return {
        "mean_shell_attenuation": _mean(vals),
        "max_shell_attenuation": float(max(vals)) if vals else 0.0,
    }


def _track_motif_snapshot(track_name: str, track_payload: dict[str, Any]) -> dict[str, Any]:
    family_means = {name: float(track_payload.get("family_means", {}).get(name, 0.0)) for name in FAMILY_NAMES}
    axis_balance = {axis: float(track_payload.get("axis_balance", {}).get(axis, 0.0)) for axis in AXES}
    signed_circulation = float(track_payload.get("signed_circulation", 0.0))
    transfer_profile = [float(v) for v in track_payload.get("transfer_shell_profile", [])]
    bandwidth_profile = [float(v) for v in track_payload.get("bandwidth_shell_profile", [])]
    nodes = list(track_payload.get("nodes", []))
    edges = list(track_payload.get("edges", []))
    hyperedges = list(track_payload.get("hyperedges", []))

    dominant_family = max(family_means, key=family_means.get) if family_means else "structural_tonic_family"
    dominant_axis = _dominant_axis(axis_balance)
    axial_minus_swirl = float(family_means.get("axial_polar_family", 0.0) - family_means.get("swirl_circulation_family", 0.0))

    motif_labels: list[str] = []
    if axial_minus_swirl > 0.0:
        motif_labels.append("axial_path_motif")
    elif axial_minus_swirl < 0.0:
        motif_labels.append("swirl_loop_motif")

    for axis in AXES:
        label = _sign_label(axis_balance[axis], f"{axis}_positive_polarity_motif", f"{axis}_negative_polarity_motif")
        if label:
            motif_labels.append(label)
    circ_label = _sign_label(signed_circulation, "positive_circulation_motif", "negative_circulation_motif")
    if circ_label:
        motif_labels.append(circ_label)

    family_shell_motifs, stable_substructures = _family_shell_signature(hyperedges)
    attenuation_summary = _edge_attenuation_summary(edges)
    if attenuation_summary["mean_shell_attenuation"] > 0.0:
        motif_labels.append("attenuation_chain_motif")
        stable_substructures.append({
            "substructure_type": "attenuation_chain",
            "signature": f"{track_name}@atten{attenuation_summary['mean_shell_attenuation']:.3f}",
            "strength": attenuation_summary["mean_shell_attenuation"],
        })
    transfer_peak_shell = int(np.argmax(transfer_profile)) if transfer_profile else 0
    bandwidth_peak_shell = int(np.argmax(bandwidth_profile)) if bandwidth_profile else 0
    stable_substructures.append({
        "substructure_type": "transfer_peak_shell",
        "signature": f"transfer_peak@{transfer_peak_shell}",
        "peak_shell_index": transfer_peak_shell,
        "strength": float(transfer_profile[transfer_peak_shell]) if transfer_profile else 0.0,
    })
    stable_substructures.append({
        "substructure_type": "bandwidth_peak_shell",
        "signature": f"bandwidth_peak@{bandwidth_peak_shell}",
        "peak_shell_index": bandwidth_peak_shell,
        "strength": float(bandwidth_profile[bandwidth_peak_shell]) if bandwidth_profile else 0.0,
    })

    motif_signature = {
        "dominant_family": dominant_family,
        "dominant_axis": dominant_axis,
        "circulation_sign": 1 if signed_circulation > 0.0 else (-1 if signed_circulation < 0.0 else 0),
        "transfer_peak_shell": transfer_peak_shell,
        "bandwidth_peak_shell": bandwidth_peak_shell,
    }

    return {
        "track_name": track_name,
        "dominant_family": dominant_family,
        "dominant_axis": dominant_axis,
        "motif_signature": motif_signature,
        "motif_labels": motif_labels,
        "family_shell_motifs": family_shell_motifs,
        "stable_substructures": stable_substructures,
        "attenuation_summary": attenuation_summary,
        "family_means": family_means,
        "axis_balance": axis_balance,
        "signed_circulation": signed_circulation,
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "hyperedge_count": int(len(hyperedges)),
    }


def build_channel_motif_trace(channel_hypergraph_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in channel_hypergraph_trace:
        tracks = row.get("tracks", {})
        payload = {track_name: _track_motif_snapshot(track_name, tracks.get(track_name, {})) for track_name in TRACK_NAMES}
        out.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "motif_structure": {
                "principle": "stable substructures and repeated higher-order propagation motifs extracted externally from the channel hypergraph; motifs summarize physical transduction structure and do not perform semantic recognition",
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
                "motif_label_examples": [
                    "axial_path_motif",
                    "swirl_loop_motif",
                    "x_positive_polarity_motif",
                    "positive_circulation_motif",
                    "attenuation_chain_motif",
                ],
            },
            "tracks": payload,
        })
    return out


def _summarize_track(trace: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    rows = [row.get("tracks", {}).get(track_name, {}) for row in trace]
    active_rows = [row.get("tracks", {}).get(track_name, {}) for row in trace if bool(row.get("stimulus_active", False))]
    motif_counter = Counter()
    active_motif_counter = Counter()
    signature_counter = Counter()
    active_signature_counter = Counter()
    substructure_counter = Counter()
    active_substructure_counter = Counter()
    signature_run_max = Counter()
    last_signature = None
    current_run = 0
    for row in rows:
        labels = list(row.get("motif_labels", []))
        motif_counter.update(labels)
        signature = json_like_signature(row.get("motif_signature", {}))
        signature_counter[signature] += 1
        if signature == last_signature:
            current_run += 1
        else:
            if last_signature is not None:
                signature_run_max[last_signature] = max(signature_run_max[last_signature], current_run)
            last_signature = signature
            current_run = 1
        for sub in row.get("stable_substructures", []):
            substructure_counter[sub.get("signature", "")] += 1
    if last_signature is not None:
        signature_run_max[last_signature] = max(signature_run_max[last_signature], current_run)

    for row in active_rows:
        active_motif_counter.update(list(row.get("motif_labels", [])))
        active_signature_counter[json_like_signature(row.get("motif_signature", {}))] += 1
        for sub in row.get("stable_substructures", []):
            active_substructure_counter[sub.get("signature", "")] += 1

    def _top(counter: Counter, limit: int = 6) -> list[dict[str, Any]]:
        return [{"signature": key, "count": int(count)} for key, count in counter.most_common(limit)]

    stable_threshold = max(2, int(np.ceil(0.5 * max(1, len(active_rows)))))
    stable_substructures = [
        {"signature": key, "active_count": int(count), "persistence": float(count / max(1, len(active_rows)))}
        for key, count in active_substructure_counter.items()
        if count >= stable_threshold
    ]

    return {
        "num_samples": int(len(rows)),
        "active_num_samples": int(len(active_rows)),
        "motif_counts": {key: int(val) for key, val in motif_counter.items()},
        "active_motif_counts": {key: int(val) for key, val in active_motif_counter.items()},
        "top_repeated_signatures": _top(signature_counter),
        "active_top_repeated_signatures": _top(active_signature_counter),
        "stable_substructures": stable_substructures,
        "top_substructures": _top(substructure_counter),
        "active_top_substructures": _top(active_substructure_counter),
        "longest_signature_runs": [{"signature": key, "run_length": int(val)} for key, val in signature_run_max.most_common(6)],
        "mean_edge_count": _mean([float(row.get("edge_count", 0.0)) for row in rows]),
        "mean_hyperedge_count": _mean([float(row.get("hyperedge_count", 0.0)) for row in rows]),
        "active_signed_circulation": _mean([float(row.get("signed_circulation", 0.0)) for row in active_rows]),
        "active_axis_balance": {axis: _mean([float(row.get("axis_balance", {}).get(axis, 0.0)) for row in active_rows]) for axis in AXES},
        "active_family_means": {family: _mean([float(row.get("family_means", {}).get(family, 0.0)) for row in active_rows]) for family in FAMILY_NAMES},
    }


def json_like_signature(payload: dict[str, Any]) -> str:
    dom_family = str(payload.get("dominant_family", "none"))
    dom_axis = str(payload.get("dominant_axis", "x"))
    circ_sign = int(payload.get("circulation_sign", 0))
    transfer_peak = int(payload.get("transfer_peak_shell", 0))
    bandwidth_peak = int(payload.get("bandwidth_peak_shell", 0))
    return f"{dom_family}|{dom_axis}|circ{circ_sign}|tp{transfer_peak}|bp{bandwidth_peak}"


def summarize_channel_motif_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "track_names": TRACK_NAMES,
            "family_names": FAMILY_NAMES,
            "tracks": {track_name: _summarize_track([], track_name) for track_name in TRACK_NAMES},
        }
    return {
        "num_samples": int(len(trace)),
        "track_names": TRACK_NAMES,
        "family_names": FAMILY_NAMES,
        "tracks": {track_name: _summarize_track(trace, track_name) for track_name in TRACK_NAMES},
    }
