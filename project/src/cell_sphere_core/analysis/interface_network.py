from __future__ import annotations

from typing import Any
import math
import numpy as np

TRACK_NAMES = [
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
]

CHANNEL_NAMES = [
    "deformation_drive",
    "vibration_drive",
    "event_flux",
    "dissipation_load",
    "axial_flux",
    "swirl_flux",
    "polarity_projection",
    "circulation_projection",
    "transfer_potential",
]

SIGNED_CHANNELS = {"polarity_projection", "circulation_projection"}

SECTOR_DIRS: dict[str, np.ndarray] = {
    "x_pos": np.asarray([1.0, 0.0, 0.0], dtype=np.float64),
    "x_neg": np.asarray([-1.0, 0.0, 0.0], dtype=np.float64),
    "y_pos": np.asarray([0.0, 1.0, 0.0], dtype=np.float64),
    "y_neg": np.asarray([0.0, -1.0, 0.0], dtype=np.float64),
    "z_pos": np.asarray([0.0, 0.0, 1.0], dtype=np.float64),
    "z_neg": np.asarray([0.0, 0.0, -1.0], dtype=np.float64),
}
SECTOR_ORDER = list(SECTOR_DIRS.keys())

CHANNEL_PARAMS: dict[str, dict[str, float]] = {
    "deformation_drive": {"persistence": 0.70, "lateral": 0.08, "radial": 0.05, "layer": 0.03, "global": 0.00, "boundary": 0.05},
    "vibration_drive": {"persistence": 0.35, "lateral": 0.12, "radial": 0.07, "layer": 0.04, "global": 0.02, "boundary": 0.08},
    "event_flux": {"persistence": 0.18, "lateral": 0.05, "radial": 0.03, "layer": 0.00, "global": 0.00, "boundary": 0.03},
    "dissipation_load": {"persistence": 0.82, "lateral": 0.05, "radial": 0.06, "layer": 0.05, "global": 0.03, "boundary": 0.04},
    "axial_flux": {"persistence": 0.44, "lateral": 0.12, "radial": 0.06, "layer": 0.04, "global": 0.02, "boundary": 0.08},
    "swirl_flux": {"persistence": 0.46, "lateral": 0.13, "radial": 0.08, "layer": 0.05, "global": 0.03, "boundary": 0.08},
    "polarity_projection": {"persistence": 0.42, "lateral": 0.10, "radial": 0.05, "layer": 0.02, "global": 0.00, "boundary": 0.06},
    "circulation_projection": {"persistence": 0.40, "lateral": 0.09, "radial": 0.06, "layer": 0.03, "global": 0.00, "boundary": 0.06},
    "transfer_potential": {"persistence": 0.62, "lateral": 0.11, "radial": 0.08, "layer": 0.08, "global": 0.05, "boundary": 0.07},
}


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _clip_signed(value: float) -> float:
    return float(np.clip(value, -1.0, 1.0))


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    if values.size == 0 or weights.size == 0:
        return 0.0
    total = float(np.sum(weights))
    if total <= 1e-12:
        return 0.0
    return float(np.sum(values * weights) / total)


def _weighted_vec_mean(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    if values.size == 0 or weights.size == 0:
        return np.zeros(3, dtype=np.float64)
    total = float(np.sum(weights))
    if total <= 1e-12:
        return np.zeros(3, dtype=np.float64)
    return np.sum(values * weights[:, None], axis=0) / total


def _scaled_abs(value: float, gain: float) -> float:
    return _clip01(abs(float(value)) * gain)


def _direction_vector(bundles: list[dict[str, Any]], channel: str = "polarity_projection") -> list[float]:
    if not bundles:
        return [0.0, 0.0, 0.0]
    acc = np.zeros(3, dtype=np.float64)
    for bundle in bundles:
        sector = str(bundle.get("sector", ""))
        vec = SECTOR_DIRS.get(sector)
        if vec is None:
            continue
        weight = float(bundle.get("channels", {}).get(channel, 0.0))
        acc += vec * weight
    norm = float(np.linalg.norm(acc))
    return [0.0, 0.0, 0.0] if norm <= 1e-12 else [float(v) for v in (acc / norm).tolist()]


def _channel_dict_mean(channel_dicts: list[dict[str, float]]) -> dict[str, float]:
    if not channel_dicts:
        out = {name: 0.0 for name in CHANNEL_NAMES}
    else:
        out = {name: float(np.mean([float(ch.get(name, 0.0)) for ch in channel_dicts])) for name in CHANNEL_NAMES}
    out["directional_strength"] = float(np.mean([abs(float(ch.get("polarity_projection", 0.0))) for ch in channel_dicts])) if channel_dicts else 0.0
    out["circulation_strength"] = float(np.mean([abs(float(ch.get("circulation_projection", 0.0))) for ch in channel_dicts])) if channel_dicts else 0.0
    out["mean_signed_polarity"] = float(np.mean([float(ch.get("polarity_projection", 0.0)) for ch in channel_dicts])) if channel_dicts else 0.0
    out["mean_signed_circulation"] = float(np.mean([float(ch.get("circulation_projection", 0.0)) for ch in channel_dicts])) if channel_dicts else 0.0
    return out


def _compute_spatial_metrics(bundles: list[dict[str, Any]]) -> dict[str, float]:
    if not bundles:
        return {
            "coherence": 0.0,
            "polarity_strength": 0.0,
            "circulation_strength": 0.0,
            "bundle_energy": 0.0,
            "transfer_std": 0.0,
            "polarity_span": 0.0,
            "circulation_span": 0.0,
        }
    transfer = np.asarray([float(bundle["channels"].get("transfer_potential", 0.0)) for bundle in bundles], dtype=np.float64)
    polarity = np.asarray([float(bundle["channels"].get("polarity_projection", 0.0)) for bundle in bundles], dtype=np.float64)
    circulation = np.asarray([float(bundle["channels"].get("circulation_projection", 0.0)) for bundle in bundles], dtype=np.float64)
    energy = np.asarray([
        0.28 * float(bundle["channels"].get("deformation_drive", 0.0))
        + 0.24 * float(bundle["channels"].get("vibration_drive", 0.0))
        + 0.16 * float(bundle["channels"].get("dissipation_load", 0.0))
        + 0.14 * abs(float(bundle["channels"].get("polarity_projection", 0.0)))
        + 0.10 * abs(float(bundle["channels"].get("circulation_projection", 0.0)))
        + 0.08 * float(bundle["channels"].get("event_flux", 0.0))
        for bundle in bundles
    ], dtype=np.float64)
    coherence = _clip01(1.0 - float(np.std(transfer)) / max(float(np.mean(transfer)) + 1e-6, 1e-6))
    dir_vec = np.asarray(_direction_vector(bundles, "polarity_projection"), dtype=np.float64)
    circ_vec = np.asarray(_direction_vector(bundles, "circulation_projection"), dtype=np.float64)
    return {
        "coherence": float(coherence),
        "polarity_strength": float(np.linalg.norm(dir_vec)),
        "circulation_strength": float(np.linalg.norm(circ_vec)),
        "bundle_energy": float(np.mean(energy)),
        "transfer_std": float(np.std(transfer)),
        "polarity_span": float(np.max(polarity) - np.min(polarity)),
        "circulation_span": float(np.max(circulation) - np.min(circulation)),
    }


def _aggregate_global_channels(bundles: list[dict[str, Any]]) -> dict[str, float]:
    return _channel_dict_mean([bundle.get("channels", {}) for bundle in bundles])


def _axis_balance(bundles: list[dict[str, Any]], channel: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        pos = [float(bundle.get("channels", {}).get(channel, 0.0)) for bundle in bundles if str(bundle.get("sector")) == f"{axis}_pos"]
        neg = [float(bundle.get("channels", {}).get(channel, 0.0)) for bundle in bundles if str(bundle.get("sector")) == f"{axis}_neg"]
        pos_mean = float(np.mean(pos)) if pos else 0.0
        neg_mean = float(np.mean(neg)) if neg else 0.0
        out[axis] = float(pos_mean - neg_mean)
    return out


def _layer_summaries(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not bundles:
        return []
    shell_ids = sorted({int(bundle.get("shell_index", -1)) for bundle in bundles})
    out: list[dict[str, Any]] = []
    for shell in shell_ids:
        shell_bundles = [bundle for bundle in bundles if int(bundle.get("shell_index", -1)) == shell]
        out.append(
            {
                "shell_index": int(shell),
                "bundle_count": int(len(shell_bundles)),
                "mean_channels": _aggregate_global_channels(shell_bundles),
                "direction_vector": _direction_vector(shell_bundles, "polarity_projection"),
                "circulation_vector": _direction_vector(shell_bundles, "circulation_projection"),
                "spatial_metrics": _compute_spatial_metrics(shell_bundles),
            }
        )
    return out


def _base_bundle_from_layer(layer: dict[str, Any], sector_name: str, sector_dir: np.ndarray, process_row: dict[str, Any]) -> dict[str, Any]:
    nodes = layer.get("nodes", [])
    if not nodes:
        weights = np.zeros(0, dtype=np.float64)
        unit_dirs = np.zeros((0, 3), dtype=np.float64)
        abs_u = abs_v = abs_acc_r = tang = abs_acc_t = force = gate = contact = signed_v = np.zeros(0, dtype=np.float64)
        vel_abs = np.zeros((0, 3), dtype=np.float64)
        pos_rel = np.zeros((0, 3), dtype=np.float64)
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
        abs_acc_r = np.abs(np.asarray([float(node.get("accel_r", 0.0)) for node in nodes], dtype=np.float64))
        abs_acc_t = np.abs(np.asarray([float(node.get("accel_tangential", 0.0)) for node in nodes], dtype=np.float64))
        force = np.asarray([float(node.get("force_density", 0.0)) for node in nodes], dtype=np.float64)
        gate = np.asarray([float(node.get("gate", 0.0)) for node in nodes], dtype=np.float64)
        contact = np.asarray([float(node.get("contact", 0.0)) for node in nodes], dtype=np.float64)
        vel_abs = np.asarray([node.get("vel_abs", [0.0, 0.0, 0.0]) for node in nodes], dtype=np.float64)

    shell_idx = int(layer.get("band_index", 0))
    shell_name = f"mirror_shell_{shell_idx}"
    shell_factor = 0.55 + 0.15 * float(shell_idx)

    local_abs_u = _weighted_mean(abs_u, weights)
    local_abs_v = _weighted_mean(abs_v, weights)
    local_signed_v = _weighted_mean(signed_v, weights)
    local_tang = _weighted_mean(tang, weights)
    local_abs_acc_r = _weighted_mean(abs_acc_r, weights)
    local_abs_acc_t = _weighted_mean(abs_acc_t, weights)
    local_force = _weighted_mean(force, weights)
    local_gate = _weighted_mean(gate, weights)
    local_contact = _weighted_mean(contact, weights)
    local_angmom = _weighted_vec_mean(np.cross(pos_rel, vel_abs), weights)
    local_vel_vec = _weighted_vec_mean(vel_abs, weights)

    dominant_axis = np.asarray(process_row.get("dominant_axis", [0.0, 0.0, 0.0]), dtype=np.float64)
    dominant_norm = float(np.linalg.norm(dominant_axis))
    dominant_axis = dominant_axis / dominant_norm if dominant_norm > 1e-12 else np.zeros(3, dtype=np.float64)
    signed_velocity_projection = float(local_vel_vec @ sector_dir)
    polarity = float(np.clip(0.72 * signed_velocity_projection * 3.2 + 0.28 * float(dominant_axis @ sector_dir), -1.0, 1.0))

    static_index = float(process_row.get("static_index", 0.0))
    shape_integrity = float(process_row.get("shape_integrity_index", 0.0))
    dipole_ratio = float(process_row.get("dipole_ratio", 0.0))
    quadrupole_ratio = float(process_row.get("quadrupole_ratio", 0.0))
    motion_delta = float(process_row.get("motion_delta", 0.0))
    recovery_index = float(process_row.get("recovery_index", 0.0))
    onset_flag = 1.0 if bool(process_row.get("onset_event", False)) else 0.0
    offset_flag = 1.0 if bool(process_row.get("offset_event", False)) else 0.0

    deformation_drive = _clip01(
        0.34 * _scaled_abs(local_abs_u, 18.0)
        + 0.28 * _scaled_abs(local_force, 0.05)
        + 0.20 * local_gate
        + 0.10 * (1.0 - shape_integrity)
        + 0.08 * local_contact
    )
    vibration_drive = _clip01(
        0.32 * _scaled_abs(local_abs_v, 7.0)
        + 0.28 * _scaled_abs(local_tang, 3.2)
        + 0.20 * _scaled_abs(local_abs_acc_r, 0.35)
        + 0.12 * _scaled_abs(local_abs_acc_t, 0.30)
        + 0.08 * _scaled_abs(motion_delta, 6.0)
    )
    event_flux = _clip01(
        0.30 * onset_flag
        + 0.18 * offset_flag
        + 0.22 * _scaled_abs(local_abs_acc_r + local_abs_acc_t, 0.25)
        + 0.18 * _scaled_abs(motion_delta, 6.0)
        + 0.12 * _scaled_abs(local_signed_v, 6.0)
    )
    dissipation_load = _clip01(
        0.28 * _scaled_abs(local_force * local_abs_v, 0.03)
        + 0.22 * local_contact
        + 0.20 * (1.0 - shape_integrity)
        + 0.18 * recovery_index
        + 0.12 * (1.0 - static_index)
    )
    axial_flux = _clip01(
        (
            0.40 * _scaled_abs(local_signed_v, 6.5)
            + 0.24 * deformation_drive
            + 0.18 * event_flux
            + 0.10 * _scaled_abs(local_force, 0.05)
            + 0.08 * local_gate
        )
        * (0.30 + 0.80 * abs(polarity))
        * (0.55 + 0.85 * dipole_ratio)
    )
    swirl_flux = _clip01(
        (
            0.42 * _scaled_abs(local_tang, 3.5)
            + 0.24 * vibration_drive
            + 0.16 * _scaled_abs(local_abs_acc_t, 0.30)
            + 0.10 * deformation_drive
            + 0.08 * _scaled_abs(local_force, 0.05)
        )
        * (0.30 + 0.60 * shell_factor)
        * (0.25 + 0.80 * quadrupole_ratio)
        * (0.95 - 0.22 * abs(polarity))
    )
    polarity_projection = _clip_signed(polarity * max(axial_flux, 1e-6))
    circulation_projection = _clip_signed(float(local_angmom @ sector_dir) * 35.0 * (0.35 + 0.65 * max(swirl_flux, 0.05)))
    transfer_potential = _clip01(
        0.22 * deformation_drive
        + 0.18 * vibration_drive
        + 0.16 * event_flux
        + 0.14 * dissipation_load
        + 0.12 * axial_flux
        + 0.10 * swirl_flux
        + 0.04 * abs(polarity_projection)
        + 0.04 * abs(circulation_projection)
    )

    centroid = unit_dirs[np.argmax(weights)].tolist() if weights.size and np.any(weights > 0.0) else sector_dir.tolist()
    return {
        "bundle_id": f"{shell_name}_{sector_name}",
        "shell_index": shell_idx,
        "shell_name": shell_name,
        "sector": sector_name,
        "centroid_direction": [float(v) for v in centroid],
        "coupling_weight": float(np.mean(weights)) if weights.size else 0.0,
        "channels": {
            "deformation_drive": deformation_drive,
            "vibration_drive": vibration_drive,
            "event_flux": event_flux,
            "dissipation_load": dissipation_load,
            "axial_flux": axial_flux,
            "swirl_flux": swirl_flux,
            "polarity_projection": polarity_projection,
            "circulation_projection": circulation_projection,
            "transfer_potential": transfer_potential,
        },
        "local_observables": {
            "abs_radial_disp": float(local_abs_u),
            "abs_radial_speed": float(local_abs_v),
            "tangential_speed": float(local_tang),
            "abs_accel_r": float(local_abs_acc_r),
            "abs_accel_t": float(local_abs_acc_t),
            "force_density": float(local_force),
            "gate": float(local_gate),
            "contact": float(local_contact),
            "angular_momentum": [float(v) for v in local_angmom.tolist()],
        },
        "propagation_constraints": {
            "track_mode": "discrete",
            "shell_norm": 0.0,
            "neighbor_count": 0,
            "boundary_leak": 0.0,
            "temporal_persistence": 0.0,
        },
    }


def _build_discrete_bundles(frame_row: dict[str, Any], process_row: dict[str, Any]) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for layer in frame_row.get("layers", []):
        for sector_name, sector_dir in SECTOR_DIRS.items():
            bundles.append(_base_bundle_from_layer(layer, sector_name, sector_dir, process_row))
    return bundles


def _sector_similarity(sector_a: str, sector_b: str) -> float:
    a = SECTOR_DIRS[sector_a]
    b = SECTOR_DIRS[sector_b]
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    angle = math.acos(dot)
    return float(math.exp(-((angle / 1.05) ** 2)))


def _combine_signed(parts: list[tuple[float, float]]) -> float:
    total_w = sum(max(w, 0.0) for _, w in parts)
    if total_w <= 1e-12:
        return 0.0
    return float(sum(v * max(w, 0.0) for v, w in parts) / total_w)


def _combine_unsigned(parts: list[tuple[float, float]]) -> float:
    total_w = sum(max(w, 0.0) for _, w in parts)
    if total_w <= 1e-12:
        return 0.0
    return float(sum(v * max(w, 0.0) for v, w in parts) / total_w)


def _stateful_constrained_coupling(
    source_bundles: list[dict[str, Any]],
    previous_state: dict[str, dict[str, float]] | None,
    *,
    track_mode: str,
    stimulus_mode: str | None = None,
    stimulus_active: bool = False,
    transition_state: str | None = None,
    layered_rotation_repair: dict[str, float] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    if not source_bundles:
        return [], {}

    bundles = [dict(bundle, channels=dict(bundle["channels"])) for bundle in source_bundles]
    by_shell_sector = {(int(bundle["shell_index"]), str(bundle["sector"])): bundle for bundle in bundles}
    shell_ids = sorted({int(bundle["shell_index"]) for bundle in bundles})
    max_shell = max(shell_ids) if shell_ids else 0
    layer_means = {
        shell: _channel_dict_mean([bundle["channels"] for bundle in bundles if int(bundle["shell_index"]) == shell])
        for shell in shell_ids
    }
    global_mean = _channel_dict_mean([bundle["channels"] for bundle in bundles])

    if track_mode == "local":
        track_scale = {"lateral": 0.95, "radial": 0.70, "layer": 0.20, "global": 0.0, "memory": 1.0}
    else:
        track_scale = {"lateral": 0.82, "radial": 0.85, "layer": 0.65, "global": 0.18, "memory": 1.08}

    out: list[dict[str, Any]] = []
    next_state: dict[str, dict[str, float]] = {}
    for bundle in bundles:
        shell = int(bundle["shell_index"])
        sector = str(bundle["sector"])
        shell_norm = float(shell / max(max_shell, 1)) if max_shell > 0 else 0.0
        lateral_neighbors: list[tuple[dict[str, Any], float]] = []
        for other_sector in SECTOR_ORDER:
            if other_sector == sector:
                continue
            key = (shell, other_sector)
            if key not in by_shell_sector:
                continue
            lateral_neighbors.append((by_shell_sector[key], _sector_similarity(sector, other_sector)))
        radial_neighbors: list[tuple[dict[str, Any], float]] = []
        for other_shell in (shell - 1, shell + 1):
            key = (other_shell, sector)
            if key in by_shell_sector:
                radial_neighbors.append((by_shell_sector[key], 1.0 / (1.0 + abs(other_shell - shell))))

        mixed_channels: dict[str, float] = {}
        prev_channels = (previous_state or {}).get(str(bundle["bundle_id"]), {})
        for name in CHANNEL_NAMES:
            params = CHANNEL_PARAMS[name]
            self_v = float(bundle["channels"].get(name, 0.0))
            lateral_v = _combine_signed([(float(nb["channels"].get(name, 0.0)), w) for nb, w in lateral_neighbors]) if name in SIGNED_CHANNELS else _combine_unsigned([(float(nb["channels"].get(name, 0.0)), w) for nb, w in lateral_neighbors])
            radial_v = _combine_signed([(float(nb["channels"].get(name, 0.0)), w) for nb, w in radial_neighbors]) if name in SIGNED_CHANNELS else _combine_unsigned([(float(nb["channels"].get(name, 0.0)), w) for nb, w in radial_neighbors])
            layer_v = float(layer_means[shell].get(name, 0.0))
            global_v = float(global_mean.get(name, 0.0))
            self_w = max(0.10, 1.0 - (params["lateral"] * track_scale["lateral"] + params["radial"] * track_scale["radial"] + params["layer"] * track_scale["layer"] + params["global"] * track_scale["global"]))
            source_value = (
                self_w * self_v
                + params["lateral"] * track_scale["lateral"] * lateral_v
                + params["radial"] * track_scale["radial"] * radial_v
                + params["layer"] * track_scale["layer"] * layer_v
                + params["global"] * track_scale["global"] * global_v
            )
            boundary_factor = 1.0 - params["boundary"] * (0.35 + 0.65 * shell_norm)
            source_value *= boundary_factor
            prev_value = float(prev_channels.get(name, self_v))
            persistence = min(0.95, params["persistence"] * track_scale["memory"])
            mixed = persistence * prev_value + (1.0 - persistence) * source_value
            if name in SIGNED_CHANNELS:
                mixed_channels[name] = _clip_signed(mixed)
            else:
                mixed_channels[name] = _clip01(mixed)

        if track_mode == "layered" and stimulus_mode == "rotation":
            repair = {
                "shell_emphasis_gain": 0.45,
                "active_gain": 1.20,
                "inactive_gain": 1.08,
                "onset_boost": 1.05,
                "swirl_gain": 1.0,
                "circulation_feed": 0.18,
                "circulation_gain": 1.10,
                "circulation_shell_gain": 0.22,
                "axial_base": 0.90,
                "axial_shell_drop": 0.08,
                "transfer_base": 0.96,
                "transfer_shell_gain": 0.06,
                "transfer_swirl_mix": 0.06,
            }
            if layered_rotation_repair:
                repair.update({k: float(v) for k, v in layered_rotation_repair.items()})
            shell_emphasis = 0.75 + repair["shell_emphasis_gain"] * shell_norm
            active_gain = repair["active_gain"] if stimulus_active else repair["inactive_gain"]
            if transition_state in {"stimulus_onset", "active_motion"}:
                active_gain *= repair["onset_boost"]
            swirl_mix = _clip01(mixed_channels["swirl_flux"] * active_gain * shell_emphasis * repair["swirl_gain"] + repair["circulation_feed"] * abs(mixed_channels["circulation_projection"]))
            circ_mix = _clip_signed(mixed_channels["circulation_projection"] * (repair["circulation_gain"] + repair["circulation_shell_gain"] * shell_norm))
            axial_mix = _clip01(mixed_channels["axial_flux"] * max(0.40, repair["axial_base"] - repair["axial_shell_drop"] * shell_norm))
            transfer_mix = _clip01(mixed_channels["transfer_potential"] * (repair["transfer_base"] + repair["transfer_shell_gain"] * shell_norm) + repair["transfer_swirl_mix"] * swirl_mix)
            mixed_channels["swirl_flux"] = swirl_mix
            mixed_channels["circulation_projection"] = circ_mix
            mixed_channels["axial_flux"] = axial_mix
            mixed_channels["transfer_potential"] = transfer_mix

        new_bundle = dict(bundle)
        new_bundle["channels"] = mixed_channels
        new_bundle["propagation_constraints"] = {
            "track_mode": track_mode,
            "shell_norm": shell_norm,
            "neighbor_count": int(len(lateral_neighbors) + len(radial_neighbors)),
            "boundary_leak": float(np.mean([CHANNEL_PARAMS[name]["boundary"] for name in CHANNEL_NAMES])),
            "temporal_persistence": float(np.mean([CHANNEL_PARAMS[name]["persistence"] for name in CHANNEL_NAMES])),
        }
        out.append(new_bundle)
        next_state[str(bundle["bundle_id"])] = dict(mixed_channels)
    return out, next_state


def _track_payload(name: str, bundles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "track_name": name,
        "channel_names": CHANNEL_NAMES,
        "local_bundles": bundles,
        "layer_summaries": _layer_summaries(bundles),
        "global_channels": _aggregate_global_channels(bundles),
        "direction_vector": _direction_vector(bundles, "polarity_projection"),
        "circulation_vector": _direction_vector(bundles, "circulation_projection"),
        "spatial_metrics": _compute_spatial_metrics(bundles),
        "propagation_constraints": {
            "channel_params": CHANNEL_PARAMS,
            "mode": name,
        },
    }


def build_interface_network_trace(sensor_nodes_trace: list[dict[str, Any]], process_trace: list[dict[str, Any]], *, layered_rotation_repair: dict[str, float] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prev_local: dict[str, dict[str, float]] = {}
    prev_layered: dict[str, dict[str, float]] = {}
    for frame_row, process_row in zip(sensor_nodes_trace, process_trace):
        discrete = _build_discrete_bundles(frame_row, process_row)
        local, prev_local = _stateful_constrained_coupling(
            discrete,
            prev_local,
            track_mode="local",
            stimulus_mode=process_row.get("stimulus_mode"),
            stimulus_active=bool(process_row.get("stimulus_active", False)),
            transition_state=process_row.get("transition_state"),
            layered_rotation_repair=layered_rotation_repair,
        )
        layered, prev_layered = _stateful_constrained_coupling(
            local,
            prev_layered,
            track_mode="layered",
            stimulus_mode=process_row.get("stimulus_mode"),
            stimulus_active=bool(process_row.get("stimulus_active", False)),
            transition_state=process_row.get("transition_state"),
            layered_rotation_repair=layered_rotation_repair,
        )
        rows.append(
            {
                "time": float(process_row.get("time", 0.0)),
                "stimulus_mode": process_row.get("stimulus_mode"),
                "stimulus_active": bool(process_row.get("stimulus_active", False)),
                "transition_state": process_row.get("transition_state", "baseline"),
                "network_structure": {
                    "topology": "concentric interface shells x directional sectors x physically constrained transduction tracks",
                    "tracks": TRACK_NAMES,
                    "bundle_channel_names": CHANNEL_NAMES,
                    "sector_count": len(SECTOR_ORDER),
                    "layer_count": int(len(frame_row.get("layers", []))),
                    "signaling_principle": "transduction under spatial coupling, attenuation, and temporal persistence",
                },
                "tracks": {
                    "discrete_channel_track": _track_payload("discrete_channel_track", discrete),
                    "local_propagation_track": _track_payload("local_propagation_track", local),
                    "layered_coupling_track": _track_payload("layered_coupling_track", layered),
                },
            }
        )
    return rows


def _summarize_track(rows: list[dict[str, Any]], track_name: str, stimulus_mode: str) -> dict[str, Any]:
    if not rows:
        return {
            "num_samples": 0,
            "active_num_samples": 0,
            "mean_global_channels": _aggregate_global_channels([]),
            "mean_spatial_coherence": 0.0,
            "mean_directional_strength": 0.0,
            "mean_circulation_strength": 0.0,
            "mean_transfer_std": 0.0,
            "protocol_aligned_flux_margin": 0.0,
            "active_summary": {},
        }
    track_rows = [row["tracks"][track_name] for row in rows]
    active_track_rows = [row["tracks"][track_name] for row in rows if bool(row.get("stimulus_active", False))]
    mean_channels = _channel_dict_mean([tr["global_channels"] for tr in track_rows])
    active_channels = _channel_dict_mean([tr["global_channels"] for tr in active_track_rows]) if active_track_rows else _aggregate_global_channels([])
    mean_coherence = float(np.mean([float(tr["spatial_metrics"].get("coherence", 0.0)) for tr in track_rows]))
    mean_directional = float(np.mean([float(tr["global_channels"].get("directional_strength", 0.0)) for tr in track_rows]))
    mean_circulation = float(np.mean([float(tr["global_channels"].get("circulation_strength", 0.0)) for tr in track_rows]))
    mean_transfer_std = float(np.mean([float(tr["spatial_metrics"].get("transfer_std", 0.0)) for tr in track_rows]))
    active_coherence = float(np.mean([float(tr["spatial_metrics"].get("coherence", 0.0)) for tr in active_track_rows])) if active_track_rows else 0.0
    active_directional = float(np.mean([float(tr["global_channels"].get("directional_strength", 0.0)) for tr in active_track_rows])) if active_track_rows else 0.0
    active_circulation = float(np.mean([float(tr["global_channels"].get("circulation_strength", 0.0)) for tr in active_track_rows])) if active_track_rows else 0.0
    if stimulus_mode == "translation":
        aligned_margin = active_channels["axial_flux"] - active_channels["swirl_flux"]
    elif stimulus_mode == "rotation":
        aligned_margin = active_channels["swirl_flux"] - active_channels["axial_flux"]
    else:
        aligned_margin = mean_channels["deformation_drive"] - max(mean_channels["axial_flux"], mean_channels["swirl_flux"])
    return {
        "num_samples": int(len(track_rows)),
        "active_num_samples": int(len(active_track_rows)),
        "mean_global_channels": mean_channels,
        "mean_spatial_coherence": mean_coherence,
        "mean_directional_strength": mean_directional,
        "mean_circulation_strength": mean_circulation,
        "mean_transfer_std": mean_transfer_std,
        "axis_balance": _axis_balance([bundle for tr in track_rows for bundle in tr.get("local_bundles", [])], "axial_flux"),
        "circulation_axis_balance": _axis_balance([bundle for tr in track_rows for bundle in tr.get("local_bundles", [])], "circulation_projection"),
        "protocol_aligned_flux_margin": float(aligned_margin),
        "active_summary": {
            "mean_global_channels": active_channels,
            "mean_spatial_coherence": active_coherence,
            "mean_directional_strength": active_directional,
            "mean_circulation_strength": active_circulation,
            "axis_balance": _axis_balance([bundle for tr in active_track_rows for bundle in tr.get("local_bundles", [])], "axial_flux"),
            "circulation_axis_balance": _axis_balance([bundle for tr in active_track_rows for bundle in tr.get("local_bundles", [])], "circulation_projection"),
        },
        "bundles_per_frame": int(len(track_rows[0].get("local_bundles", []))) if track_rows else 0,
        "layers_per_frame": int(len(track_rows[0].get("layer_summaries", []))) if track_rows else 0,
    }


def summarize_interface_network_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "network_topology": "concentric interface shells x directional sectors x physically constrained transduction tracks",
            "tracks": {name: _summarize_track([], name, "none") for name in TRACK_NAMES},
        }
    stimulus_mode = str(trace[0].get("stimulus_mode") or "none")
    return {
        "num_samples": int(len(trace)),
        "network_topology": "concentric interface shells x directional sectors x physically constrained transduction tracks",
        "track_names": TRACK_NAMES,
        "bundle_channel_names": CHANNEL_NAMES,
        "tracks": {name: _summarize_track(trace, name, stimulus_mode) for name in TRACK_NAMES},
    }
