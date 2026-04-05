from __future__ import annotations

import json
from pathlib import Path
import numpy as np


def compute_multipole_energy_numpy(polar: np.ndarray, azimuthal: np.ndarray, field: np.ndarray) -> dict[str, float]:
    polar = np.asarray(polar, dtype=np.float64)
    azimuthal = np.asarray(azimuthal, dtype=np.float64)
    field = np.asarray(field, dtype=np.float64)
    n = int(field.size)
    if n == 0:
        return {"l=0": 0.0, "l=1": 0.0, "l=2": 0.0, "total": 0.0}

    d_omega = 4.0 * np.pi / n
    energies: dict[str, float] = {"l=0": 0.0, "l=1": 0.0, "l=2": 0.0}

    y00 = np.ones(n) * np.sqrt(1.0 / (4.0 * np.pi))
    energies["l=0"] = float(np.abs(np.sum(field * y00) * d_omega) ** 2)

    y10 = np.sqrt(3.0 / (4.0 * np.pi)) * np.cos(polar)
    y11 = -np.sqrt(3.0 / (8.0 * np.pi)) * np.sin(polar) * np.exp(1j * azimuthal)
    y1m1 = np.sqrt(3.0 / (8.0 * np.pi)) * np.sin(polar) * np.exp(-1j * azimuthal)
    energies["l=1"] = float(sum(np.abs(np.sum(field * np.conj(y)) * d_omega) ** 2 for y in (y10, y11, y1m1)))

    y20 = np.sqrt(5.0 / (16.0 * np.pi)) * (3.0 * np.cos(polar) ** 2 - 1.0)
    y21 = -np.sqrt(15.0 / (8.0 * np.pi)) * np.sin(polar) * np.cos(polar) * np.exp(1j * azimuthal)
    y2m1 = np.sqrt(15.0 / (8.0 * np.pi)) * np.sin(polar) * np.cos(polar) * np.exp(-1j * azimuthal)
    y22 = np.sqrt(15.0 / (32.0 * np.pi)) * np.sin(polar) ** 2 * np.exp(2j * azimuthal)
    y2m2 = np.sqrt(15.0 / (32.0 * np.pi)) * np.sin(polar) ** 2 * np.exp(-2j * azimuthal)
    energies["l=2"] = float(sum(np.abs(np.sum(field * np.conj(y)) * d_omega) ** 2 for y in (y20, y21, y2m1, y22, y2m2)))
    energies["total"] = float(energies["l=0"] + energies["l=1"] + energies["l=2"])
    return energies


def _select_band_frame(frame: dict, band: int | str = "outer") -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    layers = frame.get("layers", [])
    if not layers:
        surface = frame.get("surface_nodes")
        if not surface:
            return np.zeros(0), np.zeros(0), {}
        polar = np.asarray(surface.get("polar", []), dtype=np.float64)
        az = np.asarray(surface.get("azimuthal", []), dtype=np.float64)
        field = np.asarray(surface.get("field", []), dtype=np.float64)
        return polar, az, {str(surface.get("field_name", "field")): field, "field": field}

    if band == "outer":
        layer = max(layers, key=lambda item: int(item.get("band_index", -1)))
    elif band == "inner":
        layer = min(layers, key=lambda item: int(item.get("band_index", 10**9)))
    else:
        target = int(band)
        candidates = [layer for layer in layers if int(layer.get("band_index", -1)) == target]
        layer = candidates[0] if candidates else {"nodes": []}
    nodes = layer.get("nodes", [])
    polar = np.asarray([node.get("polar", 0.0) for node in nodes], dtype=np.float64)
    az = np.asarray([node.get("azimuthal", 0.0) for node in nodes], dtype=np.float64)
    fields: dict[str, np.ndarray] = {}
    if nodes:
        for key in nodes[0].keys():
            if key in {"id", "band_index", "is_surface", "pos_abs", "pos_rel"}:
                continue
            if isinstance(nodes[0].get(key), (int, float, bool)):
                fields[key] = np.asarray([float(node.get(key, 0.0)) for node in nodes], dtype=np.float64)
    return polar, az, fields


def load_sensor_nodes_jsonl(path: str | Path) -> list[dict]:
    frames: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                frames.append(json.loads(line))
    return frames


def analyze_sensor_frames(frames: list[dict], *, band: int | str = "outer", field_name: str = "u_r") -> list[dict]:
    results: list[dict] = []
    for frame in frames:
        polar, az, fields = _select_band_frame(frame, band=band)
        field = np.asarray(fields.get(field_name, np.zeros_like(polar)), dtype=np.float64)
        energies = compute_multipole_energy_numpy(polar, az, field)
        results.append({
            "time": float(frame.get("time", 0.0)),
            "field_name": field_name,
            "band": band,
            "stimulus_active": bool(frame.get("stimulus", {}).get("active", False)),
            **energies,
        })
    return results


def summarize_energy_series(series: list[dict]) -> dict[str, float]:
    if not series:
        return {"mean_l1": 0.0, "mean_l2": 0.0, "peak_l1": 0.0, "peak_l2": 0.0, "l1_over_l2": 0.0, "l2_over_l1": 0.0}
    l1 = np.asarray([row["l=1"] for row in series], dtype=np.float64)
    l2 = np.asarray([row["l=2"] for row in series], dtype=np.float64)
    return {
        "mean_l1": float(np.mean(l1)),
        "mean_l2": float(np.mean(l2)),
        "peak_l1": float(np.max(l1)),
        "peak_l2": float(np.max(l2)),
        "l1_over_l2": float(np.mean(l1) / max(np.mean(l2), 1e-12)),
        "l2_over_l1": float(np.mean(l2) / max(np.mean(l1), 1e-12)),
    }
