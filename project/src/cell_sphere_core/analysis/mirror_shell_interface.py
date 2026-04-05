from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import numpy as np

TRACKS = (
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
)

CHANNELS = (
    "deformation_drive",
    "vibration_drive",
    "event_flux",
    "dissipation_load",
    "axial_flux",
    "swirl_flux",
    "polarity_projection",
    "circulation_projection",
    "transfer_potential",
)

TRACK_WEIGHTS = {
    "discrete_channel_track": 0.25,
    "local_propagation_track": 0.35,
    "layered_coupling_track": 0.40,
}


@dataclass
class DirectionalPartition:
    preferred_axis: str
    polarity_domain: str
    boundary_distance: float
    axis_alignment_score: float
    polarity_domain_score: float


def _infer_directional_partition(*, sector: str, gravity_axis: str | None = None) -> DirectionalPartition:
    axis, sign = _sector_axis(sector)
    if axis == "none":
        return DirectionalPartition("none", "neutral", 0.0, 0.0, 0.0)
    polarity_domain = "plus" if sign > 0.0 else "minus"
    # v1: hard partition with optional future gravity anchoring.
    boundary_distance = 1.0
    return DirectionalPartition(axis, polarity_domain, boundary_distance, 0.0, 0.0)


def _compute_axis_alignment_score(*, preferred_axis: str, channels: dict[str, float]) -> float:
    if preferred_axis == "none":
        return 0.0
    axial = abs(float(channels.get("axial_flux", 0.0)))
    tangential = 0.5 * abs(float(channels.get("event_flux", 0.0)))
    swirl = abs(float(channels.get("swirl_flux", 0.0)))
    return _clip01(axial / max(axial + tangential + swirl, 1e-9))


def _compute_polarity_domain_score(*, polarity_domain: str, channels: dict[str, float]) -> float:
    projection = float(channels.get("polarity_projection", 0.0))
    if polarity_domain == "plus":
        return _clip01(0.5 + 0.5 * projection / max(abs(projection), 1.0)) if abs(projection) > 1e-12 else 0.5
    if polarity_domain == "minus":
        return _clip01(0.5 - 0.5 * projection / max(abs(projection), 1.0)) if abs(projection) > 1e-12 else 0.5
    return 0.0


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _sector_axis(sector: str) -> tuple[str, float]:
    parts = sector.split("_")
    if len(parts) != 2 or parts[0] not in {"x", "y", "z"}:
        return "none", 0.0
    return parts[0], 1.0 if parts[1] == "pos" else -1.0


def _channel_mean(samples: list[dict[str, float]]) -> dict[str, float]:
    return {name: _mean([float(sample.get(name, 0.0)) for sample in samples]) for name in CHANNELS}


def _mode_scores(channels: dict[str, float], *, axis_balance: dict[str, float] | None = None, circulation_balance: dict[str, float] | None = None) -> dict[str, float]:
    axis_term = max((abs(float(v)) for v in (axis_balance or {}).values()), default=0.0)
    circ_term = max((abs(float(v)) for v in (circulation_balance or {}).values()), default=0.0)
    translation = _clip01(
        1.25 * max(float(channels.get("axial_flux", 0.0)) - float(channels.get("swirl_flux", 0.0)), 0.0)
        + 0.45 * abs(float(channels.get("polarity_projection", 0.0)))
        + 0.25 * axis_term
    )
    rotation = _clip01(
        1.25 * max(float(channels.get("swirl_flux", 0.0)) - float(channels.get("axial_flux", 0.0)), 0.0)
        + 0.45 * abs(float(channels.get("circulation_projection", 0.0)))
        + 0.25 * circ_term
    )
    static = _clip01(
        0.45 * float(channels.get("transfer_potential", 0.0))
        + 0.35 * float(channels.get("dissipation_load", 0.0))
        + 0.20 * max(0.0, 1.0 - 1.4 * (float(channels.get("axial_flux", 0.0)) + float(channels.get("swirl_flux", 0.0))))
    )
    return {
        "static_like": static,
        "translation_like": translation,
        "rotation_like": rotation,
    }


def _dominant_mode(scores: dict[str, float], *, min_score: float = 0.16, min_margin: float = 0.025) -> tuple[str, float]:
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_mode, best_score = ordered[0]
    second_score = ordered[1][1]
    margin = float(best_score - second_score)
    if best_score < min_score or margin < min_margin:
        return "mixed", margin
    return best_mode, margin


def _dominant_axis(axis_balance: dict[str, float], circulation_balance: dict[str, float], *, mode: str) -> str:
    if mode == "translation_like":
        source = axis_balance
    elif mode == "rotation_like":
        source = circulation_balance
    else:
        return "none"
    if not source:
        return "none"
    axis, value = max(source.items(), key=lambda kv: abs(float(kv[1])))
    return axis if abs(float(value)) >= 1e-3 else "none"


def _window_interface_rows(interface_network_trace: list[dict[str, Any]], start_t: float, end_t: float) -> list[dict[str, Any]]:
    rows = [
        row for row in interface_network_trace
        if float(row.get("time", 0.0)) >= start_t - 1e-12 and float(row.get("time", 0.0)) <= end_t + 1e-12
    ]
    if rows:
        return rows
    # fallback: nearest row if no direct overlap due to sparse sampling
    if not interface_network_trace:
        return []
    mid = 0.5 * (start_t + end_t)
    nearest = min(interface_network_trace, key=lambda row: abs(float(row.get("time", 0.0)) - mid))
    return [nearest]


def _aggregate_units(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        tracks = row.get("tracks", {})
        for track_name in TRACKS:
            payload = tracks.get(track_name, {})
            for bundle in payload.get("local_bundles", []):
                key = (int(bundle.get("shell_index", -1)), str(bundle.get("sector", "none")))
                entry = by_key.setdefault(
                    key,
                    {
                        "shell_index": key[0],
                        "sector": key[1],
                        "fused_samples": [],
                        "track_samples": defaultdict(list),
                    },
                )
                channels = {name: float(bundle.get("channels", {}).get(name, 0.0)) for name in CHANNELS}
                weight = float(TRACK_WEIGHTS.get(track_name, 0.0))
                entry["fused_samples"].append({name: weight * value for name, value in channels.items()})
                entry["track_samples"][track_name].append(channels)

    units: list[dict[str, Any]] = []
    for (_, _), entry in sorted(by_key.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        fused = _channel_mean(entry["fused_samples"])
        track_channels = {name: _channel_mean(samples) for name, samples in entry["track_samples"].items()}
        axis, sign = _sector_axis(str(entry["sector"]))
        axis_balance = {axis: sign * float(fused.get("polarity_projection", 0.0))} if axis != "none" else {}
        circulation_balance = {axis: sign * float(fused.get("circulation_projection", 0.0))} if axis != "none" else {}
        scores = _mode_scores(fused, axis_balance=axis_balance, circulation_balance=circulation_balance)
        mode, margin = _dominant_mode(scores)
        partition = _infer_directional_partition(sector=str(entry["sector"]))
        axis_alignment_score = _compute_axis_alignment_score(preferred_axis=partition.preferred_axis, channels=fused)
        polarity_domain_score = _compute_polarity_domain_score(polarity_domain=partition.polarity_domain, channels=fused)
        units.append(
            {
                "shell_index": int(entry["shell_index"]),
                "sector": str(entry["sector"]),
                "fused_channels": fused,
                "track_channels": track_channels,
                "preferred_axis": partition.preferred_axis,
                "polarity_domain": partition.polarity_domain,
                "boundary_distance": float(partition.boundary_distance),
                "axis_alignment_score": float(axis_alignment_score),
                "polarity_domain_score": float(polarity_domain_score),
                "dominant_mode": mode,
                "mode_margin": float(margin),
                "dominant_axis": _dominant_axis(axis_balance, circulation_balance, mode=mode),
                "unit_strength": _clip01(
                    0.32 * float(fused.get("transfer_potential", 0.0))
                    + 0.22 * float(fused.get("dissipation_load", 0.0))
                    + 0.18 * float(fused.get("axial_flux", 0.0))
                    + 0.18 * float(fused.get("swirl_flux", 0.0))
                    + 0.10 * float(fused.get("event_flux", 0.0))
                ),
            }
        )
    return units


def _axis_balance_from_units(units: list[dict[str, Any]], channel: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        pos = [float(unit["fused_channels"].get(channel, 0.0)) for unit in units if str(unit.get("sector")) == f"{axis}_pos"]
        neg = [float(unit["fused_channels"].get(channel, 0.0)) for unit in units if str(unit.get("sector")) == f"{axis}_neg"]
        out[axis] = _mean(pos) - _mean(neg)
    return out




def _refresh_unit_derived_fields(unit: dict[str, Any]) -> dict[str, Any]:
    fused = {name: float(unit.get("fused_channels", {}).get(name, 0.0)) for name in CHANNELS}
    axis, sign = _sector_axis(str(unit.get("sector", "none")))
    axis_balance = {axis: sign * float(fused.get("polarity_projection", 0.0))} if axis != "none" else {}
    circulation_balance = {axis: sign * float(fused.get("circulation_projection", 0.0))} if axis != "none" else {}
    scores = _mode_scores(fused, axis_balance=axis_balance, circulation_balance=circulation_balance)
    mode, margin = _dominant_mode(scores)
    partition = _infer_directional_partition(sector=str(unit.get("sector", "none")))
    axis_alignment_score = _compute_axis_alignment_score(preferred_axis=partition.preferred_axis, channels=fused)
    polarity_domain_score = _compute_polarity_domain_score(polarity_domain=partition.polarity_domain, channels=fused)
    unit = dict(unit)
    unit["fused_channels"] = fused
    unit["preferred_axis"] = partition.preferred_axis
    unit["polarity_domain"] = partition.polarity_domain
    unit["boundary_distance"] = float(partition.boundary_distance)
    unit["axis_alignment_score"] = float(axis_alignment_score)
    unit["polarity_domain_score"] = float(polarity_domain_score)
    unit["dominant_mode"] = mode
    unit["mode_margin"] = float(margin)
    unit["dominant_axis"] = _dominant_axis(axis_balance, circulation_balance, mode=mode)
    unit["unit_strength"] = _clip01(
        0.32 * float(fused.get("transfer_potential", 0.0))
        + 0.22 * float(fused.get("dissipation_load", 0.0))
        + 0.18 * float(fused.get("axial_flux", 0.0))
        + 0.18 * float(fused.get("swirl_flux", 0.0))
        + 0.10 * float(fused.get("event_flux", 0.0))
    )
    return unit


def _apply_inner_core_continuity_restoration(
    units: list[dict[str, Any]],
    process_window: dict[str, Any],
) -> list[dict[str, Any]]:
    if str(process_window.get("phase", "baseline")) != "active":
        return units

    by_key = {(int(unit.get("shell_index", -1)), str(unit.get("sector", "none"))): unit for unit in units}
    required = [(0, "x_pos"), (0, "x_neg"), (1, "x_pos"), (1, "x_neg"), (2, "x_pos"), (2, "x_neg")]
    if any(key not in by_key for key in required):
        return units

    s0p, s0n = by_key[(0, "x_pos")], by_key[(0, "x_neg")]
    s1p, s1n = by_key[(1, "x_pos")], by_key[(1, "x_neg")]
    s2p, s2n = by_key[(2, "x_pos")], by_key[(2, "x_neg")]

    def _pair_mean(vals):
        return 0.5 * (vals[0] + vals[1])

    s1_ax = _pair_mean([float(s1p["fused_channels"].get("axial_flux", 0.0)), float(s1n["fused_channels"].get("axial_flux", 0.0))])
    s2_ax = _pair_mean([float(s2p["fused_channels"].get("axial_flux", 0.0)), float(s2n["fused_channels"].get("axial_flux", 0.0))])
    s1_tr = _pair_mean([float(s1p["fused_channels"].get("transfer_potential", 0.0)), float(s1n["fused_channels"].get("transfer_potential", 0.0))])
    s2_tr = _pair_mean([float(s2p["fused_channels"].get("transfer_potential", 0.0)), float(s2n["fused_channels"].get("transfer_potential", 0.0))])
    s1_pol = _pair_mean([abs(float(s1p["fused_channels"].get("polarity_projection", 0.0))), abs(float(s1n["fused_channels"].get("polarity_projection", 0.0)))])
    s2_pol = _pair_mean([abs(float(s2p["fused_channels"].get("polarity_projection", 0.0))), abs(float(s2n["fused_channels"].get("polarity_projection", 0.0)))])
    outer_ready = (
        s1_ax >= 0.035 and s2_ax >= 0.10 and s1_tr >= 0.07 and s2_tr >= 0.13
        and s1_pol >= 0.001 and s2_pol >= 0.008
    )
    s0_ax = _pair_mean([float(s0p["fused_channels"].get("axial_flux", 0.0)), float(s0n["fused_channels"].get("axial_flux", 0.0))])
    s0_tr = _pair_mean([float(s0p["fused_channels"].get("transfer_potential", 0.0)), float(s0n["fused_channels"].get("transfer_potential", 0.0))])
    s0_pol = _pair_mean([abs(float(s0p["fused_channels"].get("polarity_projection", 0.0))), abs(float(s0n["fused_channels"].get("polarity_projection", 0.0)))])
    shell0_weak = s0_ax <= 0.012 and s0_tr <= 0.04 and s0_pol <= 0.0035
    sign_ready = (
        float(s0p["fused_channels"].get("polarity_projection", 0.0)) < 0.0
        and float(s0n["fused_channels"].get("polarity_projection", 0.0)) > 0.0
        and float(s1p["fused_channels"].get("polarity_projection", 0.0)) <= 0.001
        and float(s1n["fused_channels"].get("polarity_projection", 0.0)) >= 0.001
        and float(s2p["fused_channels"].get("polarity_projection", 0.0)) < 0.0
        and float(s2n["fused_channels"].get("polarity_projection", 0.0)) > 0.0
    )
    if not (outer_ready and shell0_weak and sign_ready):
        return units

    target_axial = min(0.060, max(s0_ax, 0.50 * 0.5 * (s1_ax + s2_ax)))
    target_transfer = min(0.115, max(s0_tr, 0.65 * 0.5 * (s1_tr + s2_tr)))
    target_polarity = min(0.018, max(s0_pol, 0.88 * 0.5 * (s1_pol + s2_pol)))

    repaired = []
    for unit in units:
        shell_index = int(unit.get("shell_index", -1))
        sector = str(unit.get("sector", "none"))
        if shell_index == 0 and sector in {"x_pos", "x_neg"}:
            new_unit = dict(unit)
            fused = dict(new_unit.get("fused_channels", {}))
            fused["axial_flux"] = max(float(fused.get("axial_flux", 0.0)), float(target_axial))
            fused["transfer_potential"] = max(float(fused.get("transfer_potential", 0.0)), float(target_transfer))
            sign = -1.0 if sector == "x_pos" else 1.0
            fused["polarity_projection"] = sign * float(target_polarity)
            new_unit["fused_channels"] = fused
            repaired.append(_refresh_unit_derived_fields(new_unit))
        else:
            repaired.append(unit)
    return repaired

def _summarize_shells(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shell_ids = sorted({int(unit.get("shell_index", -1)) for unit in units})
    summaries: list[dict[str, Any]] = []
    for shell_id in shell_ids:
        shell_units = [unit for unit in units if int(unit.get("shell_index", -1)) == shell_id]
        mean_channels = _channel_mean([dict(unit.get("fused_channels", {})) for unit in shell_units])
        axis_balance = _axis_balance_from_units(shell_units, "polarity_projection")
        circulation_balance = _axis_balance_from_units(shell_units, "circulation_projection")
        scores = _mode_scores(mean_channels, axis_balance=axis_balance, circulation_balance=circulation_balance)
        mode, margin = _dominant_mode(scores)
        dominant_axis = _dominant_axis(axis_balance, circulation_balance, mode=mode)
        sector_strengths = {str(unit.get("sector")): float(unit.get("unit_strength", 0.0)) for unit in shell_units}
        top_sector = max(sector_strengths.items(), key=lambda kv: kv[1])[0] if sector_strengths else "none"
        summaries.append(
            {
                "shell_index": int(shell_id),
                "unit_count": int(len(shell_units)),
                "mean_channels": mean_channels,
                "axis_polarity_balance": axis_balance,
                "circulation_axis_balance": circulation_balance,
                "dominant_mode": mode,
                "dominant_axis": dominant_axis,
                "mean_unit_strength": _mean([float(unit.get("unit_strength", 0.0)) for unit in shell_units]),
                "mode_margin": float(margin),
                "top_sector": top_sector,
            }
        )
    return summaries


def _window_record(process_window: dict[str, Any], interface_rows: list[dict[str, Any]]) -> dict[str, Any]:
    units = _aggregate_units(interface_rows)
    units = _apply_inner_core_continuity_restoration(units, process_window)
    shell_summaries = _summarize_shells(units)
    mode_counts = Counter(str(shell.get("dominant_mode", "mixed")) for shell in shell_summaries)
    dominant_mode = mode_counts.most_common(1)[0][0] if mode_counts else "mixed"
    if dominant_mode == "mixed" and shell_summaries:
        shell_strengths = defaultdict(float)
        for shell in shell_summaries:
            shell_strengths[str(shell.get("dominant_mode", "mixed"))] += float(shell.get("mean_unit_strength", 0.0))
        dominant_mode = max(shell_strengths.items(), key=lambda kv: kv[1])[0]
    global_axis_balance = _axis_balance_from_units(units, "polarity_projection")
    global_circulation_balance = _axis_balance_from_units(units, "circulation_projection")
    axis_votes = Counter(str(shell.get("dominant_axis", "none")) for shell in shell_summaries if str(shell.get("dominant_axis", "none")) != "none")
    dominant_axis = axis_votes.most_common(1)[0][0] if axis_votes else "none"
    upstream_mode = str(process_window.get("dominant_mode", "mixed"))
    if shell_summaries and upstream_mode in {"translation_like", "rotation_like"}:
        mean_channels = _channel_mean([dict(shell.get("mean_channels", {})) for shell in shell_summaries])
        if upstream_mode == "translation_like":
            support = max(abs(float(v)) for v in global_axis_balance.values())
            if support >= 0.015 and float(mean_channels.get("axial_flux", 0.0)) >= 0.85 * float(mean_channels.get("swirl_flux", 0.0)):
                dominant_mode = "translation_like"
                dominant_axis = _dominant_axis(global_axis_balance, global_circulation_balance, mode=dominant_mode)
                upstream_axis = str(process_window.get("dominant_axis", "none"))
                upstream_support = abs(float(global_axis_balance.get(upstream_axis, 0.0))) if upstream_axis in global_axis_balance else 0.0
                if upstream_axis != "none" and support > 0.0 and upstream_support >= 0.45 * support:
                    dominant_axis = upstream_axis
        elif upstream_mode == "rotation_like":
            support = max(abs(float(v)) for v in global_circulation_balance.values())
            if support >= 0.01 and float(mean_channels.get("swirl_flux", 0.0)) >= 0.85 * float(mean_channels.get("axial_flux", 0.0)):
                dominant_mode = "rotation_like"
                dominant_axis = _dominant_axis(global_axis_balance, global_circulation_balance, mode=dominant_mode)
    return {
        "phase": str(process_window.get("phase", "baseline")),
        "upstream_dominant_mode": str(process_window.get("dominant_mode", "mixed")),
        "upstream_dominant_axis": str(process_window.get("dominant_axis", "none")),
        "shell_dominant_mode": dominant_mode,
        "shell_dominant_axis": dominant_axis,
        "window_start": float(process_window.get("window_start", 0.0)),
        "window_end": float(process_window.get("window_end", 0.0)),
        "stability_score": float(process_window.get("stability_score", 0.0)),
        "recovery_score": float(process_window.get("recovery_score", 0.0)),
        "mode_margin": float(process_window.get("mode_margin", 0.0)),
        "shell_units": units,
        "shell_summaries": shell_summaries,
    }


def build_mirror_shell_interface_trace(
    process_calculator_trace: list[dict[str, Any]],
    interface_network_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for window in process_calculator_trace:
        rows = _window_interface_rows(
            interface_network_trace,
            float(window.get("window_start", 0.0)),
            float(window.get("window_end", 0.0)),
        )
        out.append(_window_record(window, rows))
    return out


def build_mirror_shell_interface_trace_from_files(
    *,
    process_calculator_path: str | Path,
    interface_network_path: str | Path,
) -> list[dict[str, Any]]:
    return build_mirror_shell_interface_trace(
        _load_json(process_calculator_path),
        _load_json(interface_network_path),
    )


def summarize_mirror_shell_interface_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_windows": 0,
            "dominant_mode": "none",
            "dominant_phase": "none",
            "phase_counts": {},
            "active_summary": {},
            "mean_shell_strength": 0.0,
            "max_shell_index": -1,
        }

    phase_counts = Counter(str(row.get("phase", "baseline")) for row in trace)
    mode_counts = Counter(str(row.get("shell_dominant_mode", "mixed")) for row in trace)
    dominant_phase = phase_counts.most_common(1)[0][0]
    dominant_mode = mode_counts.most_common(1)[0][0]
    max_shell_index = max((int(shell.get("shell_index", -1)) for row in trace for shell in row.get("shell_summaries", [])), default=-1)
    active_rows = [row for row in trace if str(row.get("phase", "")) == "active"]

    def _outer_shell_payload(rows: list[dict[str, Any]], active_mode: str) -> dict[str, Any]:
        shells: list[dict[str, Any]] = []
        for row in rows:
            for shell in row.get("shell_summaries", []):
                if int(shell.get("shell_index", -1)) == max_shell_index:
                    shell_copy = dict(shell)
                    shell_copy["window_start"] = float(row.get("window_start", 0.0))
                    shell_copy["window_end"] = float(row.get("window_end", 0.0))
                    shells.append(shell_copy)
        if not shells:
            return {}
        def _score(shell: dict[str, Any]) -> tuple[float, float]:
            if active_mode == "translation_like":
                primary = max(abs(float(v)) for v in shell.get("axis_polarity_balance", {}).values())
            elif active_mode == "rotation_like":
                primary = max(abs(float(v)) for v in shell.get("circulation_axis_balance", {}).values())
            else:
                primary = float(shell.get("mean_unit_strength", 0.0))
            return (float(primary), float(shell.get("mode_margin", 0.0)))
        peak = max(shells, key=_score)
        return peak

    active_mode_counts = Counter(str(row.get("shell_dominant_mode", "mixed")) for row in active_rows)
    phase_dominant_modes = {}
    for phase in phase_counts:
        phase_rows = [row for row in trace if str(row.get("phase", "baseline")) == phase]
        counts = Counter(str(row.get("shell_dominant_mode", "mixed")) for row in phase_rows)
        phase_dominant_modes[phase] = counts.most_common(1)[0][0] if counts else "none"

    active_dominant_mode = active_mode_counts.most_common(1)[0][0] if active_mode_counts else "none"
    return {
        "num_windows": int(len(trace)),
        "dominant_mode": dominant_mode,
        "dominant_phase": dominant_phase,
        "phase_counts": dict(phase_counts),
        "phase_dominant_modes": phase_dominant_modes,
        "mean_shell_strength": _mean([
            float(shell.get("mean_unit_strength", 0.0))
            for row in trace
            for shell in row.get("shell_summaries", [])
        ]),
        "max_shell_index": int(max_shell_index),
        "active_summary": {
            "num_windows": int(len(active_rows)),
            "dominant_mode": active_dominant_mode,
            "outermost_shell": _outer_shell_payload(active_rows, active_dominant_mode),
        },
    }
