from __future__ import annotations

from typing import Any
import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES, FAMILY_NAMES


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _argmax_index(values: list[float]) -> int:
    if not values:
        return 0
    return int(np.argmax(np.asarray(values, dtype=np.float64)))


def _response_grid(track_payload: dict[str, Any], family_name: str) -> np.ndarray:
    grid = np.asarray(track_payload.get("response_atlas", {}).get("families", {}).get(family_name, []), dtype=np.float64)
    if grid.ndim != 2:
        return np.zeros((0, 0), dtype=np.float64)
    return grid


def _shell_profile(grid: np.ndarray) -> list[float]:
    if grid.size == 0:
        return []
    return [float(v) for v in np.mean(grid, axis=1).tolist()]


def _sector_profile(grid: np.ndarray) -> list[float]:
    if grid.size == 0:
        return []
    return [float(v) for v in np.mean(grid, axis=0).tolist()]


def _attenuation_metrics(shell_profile: list[float]) -> dict[str, float]:
    if not shell_profile:
        return {
            "inner_level": 0.0,
            "outer_level": 0.0,
            "outer_inner_ratio": 0.0,
            "attenuation_index": 0.0,
            "shell_gradient_mean": 0.0,
            "shell_gradient_std": 0.0,
            "peak_shell_index": 0,
            "centroid_shell_index": 0.0,
        }
    inner = float(shell_profile[0])
    outer = float(shell_profile[-1])
    ratio = float(outer / max(inner, 1e-6))
    attenuation = float(np.clip(1.0 - ratio, -4.0, 4.0))
    grads = np.diff(np.asarray(shell_profile, dtype=np.float64)) if len(shell_profile) > 1 else np.zeros(0, dtype=np.float64)
    shell_idx = np.arange(len(shell_profile), dtype=np.float64)
    profile_arr = np.asarray(shell_profile, dtype=np.float64)
    centroid = float(np.sum(shell_idx * profile_arr) / max(float(np.sum(profile_arr)), 1e-6))
    return {
        "inner_level": inner,
        "outer_level": outer,
        "outer_inner_ratio": ratio,
        "attenuation_index": attenuation,
        "shell_gradient_mean": float(np.mean(grads)) if grads.size else 0.0,
        "shell_gradient_std": float(np.std(grads)) if grads.size else 0.0,
        "peak_shell_index": int(np.argmax(profile_arr)) if profile_arr.size else 0,
        "centroid_shell_index": centroid,
    }


def _family_payload(track_payload: dict[str, Any], family_name: str) -> dict[str, Any]:
    grid = _response_grid(track_payload, family_name)
    shell_profile = _shell_profile(grid)
    sector_profile = _sector_profile(grid)
    attenuation = _attenuation_metrics(shell_profile)
    return {
        "shell_profile": shell_profile,
        "sector_profile": sector_profile,
        "attenuation": attenuation,
    }


def _track_payload(track_payload: dict[str, Any]) -> dict[str, Any]:
    families = {family_name: _family_payload(track_payload, family_name) for family_name in FAMILY_NAMES}
    response_atlas = track_payload.get("response_atlas", {})
    transfer_map = np.asarray(response_atlas.get("transfer_map", []), dtype=np.float64)
    bandwidth_map = np.asarray(response_atlas.get("bandwidth_map", []), dtype=np.float64)
    family_topology = dict(track_payload.get("family_topology", {}))
    return {
        "family_trajectories": families,
        "transfer_shell_profile": _shell_profile(transfer_map),
        "bandwidth_shell_profile": _shell_profile(bandwidth_map),
        "transfer_attenuation": _attenuation_metrics(_shell_profile(transfer_map)),
        "bandwidth_attenuation": _attenuation_metrics(_shell_profile(bandwidth_map)),
        "axis_polarity_balance": family_topology.get("polarity_by_axis", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "signed_circulation": float(family_topology.get("signed_circulation", 0.0)),
        "source_direction_vector": track_payload.get("source_direction_vector", [0.0, 0.0, 0.0]),
        "source_circulation_vector": track_payload.get("source_circulation_vector", [0.0, 0.0, 0.0]),
    }


def build_interface_temporal_trace(interface_topology_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in interface_topology_trace:
        tracks = row.get("tracks", {})
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "temporal_structure": {
                "principle": "time-varying propagation and attenuation atlas of transduced interface families; no semantic recognition embedded in the channels",
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
            },
            "tracks": {
                track_name: _track_payload(tracks.get(track_name, {}))
                for track_name in TRACK_NAMES
            },
        })
    return rows


def _family_summary(rows: list[dict[str, Any]], family_name: str) -> dict[str, Any]:
    shell_profiles = [r.get("family_trajectories", {}).get(family_name, {}).get("shell_profile", []) for r in rows]
    max_shells = max((len(p) for p in shell_profiles), default=0)
    shell_means = []
    for idx in range(max_shells):
        vals = [float(p[idx]) for p in shell_profiles if len(p) > idx]
        shell_means.append(_mean(vals))
    attenuation_rows = [r.get("family_trajectories", {}).get(family_name, {}).get("attenuation", {}) for r in rows]
    peak_idx = [int(a.get("peak_shell_index", 0)) for a in attenuation_rows]
    centroid = [float(a.get("centroid_shell_index", 0.0)) for a in attenuation_rows]
    ratios = [float(a.get("outer_inner_ratio", 0.0)) for a in attenuation_rows]
    atten = [float(a.get("attenuation_index", 0.0)) for a in attenuation_rows]
    gradients = [float(a.get("shell_gradient_mean", 0.0)) for a in attenuation_rows]
    inner = [float(a.get("inner_level", 0.0)) for a in attenuation_rows]
    outer = [float(a.get("outer_level", 0.0)) for a in attenuation_rows]
    return {
        "shell_profile_mean": shell_means,
        "mean_inner_level": _mean(inner),
        "mean_outer_level": _mean(outer),
        "mean_outer_inner_ratio": _mean(ratios),
        "mean_attenuation_index": _mean(atten),
        "attenuation_index_std": _std(atten),
        "mean_shell_gradient": _mean(gradients),
        "mean_peak_shell_index": _mean([float(v) for v in peak_idx]),
        "peak_shell_index_mode": _argmax_index([peak_idx.count(i) for i in range(max(peak_idx, default=0) + 1)]) if peak_idx else 0,
        "mean_centroid_shell_index": _mean(centroid),
    }


def _first_time_max(rows: list[dict[str, Any]], family_name: str) -> float:
    if not rows:
        return 0.0
    values = []
    for r in rows:
        att = r.get("family_trajectories", {}).get(family_name, {}).get("attenuation", {})
        values.append(float(att.get("outer_level", 0.0)))
    idx = int(np.argmax(np.asarray(values, dtype=np.float64))) if values else 0
    return float(rows[idx].get("_time", 0.0))


def _summarize_track(trace: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    track_rows = []
    active_rows = []
    post_rows = []
    for row in trace:
        payload = dict(row.get("tracks", {}).get(track_name, {}))
        payload["_time"] = float(row.get("time", 0.0))
        track_rows.append(payload)
        if bool(row.get("stimulus_active", False)):
            active_rows.append(payload)
        elif str(row.get("transition_state", "")).startswith("post_") or str(row.get("transition_state", "")).startswith("recovered"):
            post_rows.append(payload)

    def _channel_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        shell_profiles = [list(r.get(key, [])) for r in rows]
        max_shells = max((len(p) for p in shell_profiles), default=0)
        shell_means = []
        for idx in range(max_shells):
            vals = [float(p[idx]) for p in shell_profiles if len(p) > idx]
            shell_means.append(_mean(vals))
        att_rows = [r.get(f"{key.split('_shell_profile')[0]}_attenuation", {}) for r in rows]
        return {
            "shell_profile_mean": shell_means,
            "mean_attenuation_index": _mean([float(a.get("attenuation_index", 0.0)) for a in att_rows]),
            "attenuation_index_std": _std([float(a.get("attenuation_index", 0.0)) for a in att_rows]),
        }

    summary = {
        "num_samples": len(track_rows),
        "active_num_samples": len(active_rows),
        "post_num_samples": len(post_rows),
        "families": {family_name: _family_summary(track_rows, family_name) for family_name in FAMILY_NAMES},
        "active_families": {family_name: _family_summary(active_rows, family_name) for family_name in FAMILY_NAMES},
        "post_families": {family_name: _family_summary(post_rows, family_name) for family_name in FAMILY_NAMES},
        "transfer": _channel_summary(track_rows, "transfer_shell_profile"),
        "active_transfer": _channel_summary(active_rows, "transfer_shell_profile"),
        "bandwidth": _channel_summary(track_rows, "bandwidth_shell_profile"),
        "active_bandwidth": _channel_summary(active_rows, "bandwidth_shell_profile"),
        "active_peak_times": {family_name: _first_time_max(active_rows, family_name) for family_name in FAMILY_NAMES},
        "post_peak_times": {family_name: _first_time_max(post_rows, family_name) for family_name in FAMILY_NAMES},
        "mean_axis_polarity_balance": {axis: _mean([float(r.get("axis_polarity_balance", {}).get(axis, 0.0)) for r in track_rows]) for axis in ("x", "y", "z")},
        "active_mean_axis_polarity_balance": {axis: _mean([float(r.get("axis_polarity_balance", {}).get(axis, 0.0)) for r in active_rows]) for axis in ("x", "y", "z")},
        "mean_signed_circulation": _mean([float(r.get("signed_circulation", 0.0)) for r in track_rows]),
        "active_mean_signed_circulation": _mean([float(r.get("signed_circulation", 0.0)) for r in active_rows]),
    }
    return summary


def summarize_interface_temporal_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "num_samples": len(trace),
        "track_names": TRACK_NAMES,
        "family_names": FAMILY_NAMES,
        "tracks": {track_name: _summarize_track(trace, track_name) for track_name in TRACK_NAMES},
    }
