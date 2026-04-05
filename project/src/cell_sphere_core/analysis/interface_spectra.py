from __future__ import annotations

from typing import Any
import numpy as np

from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES, FAMILY_NAMES


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _spectral_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    family_response = dict(bundle.get("family_response", {}))
    dominant_family = max(FAMILY_NAMES, key=lambda n: float(family_response.get(n, 0.0))) if family_response else "none"
    dominant_level = float(family_response.get(dominant_family, 0.0)) if family_response else 0.0
    channels = dict(bundle.get("channels", {}))
    transfer_level = float(channels.get("transfer_potential", 0.0))
    return {
        "bundle_id": str(bundle.get("lineage_id", "")),
        "shell_index": int(bundle.get("shell_index", 0)),
        "sector": str(bundle.get("sector", "")),
        "family_vector": {name: float(family_response.get(name, 0.0)) for name in FAMILY_NAMES},
        "dominant_family": dominant_family,
        "dominant_level": dominant_level,
        "signed_polarity": float(bundle.get("signed_family_response", {}).get("signed_polarity", 0.0)),
        "signed_circulation": float(bundle.get("signed_family_response", {}).get("signed_circulation", 0.0)),
        "bandwidth_proxy": float(bundle.get("bandwidth_proxy", 0.0)),
        "transfer_level": transfer_level,
    }


def _family_clusters(spectral_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    family_means = {name: _mean([float(b.get("family_vector", {}).get(name, 0.0)) for b in spectral_bundles]) for name in FAMILY_NAMES}
    family_std = {name: _std([float(b.get("family_vector", {}).get(name, 0.0)) for b in spectral_bundles]) for name in FAMILY_NAMES}
    dominant_counts = {name: 0 for name in FAMILY_NAMES}
    for bundle in spectral_bundles:
        dom = str(bundle.get("dominant_family", "none"))
        if dom in dominant_counts:
            dominant_counts[dom] += 1
    return {
        "family_means": family_means,
        "family_std": family_std,
        "dominant_family_counts": dominant_counts,
        "mean_bandwidth_proxy": _mean([float(b.get("bandwidth_proxy", 0.0)) for b in spectral_bundles]),
        "mean_transfer_level": _mean([float(b.get("transfer_level", 0.0)) for b in spectral_bundles]),
        "transfer_variability": _std([float(b.get("transfer_level", 0.0)) for b in spectral_bundles]),
        "signed_family_means": {
            "signed_polarity": _mean([float(b.get("signed_polarity", 0.0)) for b in spectral_bundles]),
            "signed_circulation": _mean([float(b.get("signed_circulation", 0.0)) for b in spectral_bundles]),
        },
    }


def _shell_summary(shell_bundles: list[dict[str, Any]], shell_index: int) -> dict[str, Any]:
    return {
        "shell_index": shell_index,
        "bundle_count": len(shell_bundles),
        "family_means": {name: _mean([float(b.get("family_vector", {}).get(name, 0.0)) for b in shell_bundles]) for name in FAMILY_NAMES},
        "mean_transfer_level": _mean([float(b.get("transfer_level", 0.0)) for b in shell_bundles]),
        "mean_bandwidth_proxy": _mean([float(b.get("bandwidth_proxy", 0.0)) for b in shell_bundles]),
    }


def _transmission_spectra(spectral_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    shells = sorted({int(b.get("shell_index", 0)) for b in spectral_bundles})
    shell_profiles = []
    for shell_index in shells:
        shell_bundles = [b for b in spectral_bundles if int(b.get("shell_index", 0)) == shell_index]
        shell_profiles.append(_shell_summary(shell_bundles, shell_index))
    inter_shell = []
    for prev, curr in zip(shell_profiles, shell_profiles[1:]):
        inter_shell.append({
            "from_shell": int(prev["shell_index"]),
            "to_shell": int(curr["shell_index"]),
            "family_delta": {
                name: float(curr["family_means"].get(name, 0.0) - prev["family_means"].get(name, 0.0))
                for name in FAMILY_NAMES
            },
            "transfer_delta": float(curr.get("mean_transfer_level", 0.0) - prev.get("mean_transfer_level", 0.0)),
            "bandwidth_delta": float(curr.get("mean_bandwidth_proxy", 0.0) - prev.get("mean_bandwidth_proxy", 0.0)),
        })
    return {
        "shell_profiles": shell_profiles,
        "inter_shell_transfers": inter_shell,
    }


def _axis_balance(spectral_bundles: list[dict[str, Any]], family_name: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        pos = [float(b.get("family_vector", {}).get(family_name, 0.0)) for b in spectral_bundles if str(b.get("sector", "")) == f"{axis}_pos"]
        neg = [float(b.get("family_vector", {}).get(family_name, 0.0)) for b in spectral_bundles if str(b.get("sector", "")) == f"{axis}_neg"]
        out[axis] = _mean(pos) - _mean(neg)
    return out


def _track_payload(track_name: str, track_payload: dict[str, Any]) -> dict[str, Any]:
    lineage_bundles = track_payload.get("lineage_bundles", [])
    spectral_bundles = [_spectral_bundle(bundle) for bundle in lineage_bundles]
    family_clusters = _family_clusters(spectral_bundles)
    transmission_spectra = _transmission_spectra(spectral_bundles)
    return {
        "track_name": track_name,
        "track_mode": str(track_payload.get("track_mode", "")),
        "spectral_bundles": spectral_bundles,
        "family_clusters": family_clusters,
        "transmission_spectra": transmission_spectra,
        "axis_balance": {
            name: _axis_balance(spectral_bundles, name)
            for name in ("axial_polar_family", "swirl_circulation_family")
        },
        "source_direction_vector": track_payload.get("source_direction_vector", [0.0, 0.0, 0.0]),
        "source_circulation_vector": track_payload.get("source_circulation_vector", [0.0, 0.0, 0.0]),
    }


def build_interface_spectrum_trace(interface_lineage_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in interface_lineage_trace:
        tracks = row.get("tracks", {})
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "spectrum_structure": {
                "principle": "bundle-family plus inter-shell transmission spectrum; no semantic recognition embedded in the channels",
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
            },
            "tracks": {track_name: _track_payload(track_name, tracks.get(track_name, {})) for track_name in TRACK_NAMES},
        })
    return rows


def _summarize_track(rows: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    track_rows = [r.get("tracks", {}).get(track_name, {}) for r in rows]
    active_track_rows = [r.get("tracks", {}).get(track_name, {}) for r in rows if bool(r.get("stimulus_active", False))]

    def _family_means(track_payloads: list[dict[str, Any]]) -> dict[str, float]:
        return {
            name: _mean([float(p.get("family_clusters", {}).get("family_means", {}).get(name, 0.0)) for p in track_payloads])
            for name in FAMILY_NAMES
        }

    def _axis(active_payloads: list[dict[str, Any]], family_name: str) -> dict[str, float]:
        return {
            axis: _mean([float(p.get("axis_balance", {}).get(family_name, {}).get(axis, 0.0)) for p in active_payloads])
            for axis in ("x", "y", "z")
        }

    def _signed(payloads: list[dict[str, Any]], key: str) -> float:
        return _mean([float(p.get("family_clusters", {}).get("signed_family_means", {}).get(key, 0.0)) for p in payloads])

    def _transfer_var(payloads: list[dict[str, Any]]) -> float:
        return _mean([float(p.get("family_clusters", {}).get("transfer_variability", 0.0)) for p in payloads])

    def _inter_shell_drop(payloads: list[dict[str, Any]], family_name: str) -> float:
        vals = []
        for p in payloads:
            for item in p.get("transmission_spectra", {}).get("inter_shell_transfers", []):
                vals.append(abs(float(item.get("family_delta", {}).get(family_name, 0.0))))
        return _mean(vals)

    return {
        "num_samples": len(track_rows),
        "active_num_samples": len(active_track_rows),
        "family_cluster_means": _family_means(track_rows),
        "active_family_cluster_means": _family_means(active_track_rows),
        "mean_bandwidth_proxy": _mean([float(p.get("family_clusters", {}).get("mean_bandwidth_proxy", 0.0)) for p in track_rows]),
        "active_mean_bandwidth_proxy": _mean([float(p.get("family_clusters", {}).get("mean_bandwidth_proxy", 0.0)) for p in active_track_rows]),
        "mean_signed_polarity": _signed(track_rows, "signed_polarity"),
        "mean_signed_circulation": _signed(track_rows, "signed_circulation"),
        "active_mean_signed_polarity": _signed(active_track_rows, "signed_polarity"),
        "active_mean_signed_circulation": _signed(active_track_rows, "signed_circulation"),
        "axis_balance": {
            "axial_polar_family": _axis(track_rows, "axial_polar_family"),
            "swirl_circulation_family": _axis(track_rows, "swirl_circulation_family"),
        },
        "active_axis_balance": {
            "axial_polar_family": _axis(active_track_rows, "axial_polar_family"),
            "swirl_circulation_family": _axis(active_track_rows, "swirl_circulation_family"),
        },
        "mean_transfer_variability": _transfer_var(track_rows),
        "active_mean_transfer_variability": _transfer_var(active_track_rows),
        "mean_axial_inter_shell_delta": _inter_shell_drop(track_rows, "axial_polar_family"),
        "mean_swirl_inter_shell_delta": _inter_shell_drop(track_rows, "swirl_circulation_family"),
    }


def summarize_interface_spectrum_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "track_names": TRACK_NAMES,
            "family_names": FAMILY_NAMES,
            "tracks": {name: _summarize_track([], name) for name in TRACK_NAMES},
        }
    return {
        "num_samples": len(trace),
        "track_names": TRACK_NAMES,
        "family_names": FAMILY_NAMES,
        "tracks": {name: _summarize_track(trace, name) for name in TRACK_NAMES},
    }
