from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _zero_vec() -> list[float]:
    return [0.0, 0.0, 0.0]


def _zero_mat() -> list[list[float]]:
    return [[0.0, 0.0, 0.0] for _ in range(3)]


def _outer(u: list[float]) -> list[list[float]]:
    return [[u[i] * u[j] for j in range(3)] for i in range(3)]


def _mat_add(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] + b[i][j] for j in range(3)] for i in range(3)]


def _mat_scale(a: list[list[float]], c: float) -> list[list[float]]:
    return [[a[i][j] * c for j in range(3)] for i in range(3)]


def _trace(a: list[list[float]]) -> float:
    return a[0][0] + a[1][1] + a[2][2]


def _norm(v: list[float]) -> float:
    return sum(x * x for x in v) ** 0.5


def _vec_add(a: list[float], b: list[float]) -> list[float]:
    return [a[i] + b[i] for i in range(3)]


def _vec_scale(v: list[float], c: float) -> list[float]:
    return [x * c for x in v]


def load_interface_trace(run_dir: Path) -> list[dict[str, Any]]:
    return json.loads((run_dir / "interface_trace.json").read_text())


def frame_overview(frame: dict[str, Any]) -> dict[str, float]:
    t_vec = _zero_vec()
    p_vec = _zero_vec()
    r_vec = _zero_vec()
    t_quad = _zero_mat()
    p_quad = _zero_mat()
    translation_energy = 0.0
    rotation_energy = 0.0
    event_energy = 0.0
    tonic_energy = 0.0
    potential_energy = 0.0

    for bundle in frame["interface_bundles"]:
        w = float(bundle.get("coupling_weight", 1.0))
        u = [float(x) for x in bundle["centroid_direction"]]
        ch = bundle["channels"]
        t = w * float(ch.get("translation_signal", 0.0))
        p = w * float(ch.get("polarity_signal", 0.0))
        r = w * float(ch.get("rotation_signal", 0.0))
        e = w * float(ch.get("fast_event", ch.get("burst_signal", 0.0)))
        tonic = w * float(ch.get("slow_tonic", 0.0))
        potential = w * float(ch.get("electrical_potential", 0.0))

        t_vec = _vec_add(t_vec, _vec_scale(u, t))
        p_vec = _vec_add(p_vec, _vec_scale(u, p))
        r_vec = _vec_add(r_vec, _vec_scale(u, r))

        proj = _outer(u)
        basis = [[3.0 * proj[i][j] - (1.0 if i == j else 0.0) for j in range(3)] for i in range(3)]
        t_quad = _mat_add(t_quad, _mat_scale(basis, t))
        p_quad = _mat_add(p_quad, _mat_scale(basis, p))

        translation_energy += abs(t)
        rotation_energy += abs(r)
        event_energy += abs(e)
        tonic_energy += abs(tonic)
        potential_energy += abs(potential)

    agg = frame.get("aggregate_channels", {})
    return {
        "translation_dipole_x": t_vec[0],
        "translation_dipole_y": t_vec[1],
        "translation_dipole_z": t_vec[2],
        "translation_dipole_norm": _norm(t_vec),
        "polarity_dipole_x": p_vec[0],
        "polarity_dipole_y": p_vec[1],
        "polarity_dipole_z": p_vec[2],
        "polarity_dipole_norm": _norm(p_vec),
        "rotation_dipole_x": r_vec[0],
        "rotation_dipole_y": r_vec[1],
        "rotation_dipole_z": r_vec[2],
        "rotation_dipole_norm": _norm(r_vec),
        "translation_energy": translation_energy,
        "rotation_energy": rotation_energy,
        "event_energy": event_energy,
        "tonic_energy": tonic_energy,
        "potential_energy": potential_energy,
        "translation_quad_xx": t_quad[0][0],
        "translation_quad_yy": t_quad[1][1],
        "translation_quad_zz": t_quad[2][2],
        "translation_quad_trace": _trace(t_quad),
        "polarity_quad_xx": p_quad[0][0],
        "polarity_quad_yy": p_quad[1][1],
        "polarity_quad_zz": p_quad[2][2],
        "polarity_quad_trace": _trace(p_quad),
        "agg_translation": float(agg.get("translation", 0.0)),
        "agg_rotation": float(agg.get("rotation", 0.0)),
        "agg_event": float(agg.get("event", 0.0)),
        "agg_static": float(agg.get("static", 0.0)),
        "agg_magnitude": float(agg.get("magnitude", 0.0)),
    }


def summarize_overview_from_trace(interface_trace: list[dict[str, Any]], tail: int = 3) -> dict[str, float]:
    start = max(0, len(interface_trace) - tail)
    frames = [frame_overview(interface_trace[i]) for i in range(start, len(interface_trace))]
    keys = list(frames[0].keys())
    out: dict[str, float] = {}
    for key in keys:
        vals = [f[key] for f in frames]
        out[f"overview_{key}_mean"] = mean(vals)
        peak = max(vals, key=lambda x: abs(x))
        out[f"overview_{key}_peak"] = peak
        out[f"overview_{key}_peak_abs"] = max(abs(x) for x in vals)
    # a few derived ratios for compact gate use
    eps = 1e-9
    out["overview_translation_to_rotation_ratio"] = out["overview_translation_energy_peak_abs"] / (out["overview_rotation_energy_peak_abs"] + eps)
    out["overview_translation_to_event_ratio"] = out["overview_translation_energy_peak_abs"] / (out["overview_event_energy_peak_abs"] + eps)
    out["overview_rotation_to_event_ratio"] = out["overview_rotation_energy_peak_abs"] / (out["overview_event_energy_peak_abs"] + eps)
    out["overview_polarity_to_translation_ratio"] = out["overview_polarity_dipole_norm_peak_abs"] / (out["overview_translation_dipole_norm_peak_abs"] + eps)
    return out


def extract_overview_features(run_dir: Path, tail: int = 3) -> dict[str, float]:
    interface_trace = load_interface_trace(run_dir)
    return summarize_overview_from_trace(interface_trace, tail=tail)
