from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from cell_sphere_core.analysis.multipole import compute_multipole_energy_numpy


@dataclass(frozen=True)
class ProcessStateSnapshot:
    force_magnitude_index: float
    static_index: float
    motion_index: float
    shape_integrity_index: float
    drift_index: float
    monopole_energy: float
    dipole_energy: float
    quadrupole_energy: float
    multipole_total_energy: float
    dipole_ratio: float
    quadrupole_ratio: float
    motion_class: str
    motion_confidence: float
    dominant_axis: list[float]
    phase: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "force_magnitude_index": float(self.force_magnitude_index),
            "static_index": float(self.static_index),
            "motion_index": float(self.motion_index),
            "shape_integrity_index": float(self.shape_integrity_index),
            "drift_index": float(self.drift_index),
            "monopole_energy": float(self.monopole_energy),
            "dipole_energy": float(self.dipole_energy),
            "quadrupole_energy": float(self.quadrupole_energy),
            "multipole_total_energy": float(self.multipole_total_energy),
            "dipole_ratio": float(self.dipole_ratio),
            "quadrupole_ratio": float(self.quadrupole_ratio),
            "motion_class": self.motion_class,
            "motion_confidence": float(self.motion_confidence),
            "dominant_axis": [float(v) for v in self.dominant_axis],
            "phase": self.phase,
        }


def _safe_mean(values: np.ndarray | list[float]) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    return float(np.mean(arr))


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _extract_outer_nodes(node_frame: dict, band: int | str = "outer") -> list[dict]:
    layers = node_frame.get("layers", [])
    if not layers:
        return []
    if band == "outer":
        layer = max(layers, key=lambda item: int(item.get("band_index", -1)))
    elif band == "inner":
        layer = min(layers, key=lambda item: int(item.get("band_index", 10**9)))
    else:
        target = int(band)
        candidates = [layer for layer in layers if int(layer.get("band_index", -1)) == target]
        layer = candidates[0] if candidates else {"nodes": []}
    return layer.get("nodes", [])


def _compute_axis_signature(nodes: list[dict]) -> np.ndarray:
    if not nodes:
        return np.zeros(3, dtype=np.float64)
    pos_rel = np.asarray([node.get("pos_rel", [0.0, 0.0, 0.0]) for node in nodes], dtype=np.float64)
    v_r = np.asarray([float(node.get("v_r", 0.0)) for node in nodes], dtype=np.float64)
    accel_r = np.asarray([float(node.get("accel_r", 0.0)) for node in nodes], dtype=np.float64)
    weight = np.abs(v_r) + 0.35 * np.abs(accel_r)
    norm = np.linalg.norm(pos_rel, axis=1)
    valid = norm > 1e-12
    if not np.any(valid):
        return np.zeros(3, dtype=np.float64)
    dirs = np.zeros_like(pos_rel)
    dirs[valid] = pos_rel[valid] / norm[valid, None]
    axis_vec = np.sum(dirs * weight[:, None], axis=0)
    axis_norm = float(np.linalg.norm(axis_vec))
    if axis_norm <= 1e-12:
        return np.zeros(3, dtype=np.float64)
    return axis_vec / axis_norm


def compute_process_state_snapshot(
    *,
    node_frame: dict,
    sensor_snapshot: Any,
    metrics: dict,
    stimulus_mode: str | None,
    stimulus_active: bool,
    field_name: str = "v_r",
    band: int | str = "outer",
) -> ProcessStateSnapshot:
    nodes = _extract_outer_nodes(node_frame, band=band)
    polar = np.asarray([float(node.get("polar", 0.0)) for node in nodes], dtype=np.float64)
    azimuthal = np.asarray([float(node.get("azimuthal", 0.0)) for node in nodes], dtype=np.float64)
    field = np.asarray([float(node.get(field_name, 0.0)) for node in nodes], dtype=np.float64)
    energies = compute_multipole_energy_numpy(polar, azimuthal, field)

    total = float(energies.get("total", 0.0))
    dipole = float(energies.get("l=1", 0.0))
    quadrupole = float(energies.get("l=2", 0.0))
    monopole = float(energies.get("l=0", 0.0))
    d12 = max(dipole + quadrupole, 1e-12)
    dipole_ratio = float(dipole / d12)
    quadrupole_ratio = float(quadrupole / d12)

    force_mag = _safe_mean(getattr(sensor_snapshot, "band_force_density", []))
    compression = _safe_mean(getattr(sensor_snapshot, "band_compression", []))
    band_sag = _safe_mean(getattr(sensor_snapshot, "band_sag", []))
    radial_speed = _safe_mean(np.abs(getattr(sensor_snapshot, "band_radial_speed", [])))
    tangential_speed = _safe_mean(np.abs(getattr(sensor_snapshot, "band_tangential_speed", [])))
    global_accel = float(getattr(sensor_snapshot, "global_accel_norm", 0.0))

    kinetic_energy = float(metrics.get("kinetic_energy", 0.0))
    floor_contact = float(metrics.get("floor_contact_ratio", 0.0))
    shape_dev = float(metrics.get("shape_deviation", 0.0))
    volume_ratio = float(metrics.get("volume_ratio", 1.0))
    radius_cv = float(metrics.get("radius_cv", 0.0))
    asphericity = float(metrics.get("asphericity", 0.0))
    center_drift = float(metrics.get("center_of_mass_xy_radius", 0.0))

    force_magnitude_index = _clip01(0.06 * force_mag + 2.2 * compression + 0.18 * global_accel)
    motion_index = _clip01(
        0.18 * radial_speed
        + 0.10 * tangential_speed
        + 0.18 * np.sqrt(total)
        + 0.005 * np.sqrt(max(kinetic_energy, 0.0))
    )

    shape_penalty = 3.2 * shape_dev + 3.0 * abs(volume_ratio - 1.0) + 1.8 * radius_cv + 1.2 * asphericity + 0.8 * band_sag + 1.2 * floor_contact
    shape_integrity_index = _clip01(1.0 - shape_penalty)
    drift_index = _clip01(1.0 - (center_drift / 0.08))
    static_index = _clip01(0.52 * shape_integrity_index + 0.24 * drift_index + 0.24 * (1.0 - motion_index))

    if ((not stimulus_active) and static_index > 0.45) or (motion_index < 0.08 and static_index > 0.55):
        motion_class = "static"
        confidence = max(static_index, 1.0 - motion_index)
    elif dipole_ratio > 0.54 and dipole > quadrupole * 1.05:
        motion_class = "translation"
        confidence = max(dipole_ratio, motion_index)
    elif quadrupole_ratio > 0.58 and quadrupole > dipole * 1.08:
        motion_class = "rotation"
        confidence = max(quadrupole_ratio, motion_index)
    else:
        motion_class = "mixed"
        confidence = max(motion_index, 0.35)

    if not stimulus_active:
        phase = "baseline"
    elif stimulus_mode == "translation":
        phase = "active_translation"
    elif stimulus_mode == "rotation":
        phase = "active_rotation"
    else:
        phase = "active_generic"

    return ProcessStateSnapshot(
        force_magnitude_index=force_magnitude_index,
        static_index=static_index,
        motion_index=motion_index,
        shape_integrity_index=shape_integrity_index,
        drift_index=drift_index,
        monopole_energy=monopole,
        dipole_energy=dipole,
        quadrupole_energy=quadrupole,
        multipole_total_energy=total,
        dipole_ratio=dipole_ratio,
        quadrupole_ratio=quadrupole_ratio,
        motion_class=motion_class,
        motion_confidence=_clip01(confidence),
        dominant_axis=_compute_axis_signature(nodes).tolist(),
        phase=phase,
    )


def summarize_process_state_trace(trace: list[dict]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "dominant_motion_class": "none",
            "class_counts": {},
            "mean_force_magnitude_index": 0.0,
            "mean_static_index": 0.0,
            "mean_motion_index": 0.0,
            "mean_dipole_ratio": 0.0,
            "mean_quadrupole_ratio": 0.0,
            "active_summary": {},
        }
    class_counts: dict[str, int] = {}
    for row in trace:
        cls = str(row.get("motion_class", "unknown"))
        class_counts[cls] = class_counts.get(cls, 0) + 1
    dominant = max(class_counts.items(), key=lambda kv: kv[1])[0]

    def _mean(key: str, rows: list[dict] | None = None) -> float:
        seq = trace if rows is None else rows
        if not seq:
            return 0.0
        return float(np.mean([float(row.get(key, 0.0)) for row in seq]))

    active_rows = [row for row in trace if bool(row.get("stimulus_active", False))]
    active_classes: dict[str, int] = {}
    for row in active_rows:
        cls = str(row.get("motion_class", "unknown"))
        active_classes[cls] = active_classes.get(cls, 0) + 1
    active_dominant = max(active_classes.items(), key=lambda kv: kv[1])[0] if active_classes else "none"

    payload = {
        "num_samples": int(len(trace)),
        "dominant_motion_class": dominant,
        "class_counts": class_counts,
        "mean_force_magnitude_index": _mean("force_magnitude_index"),
        "mean_static_index": _mean("static_index"),
        "mean_motion_index": _mean("motion_index"),
        "mean_dipole_ratio": _mean("dipole_ratio"),
        "mean_quadrupole_ratio": _mean("quadrupole_ratio"),
        "active_summary": {
            "num_samples": int(len(active_rows)),
            "dominant_motion_class": active_dominant,
            "class_counts": active_classes,
            "mean_force_magnitude_index": _mean("force_magnitude_index", active_rows),
            "mean_static_index": _mean("static_index", active_rows),
            "mean_motion_index": _mean("motion_index", active_rows),
            "mean_dipole_ratio": _mean("dipole_ratio", active_rows),
            "mean_quadrupole_ratio": _mean("quadrupole_ratio", active_rows),
        },
    }
    if trace and "transition_state" in trace[0]:
        payload["transition_state_counts"] = _count_by_key(trace, "transition_state")
        payload["mean_memory_trace_strength"] = _mean("memory_trace_strength")
        payload["mean_recovery_index"] = _mean("recovery_index")
    return payload


def _count_by_key(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key, "unknown"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def enrich_process_state_trace(
    trace: list[dict],
    *,
    ema_alpha: float = 0.28,
    onset_window_s: float = 0.018,
    recovery_window_s: float = 0.04,
) -> list[dict]:
    if not trace:
        return []

    enriched: list[dict] = []
    ema_force = float(trace[0].get("force_magnitude_index", 0.0))
    ema_static = float(trace[0].get("static_index", 0.0))
    ema_motion = float(trace[0].get("motion_index", 0.0))
    ema_dipole = float(trace[0].get("dipole_ratio", 0.0))
    ema_quadrupole = float(trace[0].get("quadrupole_ratio", 0.0))

    prev_motion = float(trace[0].get("motion_index", 0.0))
    prev_active = False
    had_activation = False
    activation_count = 0
    deactivation_count = 0
    cycle_id = 0
    last_onset_time: float | None = None
    last_offset_time: float | None = None
    current_cycle_peak_motion = 0.0
    last_cycle_peak_motion = 0.0
    current_cycle_peak_force = 0.0
    last_stimulus_class = "none"
    active_class_counts: dict[str, int] = {}

    for i, base_row in enumerate(trace):
        row = dict(base_row)
        t = float(row.get("time", 0.0))
        active = bool(row.get("stimulus_active", False))
        force_idx = float(row.get("force_magnitude_index", 0.0))
        static_idx = float(row.get("static_index", 0.0))
        motion_idx = float(row.get("motion_index", 0.0))
        dipole_ratio = float(row.get("dipole_ratio", 0.0))
        quadrupole_ratio = float(row.get("quadrupole_ratio", 0.0))
        motion_class = str(row.get("motion_class", "unknown"))

        if i > 0:
            ema_force = (1.0 - ema_alpha) * ema_force + ema_alpha * force_idx
            ema_static = (1.0 - ema_alpha) * ema_static + ema_alpha * static_idx
            ema_motion = (1.0 - ema_alpha) * ema_motion + ema_alpha * motion_idx
            ema_dipole = (1.0 - ema_alpha) * ema_dipole + ema_alpha * dipole_ratio
            ema_quadrupole = (1.0 - ema_alpha) * ema_quadrupole + ema_alpha * quadrupole_ratio

        onset_event = bool(active and not prev_active)
        offset_event = bool((not active) and prev_active)
        if onset_event:
            had_activation = True
            activation_count += 1
            cycle_id += 1
            last_onset_time = t
            current_cycle_peak_motion = motion_idx
            current_cycle_peak_force = force_idx
            active_class_counts = {}
        if active:
            current_cycle_peak_motion = max(current_cycle_peak_motion, motion_idx)
            current_cycle_peak_force = max(current_cycle_peak_force, force_idx)
            if motion_class != "static":
                active_class_counts[motion_class] = active_class_counts.get(motion_class, 0) + 1
        if offset_event:
            deactivation_count += 1
            last_offset_time = t
            last_cycle_peak_motion = max(last_cycle_peak_motion, current_cycle_peak_motion)
            if active_class_counts:
                last_stimulus_class = max(active_class_counts.items(), key=lambda kv: kv[1])[0]
            else:
                last_stimulus_class = str(row.get("stimulus_mode", "none") or "none")

        time_since_activation = 0.0 if last_onset_time is None else max(0.0, t - last_onset_time)
        time_since_deactivation = 0.0 if last_offset_time is None else max(0.0, t - last_offset_time)
        motion_delta = motion_idx - prev_motion if i > 0 else 0.0
        adaptation_index = 0.0
        if active and current_cycle_peak_motion > 1e-8:
            adaptation_index = _clip01((current_cycle_peak_motion - motion_idx) / current_cycle_peak_motion)

        recovery_index = 0.0
        if had_activation and not active:
            recovery_index = _clip01(0.65 * static_idx + 0.35 * (1.0 - motion_idx))

        memory_trace_strength = _clip01(
            0.45 * ema_motion + 0.20 * abs(ema_force - force_idx) + 0.20 * max(ema_dipole, ema_quadrupole) + 0.15 * abs(motion_delta)
        )

        if not had_activation and not active:
            transition_state = "baseline"
        elif onset_event or (active and time_since_activation <= onset_window_s):
            transition_state = "stimulus_onset"
        elif active:
            transition_state = "stimulus_active"
        elif offset_event or ((not active) and last_offset_time is not None and time_since_deactivation <= recovery_window_s):
            transition_state = "recovery"
        elif static_idx >= 0.42 and motion_idx <= 0.12:
            transition_state = "recovered_static"
        else:
            transition_state = "post_stimulus_drift"

        row.update(
            {
                "transition_state": transition_state,
                "onset_event": onset_event,
                "offset_event": offset_event,
                "memory_force_ema": float(ema_force),
                "memory_static_ema": float(ema_static),
                "memory_motion_ema": float(ema_motion),
                "memory_dipole_ema": float(ema_dipole),
                "memory_quadrupole_ema": float(ema_quadrupole),
                "motion_delta": float(motion_delta),
                "adaptation_index": float(adaptation_index),
                "recovery_index": float(recovery_index),
                "memory_trace_strength": float(memory_trace_strength),
                "time_since_activation": float(time_since_activation),
                "time_since_deactivation": float(time_since_deactivation),
                "activation_count": int(activation_count),
                "deactivation_count": int(deactivation_count),
                "stimulus_cycle_id": int(cycle_id),
                "last_stimulus_class": last_stimulus_class,
                "cycle_peak_motion_index": float(current_cycle_peak_motion if active else last_cycle_peak_motion),
                "cycle_peak_force_index": float(current_cycle_peak_force if active else current_cycle_peak_force),
            }
        )
        enriched.append(row)
        prev_motion = motion_idx
        prev_active = active
    return enriched


def summarize_transition_memory_trace(trace: list[dict]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "activation_events": 0,
            "deactivation_events": 0,
            "dominant_transition_state": "none",
            "transition_counts": {},
            "mean_memory_trace_strength": 0.0,
            "peak_memory_trace_strength": 0.0,
            "mean_recovery_index": 0.0,
            "final_recovery_index": 0.0,
            "time_to_first_recovered_static": None,
            "recovered_after_last_offset": False,
        }

    transition_counts = _count_by_key(trace, "transition_state")
    dominant = max(transition_counts.items(), key=lambda kv: kv[1])[0]
    memory_values = np.asarray([float(row.get("memory_trace_strength", 0.0)) for row in trace], dtype=np.float64)
    recovery_values = np.asarray([float(row.get("recovery_index", 0.0)) for row in trace], dtype=np.float64)
    activation_events = int(sum(bool(row.get("onset_event", False)) for row in trace))
    deactivation_events = int(sum(bool(row.get("offset_event", False)) for row in trace))

    last_offset_time = None
    for row in trace:
        if bool(row.get("offset_event", False)):
            last_offset_time = float(row.get("time", 0.0))

    time_to_first_recovered_static: float | None = None
    recovered_after_last_offset = False
    if last_offset_time is not None:
        for row in trace:
            t = float(row.get("time", 0.0))
            if t >= last_offset_time and str(row.get("transition_state", "")) == "recovered_static":
                recovered_after_last_offset = True
                time_to_first_recovered_static = t - last_offset_time
                break

    recovery_rows = [row for row in trace if str(row.get("transition_state", "")) in {"recovery", "recovered_static", "post_stimulus_drift"}]
    active_rows = [row for row in trace if bool(row.get("stimulus_active", False))]
    return {
        "num_samples": int(len(trace)),
        "activation_events": activation_events,
        "deactivation_events": deactivation_events,
        "dominant_transition_state": dominant,
        "transition_counts": transition_counts,
        "mean_memory_trace_strength": float(np.mean(memory_values)),
        "peak_memory_trace_strength": float(np.max(memory_values)),
        "mean_recovery_index": float(np.mean(recovery_values)) if recovery_values.size else 0.0,
        "final_recovery_index": float(trace[-1].get("recovery_index", 0.0)),
        "mean_active_adaptation_index": float(np.mean([float(row.get("adaptation_index", 0.0)) for row in active_rows])) if active_rows else 0.0,
        "mean_recovery_index_post_offset": float(np.mean([float(row.get("recovery_index", 0.0)) for row in recovery_rows])) if recovery_rows else 0.0,
        "time_to_first_recovered_static": None if time_to_first_recovered_static is None else float(time_to_first_recovered_static),
        "recovered_after_last_offset": bool(recovered_after_last_offset),
        "last_stimulus_class": str(trace[-1].get("last_stimulus_class", "none")),
    }
