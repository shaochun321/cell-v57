from __future__ import annotations

from typing import Any
import numpy as np

CHANNEL_NAMES = [
    "slow_tonic",
    "medium_drive",
    "fast_event",
    "translation_signal",
    "rotation_signal",
    "polarity_signal",
    "electrical_potential",
    "burst_signal",
]

SECTOR_DIRS: dict[str, np.ndarray] = {
    "x_pos": np.asarray([1.0, 0.0, 0.0], dtype=np.float64),
    "x_neg": np.asarray([-1.0, 0.0, 0.0], dtype=np.float64),
    "y_pos": np.asarray([0.0, 1.0, 0.0], dtype=np.float64),
    "y_neg": np.asarray([0.0, -1.0, 0.0], dtype=np.float64),
    "z_pos": np.asarray([0.0, 0.0, 1.0], dtype=np.float64),
    "z_neg": np.asarray([0.0, 0.0, -1.0], dtype=np.float64),
}


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    if values.size == 0 or weights.size == 0:
        return 0.0
    total = float(np.sum(weights))
    if total <= 1e-12:
        return 0.0
    return float(np.sum(values * weights) / total)


def _bundle_from_layer(layer: dict[str, Any], sector_name: str, sector_dir: np.ndarray, process_row: dict[str, Any], readout_row: dict[str, Any]) -> dict[str, Any]:
    nodes = layer.get("nodes", [])
    if not nodes:
        weights = np.zeros(0, dtype=np.float64)
        unit_dirs = np.zeros((0, 3), dtype=np.float64)
        abs_u = abs_v = tang = force = gate = contact = signed_v = np.zeros(0, dtype=np.float64)
    else:
        pos_rel = np.asarray([node.get("pos_rel", [0.0, 0.0, 0.0]) for node in nodes], dtype=np.float64)
        norms = np.linalg.norm(pos_rel, axis=1)
        unit_dirs = np.zeros_like(pos_rel)
        valid = norms > 1e-12
        unit_dirs[valid] = pos_rel[valid] / norms[valid, None]
        weights = np.maximum(unit_dirs @ sector_dir, 0.0)
        abs_u = np.abs(np.asarray([float(node.get("u_r", 0.0)) for node in nodes], dtype=np.float64))
        abs_v = np.abs(np.asarray([float(node.get("v_r", 0.0)) for node in nodes], dtype=np.float64))
        signed_v = np.asarray([float(node.get("v_r", 0.0)) for node in nodes], dtype=np.float64)
        tang = np.asarray([float(node.get("tangential_speed", 0.0)) for node in nodes], dtype=np.float64)
        force = np.asarray([float(node.get("force_density", 0.0)) for node in nodes], dtype=np.float64)
        gate = np.asarray([float(node.get("gate", 0.0)) for node in nodes], dtype=np.float64)
        contact = np.asarray([float(node.get("contact", 0.0)) for node in nodes], dtype=np.float64)

    shell_idx = int(layer.get("band_index", 0))
    shell_name = f"mirror_shell_{shell_idx}"
    shell_factor = 0.55 + 0.15 * float(shell_idx)

    local_abs_u = _weighted_mean(abs_u, weights)
    local_abs_v = _weighted_mean(abs_v, weights)
    local_signed_v = _weighted_mean(signed_v, weights)
    local_tang = _weighted_mean(tang, weights)
    local_force = _weighted_mean(force, weights)
    local_gate = _weighted_mean(gate, weights)
    local_contact = _weighted_mean(contact, weights)

    dominant_axis = np.asarray(process_row.get("dominant_axis", [0.0, 0.0, 0.0]), dtype=np.float64)
    dominant_norm = float(np.linalg.norm(dominant_axis))
    dominant_axis = dominant_axis / dominant_norm if dominant_norm > 1e-12 else np.zeros(3, dtype=np.float64)
    polarity = float(dominant_axis @ sector_dir)
    dir_gain = max(polarity, 0.0)
    dir_mag = max(float(readout_row.get("translation_channel", 0.0)), float(readout_row.get("rotation_channel", 0.0)))

    slow_tonic = _clip01(
        0.42 * float(readout_row.get("static_channel", 0.0))
        + 0.20 * float(process_row.get("static_index", 0.0))
        + 0.15 * local_gate
        + 0.10 * float(process_row.get("shape_integrity_index", 0.0))
        + 0.08 * max(0.0, 1.0 - min(local_contact, 1.0))
        + 0.05 * max(0.0, 1.0 - min(local_abs_v * 5.0, 1.0))
    )
    medium_drive = _clip01(
        0.28 * float(readout_row.get("magnitude_channel", 0.0))
        + 0.24 * float(process_row.get("force_magnitude_index", 0.0))
        + 0.20 * min(local_force / 25.0, 1.0)
        + 0.16 * float(process_row.get("motion_index", 0.0))
        + 0.12 * min(local_abs_u * 20.0, 1.0)
    )
    fast_event = _clip01(
        0.34 * float(readout_row.get("onset_channel", 0.0))
        + 0.24 * float(readout_row.get("recovery_channel", 0.0))
        + 0.22 * min(abs(float(process_row.get("motion_delta", 0.0))) * 6.0, 1.0)
        + 0.20 * min(abs(local_signed_v) * 8.0, 1.0)
    )
    translation_signal = _clip01(
        float(readout_row.get("translation_channel", 0.0)) * (0.28 + 0.72 * dir_gain) * (0.85 + 0.15 * shell_factor)
        + 0.10 * min(local_abs_v * 4.0, 1.0)
    )
    rotation_signal = _clip01(
        float(readout_row.get("rotation_channel", 0.0)) * (0.25 + 0.75 * min(local_tang * 3.5, 1.0)) * (0.85 + 0.15 * shell_factor)
    )
    polarity_signal = float(np.clip(polarity * dir_mag, -1.0, 1.0))
    electrical_potential = _clip01(
        0.28 * slow_tonic + 0.24 * medium_drive + 0.18 * max(translation_signal, rotation_signal) + 0.16 * fast_event + 0.14 * abs(polarity_signal)
    )
    burst_signal = _clip01(0.60 * fast_event + 0.25 * medium_drive + 0.15 * max(translation_signal, rotation_signal))

    centroid = unit_dirs[np.argmax(weights)].tolist() if weights.size and np.any(weights > 0.0) else sector_dir.tolist()
    return {
        "bundle_id": f"{shell_name}_{sector_name}",
        "shell_index": shell_idx,
        "shell_name": shell_name,
        "sector": sector_name,
        "coupling_weight": float(np.mean(weights)) if weights.size else 0.0,
        "centroid_direction": [float(v) for v in centroid],
        "channels": {
            "slow_tonic": slow_tonic,
            "medium_drive": medium_drive,
            "fast_event": fast_event,
            "translation_signal": translation_signal,
            "rotation_signal": rotation_signal,
            "polarity_signal": polarity_signal,
            "electrical_potential": electrical_potential,
            "burst_signal": burst_signal,
        },
        "local_observables": {
            "abs_radial_disp": float(local_abs_u),
            "abs_radial_speed": float(local_abs_v),
            "tangential_speed": float(local_tang),
            "force_density": float(local_force),
            "gate": float(local_gate),
            "contact": float(local_contact),
        },
    }


def _aggregate_channels(bundles: list[dict[str, Any]]) -> dict[str, float]:
    if not bundles:
        return {"static": 0.0, "translation": 0.0, "rotation": 0.0, "event": 0.0, "magnitude": 0.0, "polarity_abs": 0.0}
    def _mean_channel(name: str) -> float:
        return float(np.mean([float(bundle["channels"].get(name, 0.0)) for bundle in bundles]))
    def _top_channel(name: str, fraction: float = 0.25) -> float:
        vals = sorted((float(bundle["channels"].get(name, 0.0)) for bundle in bundles), reverse=True)
        if not vals:
            return 0.0
        count = max(1, int(np.ceil(len(vals) * fraction)))
        return float(np.mean(vals[:count]))
    return {
        "static": _mean_channel("slow_tonic"),
        "translation": _top_channel("translation_signal", 0.25),
        "rotation": _top_channel("rotation_signal", 0.25),
        "event": _top_channel("fast_event", 0.25),
        "magnitude": _top_channel("medium_drive", 0.25),
        "polarity_abs": float(np.mean([abs(float(bundle["channels"].get("polarity_signal", 0.0))) for bundle in bundles])),
    }


def _direction_vector(bundles: list[dict[str, Any]]) -> list[float]:
    if not bundles:
        return [0.0, 0.0, 0.0]
    acc = np.zeros(3, dtype=np.float64)
    for bundle in bundles:
        sector = str(bundle.get("sector", ""))
        sign = -1.0 if sector.endswith("neg") else 1.0
        axis = sector[0] if sector else "x"
        vec = np.zeros(3, dtype=np.float64)
        vec[{"x": 0, "y": 1, "z": 2}.get(axis, 0)] = sign
        weight = abs(float(bundle["channels"].get("polarity_signal", 0.0))) + 0.20 * float(bundle["channels"].get("translation_signal", 0.0))
        acc += vec * weight
    norm = float(np.linalg.norm(acc))
    return [0.0, 0.0, 0.0] if norm <= 1e-12 else [float(v) for v in (acc / norm).tolist()]


def _classify_interface(aggregates: dict[str, float], stimulus_active: bool) -> tuple[str, float, float]:
    static = float(aggregates.get("static", 0.0))
    translation = float(aggregates.get("translation", 0.0))
    rotation = float(aggregates.get("rotation", 0.0))
    if stimulus_active:
        if translation >= rotation * 1.02 and translation >= 0.05:
            return "translation", translation, translation - rotation
        if rotation >= translation * 1.02 and rotation >= 0.05:
            return "rotation", rotation, rotation - translation
        if static >= max(translation, rotation):
            return "static", static, static - max(translation, rotation)
        return "mixed", max(static, translation, rotation), abs(translation - rotation)
    if static >= max(translation, rotation):
        return "static", static, static - max(translation, rotation)
    if translation > rotation * 1.04:
        return "translation", translation, translation - rotation
    if rotation > translation * 1.04:
        return "rotation", rotation, rotation - translation
    return "mixed", max(static, translation, rotation), abs(translation - rotation)


def build_mirror_interface_trace(sensor_nodes_trace: list[dict[str, Any]], process_trace: list[dict[str, Any]], readout_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for frame_row, process_row, readout_row in zip(sensor_nodes_trace, process_trace, readout_trace):
        bundles = []
        for layer in frame_row.get("layers", []):
            for sector_name, sector_dir in SECTOR_DIRS.items():
                bundles.append(_bundle_from_layer(layer, sector_name, sector_dir, process_row, readout_row))
        aggregates = _aggregate_channels(bundles)
        interface_class, confidence, margin = _classify_interface(aggregates, bool(readout_row.get("stimulus_active", False)))
        rows.append({
            "time": float(process_row.get("time", 0.0)),
            "stimulus_mode": process_row.get("stimulus_mode"),
            "stimulus_active": bool(process_row.get("stimulus_active", False)),
            "transition_state": process_row.get("transition_state", "baseline"),
            "mirror_structure": {
                "shell_count": int(len(frame_row.get("layers", []))),
                "sector_count": int(len(SECTOR_DIRS)),
                "bundle_channel_names": CHANNEL_NAMES,
                "topology": "concentric mirror shells x directional sectors",
            },
            "aggregate_channels": {k: float(v) for k, v in aggregates.items()},
            "direction_vector": _direction_vector(bundles),
            "interface_class": interface_class,
            "interface_confidence": _clip01(confidence),
            "interface_margin": float(max(margin, 0.0)),
            "interface_bundles": bundles,
        })
    return rows


def summarize_mirror_interface_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "dominant_interface_class": "none",
            "class_counts": {},
            "mean_static_channel": 0.0,
            "mean_translation_channel": 0.0,
            "mean_rotation_channel": 0.0,
            "mean_event_channel": 0.0,
            "mean_magnitude_channel": 0.0,
            "mean_interface_margin": 0.0,
            "bundle_channels": CHANNEL_NAMES,
            "mirror_topology": "concentric mirror shells x directional sectors",
            "active_summary": {},
        }

    def _mean_channel(rows: list[dict[str, Any]], key: str) -> float:
        return 0.0 if not rows else float(np.mean([float(row.get("aggregate_channels", {}).get(key, 0.0)) for row in rows]))

    def _count(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            label = str(row.get(key, "unknown"))
            counts[label] = counts.get(label, 0) + 1
        return counts

    class_counts = _count(trace, "interface_class")
    dominant = max(class_counts.items(), key=lambda kv: kv[1])[0]
    active_rows = [row for row in trace if bool(row.get("stimulus_active", False))]
    active_counts = _count(active_rows, "interface_class") if active_rows else {}
    active_dominant = max(active_counts.items(), key=lambda kv: kv[1])[0] if active_counts else "none"
    bundle_count = len(trace[0].get("interface_bundles", [])) if trace else 0

    all_bundles = [bundle for row in trace for bundle in row.get("interface_bundles", [])]
    grouped: dict[str, list[float]] = {}
    for bundle in all_bundles:
        grouped.setdefault(str(bundle.get("bundle_id", "bundle")), []).append(float(bundle.get("channels", {}).get("electrical_potential", 0.0)))
    ranked = sorted(grouped.items(), key=lambda kv: float(np.mean(kv[1])), reverse=True)[:8]
    top_bundles = [{"bundle_id": bundle_id, "mean_potential": float(np.mean(vals)), "peak_potential": float(np.max(vals))} for bundle_id, vals in ranked]

    summary = {
        "num_samples": int(len(trace)),
        "dominant_interface_class": dominant,
        "class_counts": class_counts,
        "mean_static_channel": _mean_channel(trace, "static"),
        "mean_translation_channel": _mean_channel(trace, "translation"),
        "mean_rotation_channel": _mean_channel(trace, "rotation"),
        "mean_event_channel": _mean_channel(trace, "event"),
        "mean_magnitude_channel": _mean_channel(trace, "magnitude"),
        "mean_interface_margin": float(np.mean([float(row.get("interface_margin", 0.0)) for row in trace])),
        "bundle_channels": CHANNEL_NAMES,
        "mirror_topology": "concentric mirror shells x directional sectors",
        "bundles_per_frame": int(bundle_count),
        "top_bundles": top_bundles,
        "active_summary": {
            "num_samples": int(len(active_rows)),
            "dominant_interface_class": active_dominant,
            "class_counts": active_counts,
            "mean_static_channel": _mean_channel(active_rows, "static"),
            "mean_translation_channel": _mean_channel(active_rows, "translation"),
            "mean_rotation_channel": _mean_channel(active_rows, "rotation"),
            "mean_event_channel": _mean_channel(active_rows, "event"),
            "mean_magnitude_channel": _mean_channel(active_rows, "magnitude"),
            "mean_interface_margin": float(np.mean([float(row.get("interface_margin", 0.0)) for row in active_rows])) if active_rows else 0.0,
        },
    }
    stimulus_mode = str(trace[0].get("stimulus_mode", "none") or "none")
    if stimulus_mode == "translation":
        summary["matched_channel_advantage"] = float(summary["active_summary"].get("mean_translation_channel", 0.0) - summary["active_summary"].get("mean_rotation_channel", 0.0))
    elif stimulus_mode == "rotation":
        summary["matched_channel_advantage"] = float(summary["active_summary"].get("mean_rotation_channel", 0.0) - summary["active_summary"].get("mean_translation_channel", 0.0))
    else:
        summary["matched_channel_advantage"] = float(summary["mean_static_channel"] - max(summary["mean_translation_channel"], summary["mean_rotation_channel"]))
    return summary
