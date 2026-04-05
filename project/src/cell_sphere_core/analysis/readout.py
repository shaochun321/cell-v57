from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


@dataclass(frozen=True)
class ExternalReadoutSnapshot:
    magnitude_channel: float
    static_channel: float
    translation_channel: float
    rotation_channel: float
    onset_channel: float
    recovery_channel: float
    direction_channels: dict[str, float]
    shell_responses: list[dict[str, float | str]]
    readout_class: str
    readout_confidence: float
    channel_margin: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "magnitude_channel": float(self.magnitude_channel),
            "static_channel": float(self.static_channel),
            "translation_channel": float(self.translation_channel),
            "rotation_channel": float(self.rotation_channel),
            "onset_channel": float(self.onset_channel),
            "recovery_channel": float(self.recovery_channel),
            "direction_channels": {k: float(v) for k, v in self.direction_channels.items()},
            "shell_responses": [
                {"shell": str(item["shell"]), "response": float(item["response"]), "role": str(item["role"])}
                for item in self.shell_responses
            ],
            "readout_class": self.readout_class,
            "readout_confidence": float(self.readout_confidence),
            "channel_margin": float(self.channel_margin),
        }


def _direction_channels(axis: list[float] | np.ndarray, signal_strength: float) -> dict[str, float]:
    vec = np.asarray(axis, dtype=np.float64)
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        vec = np.zeros(3, dtype=np.float64)
    else:
        vec = vec / norm
    pos = np.maximum(vec, 0.0) * float(signal_strength)
    neg = np.maximum(-vec, 0.0) * float(signal_strength)
    return {
        "x_pos": float(pos[0]),
        "x_neg": float(neg[0]),
        "y_pos": float(pos[1]),
        "y_neg": float(neg[1]),
        "z_pos": float(pos[2]),
        "z_neg": float(neg[2]),
    }


def compute_external_readout_snapshot(process_row: dict[str, Any]) -> ExternalReadoutSnapshot:
    magnitude = _clip01(0.65 * float(process_row.get("force_magnitude_index", 0.0)) + 0.35 * float(process_row.get("motion_index", 0.0)))
    static_channel = _clip01(
        0.78 * float(process_row.get("static_index", 0.0))
        + 0.22 * float(process_row.get("shape_integrity_index", 0.0))
        - 0.18 * float(process_row.get("motion_index", 0.0))
    )
    translation_channel = _clip01(
        float(process_row.get("motion_index", 0.0))
        * float(process_row.get("dipole_ratio", 0.0))
        * (0.62 + 0.38 * float(process_row.get("motion_confidence", 0.0)))
    )
    rotation_channel = _clip01(
        float(process_row.get("motion_index", 0.0))
        * float(process_row.get("quadrupole_ratio", 0.0))
        * (0.62 + 0.38 * float(process_row.get("motion_confidence", 0.0)))
    )

    transition_state = str(process_row.get("transition_state", "baseline"))
    onset_event = bool(process_row.get("onset_event", False))
    offset_event = bool(process_row.get("offset_event", False))
    onset_channel = _clip01(
        (1.0 if onset_event else 0.0)
        + 0.55 * max(float(process_row.get("motion_delta", 0.0)), 0.0)
        + (0.35 if transition_state == "stimulus_onset" else 0.0)
    )
    recovery_channel = _clip01(
        0.65 * float(process_row.get("recovery_index", 0.0))
        + 0.20 * (1.0 if offset_event else 0.0)
        + (0.15 if transition_state in {"recovery", "recovered_static"} else 0.0)
    )

    directional_strength = max(translation_channel, rotation_channel)
    direction_channels = _direction_channels(process_row.get("dominant_axis", [0.0, 0.0, 0.0]), directional_strength)

    shell_responses = [
        {
            "shell": "shell_0_reference",
            "role": "stable baseline / relative stillness",
            "response": _clip01(0.82 * static_channel + 0.18 * recovery_channel),
        },
        {
            "shell": "shell_1_translation",
            "role": "dipole-like translation readout",
            "response": translation_channel,
        },
        {
            "shell": "shell_2_rotation",
            "role": "quadrupole-like rotation readout",
            "response": rotation_channel,
        },
        {
            "shell": "shell_3_transition",
            "role": "onset / recovery event readout",
            "response": _clip01(max(onset_channel, recovery_channel)),
        },
    ]

    stimulus_active = bool(process_row.get("stimulus_active", False))
    process_motion_class = str(process_row.get("motion_class", "unknown"))
    if ((not stimulus_active) and static_channel >= max(translation_channel, rotation_channel)) or process_motion_class == "static":
        readout_class = "static"
        confidence = max(static_channel, float(process_row.get("static_index", 0.0)))
        margin = static_channel - max(translation_channel, rotation_channel)
    elif translation_channel > rotation_channel * 1.04:
        readout_class = "translation"
        confidence = translation_channel
        margin = translation_channel - rotation_channel
    elif rotation_channel > translation_channel * 1.04:
        readout_class = "rotation"
        confidence = rotation_channel
        margin = rotation_channel - translation_channel
    else:
        readout_class = "mixed"
        confidence = max(translation_channel, rotation_channel, static_channel)
        margin = abs(translation_channel - rotation_channel)

    return ExternalReadoutSnapshot(
        magnitude_channel=magnitude,
        static_channel=static_channel,
        translation_channel=translation_channel,
        rotation_channel=rotation_channel,
        onset_channel=onset_channel,
        recovery_channel=recovery_channel,
        direction_channels=direction_channels,
        shell_responses=shell_responses,
        readout_class=readout_class,
        readout_confidence=_clip01(confidence),
        channel_margin=float(max(margin, 0.0)),
    )


def build_external_readout_trace(process_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in process_trace:
        snapshot = compute_external_readout_snapshot(row).to_dict()
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            **snapshot,
        })
    return rows


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return float(np.mean([float(row.get(key, 0.0)) for row in rows]))


def _count(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key, "unknown"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def summarize_external_readout_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "dominant_readout_class": "none",
            "class_counts": {},
            "mean_static_channel": 0.0,
            "mean_translation_channel": 0.0,
            "mean_rotation_channel": 0.0,
            "mean_onset_channel": 0.0,
            "mean_recovery_channel": 0.0,
            "separation_margin_mean": 0.0,
            "active_summary": {},
            "virtual_shells": [],
        }
    class_counts = _count(trace, "readout_class")
    dominant = max(class_counts.items(), key=lambda kv: kv[1])[0]
    active_rows = [row for row in trace if bool(row.get("stimulus_active", False))]
    active_counts = _count(active_rows, "readout_class") if active_rows else {}
    active_dominant = max(active_counts.items(), key=lambda kv: kv[1])[0] if active_counts else "none"

    shell_names: list[str] = []
    if trace and trace[0].get("shell_responses"):
        shell_names = [str(item.get("shell", "shell")) for item in trace[0]["shell_responses"]]
    virtual_shells = []
    for shell_name in shell_names:
        vals = []
        for row in trace:
            for shell_item in row.get("shell_responses", []):
                if str(shell_item.get("shell")) == shell_name:
                    vals.append(float(shell_item.get("response", 0.0)))
        virtual_shells.append({
            "shell": shell_name,
            "mean_response": float(np.mean(vals)) if vals else 0.0,
            "peak_response": float(np.max(vals)) if vals else 0.0,
        })

    payload = {
        "num_samples": int(len(trace)),
        "dominant_readout_class": dominant,
        "class_counts": class_counts,
        "mean_static_channel": _mean(trace, "static_channel"),
        "mean_translation_channel": _mean(trace, "translation_channel"),
        "mean_rotation_channel": _mean(trace, "rotation_channel"),
        "mean_onset_channel": _mean(trace, "onset_channel"),
        "mean_recovery_channel": _mean(trace, "recovery_channel"),
        "separation_margin_mean": _mean(trace, "channel_margin"),
        "active_summary": {
            "num_samples": int(len(active_rows)),
            "dominant_readout_class": active_dominant,
            "class_counts": active_counts,
            "mean_static_channel": _mean(active_rows, "static_channel"),
            "mean_translation_channel": _mean(active_rows, "translation_channel"),
            "mean_rotation_channel": _mean(active_rows, "rotation_channel"),
            "mean_onset_channel": _mean(active_rows, "onset_channel"),
            "mean_recovery_channel": _mean(active_rows, "recovery_channel"),
            "separation_margin_mean": _mean(active_rows, "channel_margin"),
        },
        "virtual_shells": virtual_shells,
    }

    if active_rows:
        stimulus_mode = str(active_rows[0].get("stimulus_mode") or "none")
    else:
        stimulus_mode = str(trace[0].get("stimulus_mode") or "none")
    if stimulus_mode == "translation":
        payload["matched_channel_advantage"] = float(
            _mean(active_rows, "translation_channel") - _mean(active_rows, "rotation_channel")
        )
    elif stimulus_mode == "rotation":
        payload["matched_channel_advantage"] = float(
            _mean(active_rows, "rotation_channel") - _mean(active_rows, "translation_channel")
        )
    elif stimulus_mode in {"none", "null", "static"}:
        payload["matched_channel_advantage"] = float(
            _mean(trace, "static_channel") - max(_mean(trace, "translation_channel"), _mean(trace, "rotation_channel"))
        )
    else:
        payload["matched_channel_advantage"] = 0.0
    return payload
