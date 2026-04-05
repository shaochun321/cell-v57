from __future__ import annotations

from typing import Any
import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES, FAMILY_NAMES
from cell_sphere_core.analysis.interface_network import SECTOR_ORDER


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _adjacent_sector_pairs() -> list[tuple[str, str]]:
    order = list(SECTOR_ORDER)
    pairs: list[tuple[str, str]] = []
    if not order:
        return pairs
    for i, sector in enumerate(order):
        pairs.append((sector, order[(i + 1) % len(order)]))
    return pairs


def _response_atlas(spectral_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    shell_indices = sorted({int(b.get("shell_index", 0)) for b in spectral_bundles})
    atlas: dict[str, Any] = {
        "shell_indices": shell_indices,
        "sector_order": list(SECTOR_ORDER),
        "families": {},
        "bandwidth_map": [],
        "transfer_map": [],
    }
    for family_name in FAMILY_NAMES:
        rows = []
        for shell_index in shell_indices:
            row = []
            for sector in SECTOR_ORDER:
                vals = [
                    float(b.get("family_vector", {}).get(family_name, 0.0))
                    for b in spectral_bundles
                    if int(b.get("shell_index", 0)) == shell_index and str(b.get("sector", "")) == sector
                ]
                row.append(_mean(vals))
            rows.append(row)
        atlas["families"][family_name] = rows
    for field_name, out_key in (("bandwidth_proxy", "bandwidth_map"), ("transfer_level", "transfer_map")):
        rows = []
        for shell_index in shell_indices:
            row = []
            for sector in SECTOR_ORDER:
                vals = [
                    float(b.get(field_name, 0.0))
                    for b in spectral_bundles
                    if int(b.get("shell_index", 0)) == shell_index and str(b.get("sector", "")) == sector
                ]
                row.append(_mean(vals))
            rows.append(row)
        atlas[out_key] = rows
    return atlas


def _topology_nodes(spectral_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = []
    for b in spectral_bundles:
        nodes.append({
            "node_id": str(b.get("bundle_id", "")),
            "shell_index": int(b.get("shell_index", 0)),
            "sector": str(b.get("sector", "")),
            "dominant_family": str(b.get("dominant_family", "none")),
            "dominant_level": float(b.get("dominant_level", 0.0)),
            "bandwidth_proxy": float(b.get("bandwidth_proxy", 0.0)),
            "transfer_level": float(b.get("transfer_level", 0.0)),
            "signed_polarity": float(b.get("signed_polarity", 0.0)),
            "signed_circulation": float(b.get("signed_circulation", 0.0)),
        })
    return nodes


def _family_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    va = np.asarray([float(a.get("family_vector", {}).get(name, 0.0)) for name in FAMILY_NAMES], dtype=np.float64)
    vb = np.asarray([float(b.get("family_vector", {}).get(name, 0.0)) for name in FAMILY_NAMES], dtype=np.float64)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-12:
        return 0.0
    return float(np.clip(np.dot(va, vb) / denom, -1.0, 1.0))


def _topology_edges(spectral_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {(int(b.get("shell_index", 0)), str(b.get("sector", ""))): b for b in spectral_bundles}
    shells = sorted({int(b.get("shell_index", 0)) for b in spectral_bundles})
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    # lateral ring edges
    for shell_index in shells:
        for s0, s1 in _adjacent_sector_pairs():
            a = lookup.get((shell_index, s0))
            b = lookup.get((shell_index, s1))
            if a is None or b is None:
                continue
            edge_id = (str(a.get("bundle_id", "")), str(b.get("bundle_id", "")), "lateral")
            if edge_id in seen:
                continue
            seen.add(edge_id)
            sim = _family_similarity(a, b)
            weight = 0.5 * (float(a.get("transfer_level", 0.0)) + float(b.get("transfer_level", 0.0))) * (0.5 + 0.5 * sim)
            edges.append({
                "edge_type": "lateral",
                "from_node": str(a.get("bundle_id", "")),
                "to_node": str(b.get("bundle_id", "")),
                "from_shell": shell_index,
                "to_shell": shell_index,
                "weight": float(weight),
                "family_similarity": float(sim),
            })
    # radial shell-to-shell edges per sector
    for sector in SECTOR_ORDER:
        for s0, s1 in zip(shells, shells[1:]):
            a = lookup.get((s0, sector))
            b = lookup.get((s1, sector))
            if a is None or b is None:
                continue
            sim = _family_similarity(a, b)
            weight = 0.5 * (float(a.get("transfer_level", 0.0)) + float(b.get("transfer_level", 0.0))) * (0.5 + 0.5 * sim)
            edges.append({
                "edge_type": "radial",
                "from_node": str(a.get("bundle_id", "")),
                "to_node": str(b.get("bundle_id", "")),
                "from_shell": s0,
                "to_shell": s1,
                "sector": sector,
                "weight": float(weight),
                "family_similarity": float(sim),
            })
    return edges


def _family_topology(response_atlas: dict[str, Any], spectral_bundles: list[dict[str, Any]], topology_edges: list[dict[str, Any]]) -> dict[str, Any]:
    shell_indices = list(response_atlas.get("shell_indices", []))
    shell_profiles = {}
    sector_profiles = {}
    response_roughness = {}
    for family_name in FAMILY_NAMES:
        grid = np.asarray(response_atlas.get("families", {}).get(family_name, []), dtype=np.float64)
        if grid.size == 0:
            shell_profiles[family_name] = {str(shell): 0.0 for shell in shell_indices}
            sector_profiles[family_name] = {sector: 0.0 for sector in SECTOR_ORDER}
            response_roughness[family_name] = 0.0
            continue
        shell_profiles[family_name] = {str(shell): float(np.mean(grid[i])) for i, shell in enumerate(shell_indices)}
        sector_profiles[family_name] = {sector: float(np.mean(grid[:, j])) for j, sector in enumerate(SECTOR_ORDER)}
        diffs = []
        if grid.shape[0] > 1:
            diffs.extend(np.abs(np.diff(grid, axis=0)).ravel().tolist())
        if grid.shape[1] > 1:
            diffs.extend(np.abs(np.diff(grid, axis=1)).ravel().tolist())
        response_roughness[family_name] = _mean(diffs)
    edge_weight_mean = _mean([float(e.get("weight", 0.0)) for e in topology_edges])
    edge_weight_std = _std([float(e.get("weight", 0.0)) for e in topology_edges])
    lateral_weight_mean = _mean([float(e.get("weight", 0.0)) for e in topology_edges if str(e.get("edge_type")) == "lateral"])
    radial_weight_mean = _mean([float(e.get("weight", 0.0)) for e in topology_edges if str(e.get("edge_type")) == "radial"])
    family_dominance_counts = {name: 0 for name in FAMILY_NAMES}
    for b in spectral_bundles:
        dom = str(b.get("dominant_family", "none"))
        if dom in family_dominance_counts:
            family_dominance_counts[dom] += 1
    polarity_by_axis = {}
    for axis in ("x", "y", "z"):
        pos = [float(b.get("signed_polarity", 0.0)) for b in spectral_bundles if str(b.get("sector", "")) == f"{axis}_pos"]
        neg = [float(b.get("signed_polarity", 0.0)) for b in spectral_bundles if str(b.get("sector", "")) == f"{axis}_neg"]
        polarity_by_axis[axis] = _mean(pos) - _mean(neg)
    signed_circulation = _mean([float(b.get("signed_circulation", 0.0)) for b in spectral_bundles])
    return {
        "family_shell_profiles": shell_profiles,
        "family_sector_profiles": sector_profiles,
        "response_roughness": response_roughness,
        "edge_weight_mean": edge_weight_mean,
        "edge_weight_std": edge_weight_std,
        "lateral_edge_weight_mean": lateral_weight_mean,
        "radial_edge_weight_mean": radial_weight_mean,
        "family_dominance_counts": family_dominance_counts,
        "polarity_by_axis": polarity_by_axis,
        "signed_circulation": signed_circulation,
    }


def _track_payload(track_name: str, track_payload: dict[str, Any]) -> dict[str, Any]:
    spectral_bundles = list(track_payload.get("spectral_bundles", []))
    response_atlas = _response_atlas(spectral_bundles)
    topology_nodes = _topology_nodes(spectral_bundles)
    topology_edges = _topology_edges(spectral_bundles)
    family_topology = _family_topology(response_atlas, spectral_bundles, topology_edges)
    return {
        "track_name": track_name,
        "track_mode": str(track_payload.get("track_mode", "")),
        "response_atlas": response_atlas,
        "topology_nodes": topology_nodes,
        "topology_edges": topology_edges,
        "family_topology": family_topology,
        "source_direction_vector": track_payload.get("source_direction_vector", [0.0, 0.0, 0.0]),
        "source_circulation_vector": track_payload.get("source_circulation_vector", [0.0, 0.0, 0.0]),
    }


def build_interface_topology_trace(interface_spectrum_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in interface_spectrum_trace:
        tracks = row.get("tracks", {})
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "topology_structure": {
                "principle": "bundle-family topology and response atlas of interface transduction; no semantic recognition embedded in the channels",
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
                "sector_order": list(SECTOR_ORDER),
            },
            "tracks": {track_name: _track_payload(track_name, tracks.get(track_name, {})) for track_name in TRACK_NAMES},
        })
    return rows


def _summarize_track(rows: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    track_rows = [r.get("tracks", {}).get(track_name, {}) for r in rows]
    active_rows = [r.get("tracks", {}).get(track_name, {}) for r in rows if bool(r.get("stimulus_active", False))]

    def _family_mean(payloads: list[dict[str, Any]], family_name: str, profile_key: str = "family_shell_profiles") -> float:
        vals = []
        for p in payloads:
            profile = p.get("family_topology", {}).get(profile_key, {}).get(family_name, {})
            vals.extend([float(v) for v in profile.values()])
        return _mean(vals)

    def _roughness(payloads: list[dict[str, Any]], family_name: str) -> float:
        return _mean([float(p.get("family_topology", {}).get("response_roughness", {}).get(family_name, 0.0)) for p in payloads])

    def _edge_mean(payloads: list[dict[str, Any]], key: str) -> float:
        return _mean([float(p.get("family_topology", {}).get(key, 0.0)) for p in payloads])

    def _axis(payloads: list[dict[str, Any]], axis: str) -> float:
        return _mean([float(p.get("family_topology", {}).get("polarity_by_axis", {}).get(axis, 0.0)) for p in payloads])

    def _signed_circulation(payloads: list[dict[str, Any]]) -> float:
        return _mean([float(p.get("family_topology", {}).get("signed_circulation", 0.0)) for p in payloads])

    return {
        "num_samples": len(track_rows),
        "active_num_samples": len(active_rows),
        "family_shell_mean": {name: _family_mean(track_rows, name) for name in FAMILY_NAMES},
        "active_family_shell_mean": {name: _family_mean(active_rows, name) for name in FAMILY_NAMES},
        "family_response_roughness": {name: _roughness(track_rows, name) for name in FAMILY_NAMES},
        "active_family_response_roughness": {name: _roughness(active_rows, name) for name in FAMILY_NAMES},
        "edge_weight_mean": _edge_mean(track_rows, "edge_weight_mean"),
        "active_edge_weight_mean": _edge_mean(active_rows, "edge_weight_mean"),
        "lateral_edge_weight_mean": _edge_mean(track_rows, "lateral_edge_weight_mean"),
        "active_lateral_edge_weight_mean": _edge_mean(active_rows, "lateral_edge_weight_mean"),
        "radial_edge_weight_mean": _edge_mean(track_rows, "radial_edge_weight_mean"),
        "active_radial_edge_weight_mean": _edge_mean(active_rows, "radial_edge_weight_mean"),
        "axis_polarity_balance": {axis: _axis(track_rows, axis) for axis in ("x", "y", "z")},
        "active_axis_polarity_balance": {axis: _axis(active_rows, axis) for axis in ("x", "y", "z")},
        "mean_signed_circulation": _signed_circulation(track_rows),
        "active_mean_signed_circulation": _signed_circulation(active_rows),
    }


def summarize_interface_topology_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "num_samples": len(trace),
        "track_names": TRACK_NAMES,
        "family_names": FAMILY_NAMES,
        "tracks": {track_name: _summarize_track(trace, track_name) for track_name in TRACK_NAMES},
    }
