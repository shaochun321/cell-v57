from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import math
from pathlib import Path

import numpy as np

TRACKS = (
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
)


@dataclass(frozen=True)
class ProcessCalculatorWindow:
    phase: str
    dominant_mode: str
    dominant_axis: str
    stability_score: float
    recovery_score: float
    mode_margin: float
    channel_contributions: dict[str, float]
    window_start: float
    window_end: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "dominant_mode": self.dominant_mode,
            "dominant_axis": self.dominant_axis,
            "stability_score": float(self.stability_score),
            "recovery_score": float(self.recovery_score),
            "mode_margin": float(self.mode_margin),
            "channel_contributions": {k: float(v) for k, v in self.channel_contributions.items()},
            "window_start": float(self.window_start),
            "window_end": float(self.window_end),
        }


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _iter_aligned_rows(
    process_trace: list[dict[str, Any]],
    readout_trace: list[dict[str, Any]],
    interface_network_trace: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    n = min(len(process_trace), len(readout_trace), len(interface_network_trace))
    return [
        (process_trace[i], readout_trace[i], interface_network_trace[i])
        for i in range(n)
    ]


def _track_payloads(interface_row: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = interface_row.get("tracks", {})
    payloads: list[dict[str, Any]] = []
    for name in TRACKS:
        payload = tracks.get(name)
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _vector_mean(vectors: list[list[float] | tuple[float, float, float]]) -> np.ndarray:
    if not vectors:
        return np.zeros(3, dtype=np.float64)
    arr = np.asarray(vectors, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        return np.zeros(3, dtype=np.float64)
    return np.mean(arr, axis=0)


def _axis_label(vector: np.ndarray, *, min_norm: float = 0.12) -> str:
    norm = float(np.linalg.norm(vector))
    if norm < min_norm:
        return "none"
    idx = int(np.argmax(np.abs(vector)))
    return ("x", "y", "z")[idx]


def _frame_features(process_row: dict[str, Any], readout_row: dict[str, Any], interface_row: dict[str, Any]) -> dict[str, float | str | np.ndarray | bool]:
    track_payloads = _track_payloads(interface_row)
    axial_fluxes: list[float] = []
    swirl_fluxes: list[float] = []
    polarity: list[float] = []
    circulation: list[float] = []
    circulation_strength: list[float] = []
    direction_vectors: list[list[float]] = []
    circulation_vectors: list[list[float]] = []

    for payload in track_payloads:
        channels = payload.get("global_channels", {})
        axial_fluxes.append(float(channels.get("axial_flux", 0.0)))
        swirl_fluxes.append(float(channels.get("swirl_flux", 0.0)))
        polarity.append(float(channels.get("polarity_projection", 0.0)))
        circulation.append(float(channels.get("circulation_projection", 0.0)))
        circulation_strength.append(float(channels.get("circulation_strength", 0.0)))
        direction_vectors.append(payload.get("direction_vector", [0.0, 0.0, 0.0]))
        circulation_vectors.append(payload.get("circulation_vector", [0.0, 0.0, 0.0]))

    mean_axial_flux = _mean(axial_fluxes)
    mean_swirl_flux = _mean(swirl_fluxes)
    mean_abs_polarity = _mean([abs(v) for v in polarity])
    mean_abs_circulation = _mean([abs(v) for v in circulation])
    mean_circulation_strength = _mean(circulation_strength)
    mean_direction_vector = _vector_mean(direction_vectors)
    mean_circulation_vector = _vector_mean(circulation_vectors)
    axis_source = np.asarray(process_row.get("dominant_axis", [0.0, 0.0, 0.0]), dtype=np.float64)
    translation_channel = float(readout_row.get("translation_channel", 0.0))
    rotation_channel = float(readout_row.get("rotation_channel", 0.0))
    translation_context = _clip01(
        4.00 * max(mean_axial_flux - mean_swirl_flux, 0.0)
        + 4.00 * max(translation_channel - rotation_channel, 0.0)
    )
    mean_direction_axis = _axis_label(mean_direction_vector)
    source_axis = _axis_label(axis_source, min_norm=0.18)
    anchored_direction_vector = mean_direction_vector
    if (
        translation_context > 0.0
        and source_axis != "none"
        and mean_direction_axis != source_axis
    ):
        anchor_weight = _clip01(0.45 + 0.70 * translation_context)
        anchored_direction_vector = ((1.0 - anchor_weight) * mean_direction_vector) + (anchor_weight * axis_source)

    x_direction = float(abs(anchored_direction_vector[0]))
    z_circulation = float(abs(mean_circulation_vector[2]))
    z_circulation_blocker = _clip01(translation_context * max(z_circulation - x_direction, 0.0))

    static_like = _clip01(
        0.50 * float(process_row.get("static_index", 0.0))
        + 0.18 * float(readout_row.get("static_channel", 0.0))
        + 0.12 * (1.0 - float(process_row.get("motion_index", 0.0)))
        + 0.20 * float(process_row.get("recovery_index", 0.0))
    )
    translation_like = _clip01(
        1.60 * max(mean_axial_flux - mean_swirl_flux, 0.0)
        + 0.72 * x_direction
        + 0.45 * translation_channel
        + 0.30 * mean_abs_polarity
        + 0.22 * z_circulation_blocker
    )
    rotation_like = _clip01(
        1.60 * max(mean_swirl_flux - mean_axial_flux, 0.0)
        + 0.75 * z_circulation
        + 0.45 * rotation_channel
        + 0.25 * mean_circulation_strength
        + 0.15 * mean_abs_circulation
        - 0.60 * z_circulation_blocker
    )

    dominant_scores = {
        "static_like": static_like,
        "translation_like": translation_like,
        "rotation_like": rotation_like,
    }
    sorted_modes = sorted(dominant_scores.items(), key=lambda kv: kv[1], reverse=True)
    top_mode, top_score = sorted_modes[0]
    second_score = sorted_modes[1][1]
    margin = float(top_score - second_score)
    if top_score < 0.20 or margin < 0.035:
        dominant_mode = "mixed"
    else:
        dominant_mode = top_mode

    axis_source = np.asarray(process_row.get("dominant_axis", [0.0, 0.0, 0.0]), dtype=np.float64)
    if dominant_mode == "translation_like":
        dominant_axis = _axis_label(anchored_direction_vector)
    elif dominant_mode == "rotation_like":
        dominant_axis = _axis_label(mean_circulation_vector)
    elif dominant_mode == "static_like":
        dominant_axis = "none"
    else:
        dominant_axis = _axis_label(axis_source, min_norm=0.18)

    return {
        "transition_state": str(process_row.get("transition_state", "baseline")),
        "stimulus_active": bool(process_row.get("stimulus_active", False)),
        "onset_event": bool(process_row.get("onset_event", False)),
        "offset_event": bool(process_row.get("offset_event", False)),
        "dominant_mode": dominant_mode,
        "dominant_axis": dominant_axis,
        "static_like": static_like,
        "translation_like": translation_like,
        "rotation_like": rotation_like,
        "mode_margin": margin,
        "recovery_score": _clip01(
            0.70 * float(process_row.get("recovery_index", 0.0))
            + 0.30 * float(readout_row.get("recovery_channel", 0.0))
        ),
        "mean_axial_flux": mean_axial_flux,
        "mean_swirl_flux": mean_swirl_flux,
        "mean_x_direction": x_direction,
        "mean_z_circulation": z_circulation,
        "mean_translation_channel": translation_channel,
        "mean_rotation_channel": rotation_channel,
        "translation_context": translation_context,
        "z_circulation_blocker": z_circulation_blocker,
        "mean_static_channel": float(readout_row.get("static_channel", 0.0)),
        "mean_onset_channel": float(readout_row.get("onset_channel", 0.0)),
        "mean_recovery_channel": float(readout_row.get("recovery_channel", 0.0)),
    }


def _phase_from_window(rows: list[dict[str, Any]]) -> str:
    transition_counts: dict[str, int] = {}
    onset_any = False
    offset_any = False
    active_count = 0
    recovery_score = 0.0
    for row in rows:
        state = str(row.get("transition_state", "baseline"))
        transition_counts[state] = transition_counts.get(state, 0) + 1
        onset_any = onset_any or bool(row.get("onset_event", False))
        offset_any = offset_any or bool(row.get("offset_event", False))
        active_count += int(bool(row.get("stimulus_active", False)))
        recovery_score += float(row.get("recovery_score", 0.0))
    if active_count >= max(1, math.ceil(0.5 * len(rows))):
        if onset_any or transition_counts.get("stimulus_onset", 0) > 0:
            onset_votes = transition_counts.get("stimulus_onset", 0) + int(onset_any)
            if onset_votes >= max(1, math.ceil(0.5 * len(rows))):
                return "onset"
        return "active"
    if onset_any or transition_counts.get("stimulus_onset", 0) > 0:
        return "onset"
    if offset_any:
        return "offset"
    if transition_counts.get("recovery", 0) > 0 or transition_counts.get("post_stimulus_drift", 0) > 0 or transition_counts.get("recovered_static", 0) > 0:
        if recovery_score / max(1, len(rows)) >= 0.18 or transition_counts.get("recovered_static", 0) > 0:
            return "recovery"
        return "offset"
    return "baseline"


def _window_record(rows: list[dict[str, Any]], start_t: float, end_t: float) -> ProcessCalculatorWindow:
    phase = _phase_from_window(rows)
    mode_counts: dict[str, int] = {}
    axis_counts: dict[str, int] = {}
    for row in rows:
        mode = str(row.get("dominant_mode", "mixed"))
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        axis = str(row.get("dominant_axis", "none"))
        axis_counts[axis] = axis_counts.get(axis, 0) + 1
    dominant_mode = max(mode_counts.items(), key=lambda kv: kv[1])[0]
    if dominant_mode == "mixed":
        mean_static = _mean([float(r.get("static_like", 0.0)) for r in rows])
        mean_translation = _mean([float(r.get("translation_like", 0.0)) for r in rows])
        mean_rotation = _mean([float(r.get("rotation_like", 0.0)) for r in rows])
        scores = {
            "static_like": mean_static,
            "translation_like": mean_translation,
            "rotation_like": mean_rotation,
        }
        best_mode, best_score = max(scores.items(), key=lambda kv: kv[1])
        second_score = sorted(scores.values(), reverse=True)[1]
        if best_score >= 0.25 and best_score - second_score >= 0.03:
            dominant_mode = best_mode
    dominant_axis = max(axis_counts.items(), key=lambda kv: kv[1])[0]
    if dominant_mode == "static_like":
        dominant_axis = "none"

    stability = _clip01(mode_counts.get(dominant_mode, 0) / max(1, len(rows)))
    recovery_score = _clip01(_mean([float(r.get("recovery_score", 0.0)) for r in rows]))
    mode_margin = max(0.0, _mean([float(r.get("mode_margin", 0.0)) for r in rows]))

    contributions = {
        "static_like": _mean([float(r.get("static_like", 0.0)) for r in rows]),
        "translation_like": _mean([float(r.get("translation_like", 0.0)) for r in rows]),
        "rotation_like": _mean([float(r.get("rotation_like", 0.0)) for r in rows]),
        "mean_static_channel": _mean([float(r.get("mean_static_channel", 0.0)) for r in rows]),
        "mean_translation_channel": _mean([float(r.get("mean_translation_channel", 0.0)) for r in rows]),
        "mean_rotation_channel": _mean([float(r.get("mean_rotation_channel", 0.0)) for r in rows]),
        "mean_onset_channel": _mean([float(r.get("mean_onset_channel", 0.0)) for r in rows]),
        "mean_recovery_channel": _mean([float(r.get("mean_recovery_channel", 0.0)) for r in rows]),
        "mean_axial_flux": _mean([float(r.get("mean_axial_flux", 0.0)) for r in rows]),
        "mean_swirl_flux": _mean([float(r.get("mean_swirl_flux", 0.0)) for r in rows]),
        "mean_x_direction": _mean([float(r.get("mean_x_direction", 0.0)) for r in rows]),
        "mean_z_circulation": _mean([float(r.get("mean_z_circulation", 0.0)) for r in rows]),
    }

    return ProcessCalculatorWindow(
        phase=phase,
        dominant_mode=dominant_mode,
        dominant_axis=dominant_axis,
        stability_score=stability,
        recovery_score=recovery_score,
        mode_margin=mode_margin,
        channel_contributions=contributions,
        window_start=start_t,
        window_end=end_t,
    )


def build_process_calculator_trace(
    process_trace: list[dict[str, Any]],
    readout_trace: list[dict[str, Any]],
    interface_network_trace: list[dict[str, Any]],
    *,
    window_size: int = 3,
    stride: int = 1,
) -> list[dict[str, Any]]:
    aligned_rows = _iter_aligned_rows(process_trace, readout_trace, interface_network_trace)
    if not aligned_rows:
        return []
    per_frame = [_frame_features(p, r, n) for p, r, n in aligned_rows]
    out: list[dict[str, Any]] = []
    step = max(1, stride)
    size = max(1, window_size)
    for start in range(0, len(aligned_rows), step):
        end = min(len(aligned_rows), start + size)
        if end - start <= 0:
            continue
        time_start = float(aligned_rows[start][0].get("time", 0.0))
        time_end = float(aligned_rows[end - 1][0].get("time", time_start))
        record = _window_record(per_frame[start:end], time_start, time_end).to_dict()
        record["num_frames"] = int(end - start)
        out.append(record)
        if end >= len(aligned_rows):
            break
    return out


def build_process_calculator_trace_from_files(
    *,
    motion_state_path: str | Path,
    readout_path: str | Path,
    interface_network_path: str | Path,
    window_size: int = 3,
    stride: int = 1,
) -> list[dict[str, Any]]:
    return build_process_calculator_trace(
        _load_json(motion_state_path),
        _load_json(readout_path),
        _load_json(interface_network_path),
        window_size=window_size,
        stride=stride,
    )


def summarize_process_calculator_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_windows": 0,
            "dominant_mode": "none",
            "dominant_phase": "none",
            "mode_counts": {},
            "phase_counts": {},
            "mean_stability_score": 0.0,
            "mean_recovery_score": 0.0,
            "mean_mode_margin": 0.0,
            "active_summary": {},
            "phase_windows": {},
        }
    mode_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    phase_windows: dict[str, dict[str, Any]] = {}
    for row in trace:
        mode = str(row.get("dominant_mode", "mixed"))
        phase = str(row.get("phase", "baseline"))
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        bucket = phase_windows.setdefault(phase, {
            "num_windows": 0,
            "mode_counts": {},
            "mean_stability_score": 0.0,
            "mean_recovery_score": 0.0,
            "mean_mode_margin": 0.0,
        })
        bucket["num_windows"] += 1
        mc = bucket["mode_counts"]
        mc[mode] = mc.get(mode, 0) + 1
        bucket["mean_stability_score"] += float(row.get("stability_score", 0.0))
        bucket["mean_recovery_score"] += float(row.get("recovery_score", 0.0))
        bucket["mean_mode_margin"] += float(row.get("mode_margin", 0.0))
    for bucket in phase_windows.values():
        n = max(1, int(bucket["num_windows"]))
        bucket["mean_stability_score"] /= n
        bucket["mean_recovery_score"] /= n
        bucket["mean_mode_margin"] /= n
        bucket["dominant_mode"] = max(bucket["mode_counts"].items(), key=lambda kv: kv[1])[0]

    dominant_mode = max(mode_counts.items(), key=lambda kv: kv[1])[0]
    dominant_phase = max(phase_counts.items(), key=lambda kv: kv[1])[0]
    active_rows = [row for row in trace if str(row.get("phase", "")) == "active"]
    active_mode_counts: dict[str, int] = {}
    for row in active_rows:
        mode = str(row.get("dominant_mode", "mixed"))
        active_mode_counts[mode] = active_mode_counts.get(mode, 0) + 1
    active_dominant = max(active_mode_counts.items(), key=lambda kv: kv[1])[0] if active_mode_counts else "none"
    return {
        "num_windows": int(len(trace)),
        "dominant_mode": dominant_mode,
        "dominant_phase": dominant_phase,
        "mode_counts": mode_counts,
        "phase_counts": phase_counts,
        "mean_stability_score": _mean([float(row.get("stability_score", 0.0)) for row in trace]),
        "mean_recovery_score": _mean([float(row.get("recovery_score", 0.0)) for row in trace]),
        "mean_mode_margin": _mean([float(row.get("mode_margin", 0.0)) for row in trace]),
        "active_summary": {
            "num_windows": int(len(active_rows)),
            "dominant_mode": active_dominant,
            "mode_counts": active_mode_counts,
            "mean_stability_score": _mean([float(row.get("stability_score", 0.0)) for row in active_rows]),
            "mean_mode_margin": _mean([float(row.get("mode_margin", 0.0)) for row in active_rows]),
        },
        "phase_windows": phase_windows,
    }
