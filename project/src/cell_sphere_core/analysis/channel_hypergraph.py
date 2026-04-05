from __future__ import annotations

from typing import Any
import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES, FAMILY_NAMES

AXES = ("x", "y", "z")


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _safe_list(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    return [float(v) for v in values]


def _family_shell_mean(track_payload: dict[str, Any], family_name: str) -> tuple[list[float], float]:
    family_payload = dict(track_payload.get("family_trajectories", {}).get(family_name, {}))
    shell_profile = _safe_list(family_payload.get("shell_profile", []))
    return shell_profile, _mean(shell_profile)


def _dominant_axis(balance: dict[str, Any]) -> str:
    vals = {axis: abs(float(balance.get(axis, 0.0))) for axis in AXES}
    return max(vals, key=vals.get) if vals else "x"


def _source_axis(vector: list[float]) -> str:
    arr = np.asarray(vector, dtype=np.float64)
    if arr.size != 3:
        return "x"
    return AXES[int(np.argmax(np.abs(arr)))]


def _track_snapshot(track_name: str, track_payload: dict[str, Any]) -> dict[str, Any]:
    family_means: dict[str, float] = {}
    family_shell_profiles: dict[str, list[float]] = {}
    family_attenuation: dict[str, dict[str, float]] = {}
    for family_name in FAMILY_NAMES:
        shell_profile, mean_level = _family_shell_mean(track_payload, family_name)
        family_shell_profiles[family_name] = shell_profile
        family_means[family_name] = mean_level
        family_attenuation[family_name] = dict(track_payload.get("family_trajectories", {}).get(family_name, {}).get("attenuation", {}))

    transfer_shell_profile = _safe_list(track_payload.get("transfer_shell_profile", []))
    bandwidth_shell_profile = _safe_list(track_payload.get("bandwidth_shell_profile", []))
    axis_balance = {axis: float(track_payload.get("axis_polarity_balance", {}).get(axis, 0.0)) for axis in AXES}
    signed_circulation = float(track_payload.get("signed_circulation", 0.0))
    direction_vector = list(track_payload.get("source_direction_vector", [0.0, 0.0, 0.0]))
    circulation_vector = list(track_payload.get("source_circulation_vector", [0.0, 0.0, 0.0]))

    max_shells = max([
        len(transfer_shell_profile),
        len(bandwidth_shell_profile),
        *[len(v) for v in family_shell_profiles.values()],
        0,
    ])

    nodes: list[dict[str, Any]] = []
    nodes.append({"id": f"track::{track_name}", "kind": "track", "track_name": track_name})
    for family_name in FAMILY_NAMES:
        nodes.append({
            "id": f"family::{track_name}::{family_name}",
            "kind": "family",
            "track_name": track_name,
            "family_name": family_name,
            "response_mean": family_means[family_name],
            "peak_shell_index": int(family_attenuation[family_name].get("peak_shell_index", 0)),
            "centroid_shell_index": float(family_attenuation[family_name].get("centroid_shell_index", 0.0)),
            "attenuation_index": float(family_attenuation[family_name].get("attenuation_index", 0.0)),
        })
    for shell_index in range(max_shells):
        nodes.append({
            "id": f"shell::{track_name}::{shell_index}",
            "kind": "shell",
            "track_name": track_name,
            "shell_index": int(shell_index),
            "transfer_level": float(transfer_shell_profile[shell_index]) if shell_index < len(transfer_shell_profile) else 0.0,
            "bandwidth_level": float(bandwidth_shell_profile[shell_index]) if shell_index < len(bandwidth_shell_profile) else 0.0,
        })
    for axis in AXES:
        nodes.append({
            "id": f"axis::{track_name}::{axis}",
            "kind": "axis",
            "track_name": track_name,
            "axis": axis,
            "polarity_balance": axis_balance[axis],
        })

    edges: list[dict[str, Any]] = []
    for family_name in FAMILY_NAMES:
        edges.append({
            "id": f"edge::track-family::{track_name}::{family_name}",
            "kind": "track_to_family",
            "source": f"track::{track_name}",
            "target": f"family::{track_name}::{family_name}",
            "strength": family_means[family_name],
        })
        for shell_index, value in enumerate(family_shell_profiles[family_name]):
            edges.append({
                "id": f"edge::family-shell::{track_name}::{family_name}::{shell_index}",
                "kind": "family_to_shell",
                "source": f"family::{track_name}::{family_name}",
                "target": f"shell::{track_name}::{shell_index}",
                "strength": float(value),
            })
    for shell_index in range(max(0, max_shells - 1)):
        left = float(transfer_shell_profile[shell_index]) if shell_index < len(transfer_shell_profile) else 0.0
        right = float(transfer_shell_profile[shell_index + 1]) if shell_index + 1 < len(transfer_shell_profile) else 0.0
        attenuation = max(left - right, 0.0)
        edges.append({
            "id": f"edge::shell-shell::{track_name}::{shell_index}",
            "kind": "shell_to_shell",
            "source": f"shell::{track_name}::{shell_index}",
            "target": f"shell::{track_name}::{shell_index + 1}",
            "strength": 0.5 * (left + right),
            "attenuation": float(attenuation),
        })
    for axis in AXES:
        edges.append({
            "id": f"edge::axis-polar::{track_name}::{axis}",
            "kind": "axis_to_family",
            "source": f"axis::{track_name}::{axis}",
            "target": f"family::{track_name}::axial_polar_family",
            "strength": abs(axis_balance[axis]),
            "signed_strength": axis_balance[axis],
        })
    circ_axis = _source_axis(circulation_vector)
    edges.append({
        "id": f"edge::axis-swirl::{track_name}::{circ_axis}",
        "kind": "axis_to_family",
        "source": f"axis::{track_name}::{circ_axis}",
        "target": f"family::{track_name}::swirl_circulation_family",
        "strength": abs(signed_circulation),
        "signed_strength": signed_circulation,
    })

    hyperedges: list[dict[str, Any]] = []
    for family_name in FAMILY_NAMES:
        shell_members = [f"shell::{track_name}::{i}" for i in range(len(family_shell_profiles[family_name]))]
        hyperedges.append({
            "id": f"hyperedge::family-shell-path::{track_name}::{family_name}",
            "kind": "family_shell_path",
            "members": [f"track::{track_name}", f"family::{track_name}::{family_name}", *shell_members],
            "family_name": family_name,
            "shell_weights": family_shell_profiles[family_name],
            "peak_shell_index": int(family_attenuation[family_name].get("peak_shell_index", 0)),
            "centroid_shell_index": float(family_attenuation[family_name].get("centroid_shell_index", 0.0)),
        })
    hyperedges.append({
        "id": f"hyperedge::axis-polarity::{track_name}",
        "kind": "axis_polarity_bundle",
        "members": [f"track::{track_name}", *(f"axis::{track_name}::{axis}" for axis in AXES), f"family::{track_name}::axial_polar_family"],
        "axis_balance": axis_balance,
        "dominant_axis": _dominant_axis(axis_balance),
        "source_direction_axis": _source_axis(direction_vector),
    })
    hyperedges.append({
        "id": f"hyperedge::swirl-circulation::{track_name}",
        "kind": "swirl_circulation_bundle",
        "members": [f"track::{track_name}", *(f"axis::{track_name}::{axis}" for axis in AXES), f"family::{track_name}::swirl_circulation_family"],
        "signed_circulation": signed_circulation,
        "source_circulation_axis": circ_axis,
    })
    hyperedges.append({
        "id": f"hyperedge::transmission-shells::{track_name}",
        "kind": "transmission_shells",
        "members": [f"track::{track_name}", *(f"shell::{track_name}::{i}" for i in range(len(transfer_shell_profile)))],
        "shell_transfer": transfer_shell_profile,
        "shell_bandwidth": bandwidth_shell_profile,
    })

    return {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": hyperedges,
        "family_means": family_means,
        "axis_balance": axis_balance,
        "signed_circulation": signed_circulation,
        "transfer_shell_profile": transfer_shell_profile,
        "bandwidth_shell_profile": bandwidth_shell_profile,
    }


def build_channel_hypergraph_trace(interface_temporal_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in interface_temporal_trace:
        tracks = row.get("tracks", {})
        track_snapshots = {track_name: _track_snapshot(track_name, tracks.get(track_name, {})) for track_name in TRACK_NAMES}
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "hypergraph_structure": {
                "principle": "temporal attributed hypergraph view of channel topology; channels and interface bundles transduce under physical constraints but do not perform semantic recognition",
                "node_types": ["track", "family", "shell", "axis"],
                "edge_types": ["track_to_family", "family_to_shell", "shell_to_shell", "axis_to_family"],
                "hyperedge_types": ["family_shell_path", "axis_polarity_bundle", "swirl_circulation_bundle", "transmission_shells"],
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
            },
            "tracks": track_snapshots,
        })
    return rows


def _summarize_track(trace: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    rows = [row.get("tracks", {}).get(track_name, {}) for row in trace]
    active_rows = [row.get("tracks", {}).get(track_name, {}) for row in trace if bool(row.get("stimulus_active", False))]

    def _family_mean(payloads: list[dict[str, Any]], family_name: str) -> float:
        return _mean([float(p.get("family_means", {}).get(family_name, 0.0)) for p in payloads])

    def _axis_mean(payloads: list[dict[str, Any]], axis: str) -> float:
        return _mean([float(p.get("axis_balance", {}).get(axis, 0.0)) for p in payloads])

    def _signed_circ(payloads: list[dict[str, Any]]) -> float:
        return _mean([float(p.get("signed_circulation", 0.0)) for p in payloads])

    def _count(payloads: list[dict[str, Any]], key: str) -> float:
        return _mean([float(len(p.get(key, []))) for p in payloads])

    def _family_shell_sum(payloads: list[dict[str, Any]], family_name: str) -> float:
        vals = []
        for p in payloads:
            for hyper in p.get("hyperedges", []):
                if hyper.get("kind") == "family_shell_path" and hyper.get("family_name") == family_name:
                    vals.append(_mean([float(v) for v in hyper.get("shell_weights", [])]))
        return _mean(vals)

    return {
        "num_samples": int(len(rows)),
        "active_num_samples": int(len(active_rows)),
        "mean_node_count": _count(rows, "nodes"),
        "mean_edge_count": _count(rows, "edges"),
        "mean_hyperedge_count": _count(rows, "hyperedges"),
        "active_family_means": {family_name: _family_mean(active_rows, family_name) for family_name in FAMILY_NAMES},
        "active_family_shell_weight_mean": {family_name: _family_shell_sum(active_rows, family_name) for family_name in FAMILY_NAMES},
        "active_axis_balance": {axis: _axis_mean(active_rows, axis) for axis in AXES},
        "active_signed_circulation": _signed_circ(active_rows),
        "active_transfer_strength_mean": _mean([_mean([float(v) for v in p.get("transfer_shell_profile", [])]) for p in active_rows]),
        "active_bandwidth_strength_mean": _mean([_mean([float(v) for v in p.get("bandwidth_shell_profile", [])]) for p in active_rows]),
    }


def summarize_channel_hypergraph_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
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
