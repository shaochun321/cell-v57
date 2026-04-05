from __future__ import annotations

from typing import Any
import numpy as np

TRACK_NAMES = [
    "discrete_channel_track",
    "local_propagation_track",
    "layered_coupling_track",
]

FAMILY_NAMES = [
    "structural_tonic_family",
    "dynamic_phasic_family",
    "axial_polar_family",
    "swirl_circulation_family",
]

FAMILY_CHANNELS: dict[str, list[str]] = {
    "structural_tonic_family": ["deformation_drive", "dissipation_load", "transfer_potential"],
    "dynamic_phasic_family": ["vibration_drive", "event_flux"],
    "axial_polar_family": ["axial_flux", "polarity_projection"],
    "swirl_circulation_family": ["swirl_flux", "circulation_projection"],
}

FAMILY_WEIGHTS: dict[str, dict[str, float]] = {
    "structural_tonic_family": {
        "deformation_drive": 0.42,
        "dissipation_load": 0.33,
        "transfer_potential": 0.25,
    },
    "dynamic_phasic_family": {
        "vibration_drive": 0.62,
        "event_flux": 0.38,
    },
    "axial_polar_family": {
        "axial_flux": 0.62,
        "polarity_projection": 0.38,
    },
    "swirl_circulation_family": {
        "swirl_flux": 0.62,
        "circulation_projection": 0.38,
    },
}

SIGNED_FAMILY_KEYS = {
    "axial_polar_family": "signed_polarity",
    "swirl_circulation_family": "signed_circulation",
}


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _clip_signed(value: float) -> float:
    return float(np.clip(value, -1.0, 1.0))


def _family_level(channels: dict[str, float], family_name: str) -> float:
    weights = FAMILY_WEIGHTS[family_name]
    total = 0.0
    for channel_name, weight in weights.items():
        value = float(channels.get(channel_name, 0.0))
        if channel_name in {"polarity_projection", "circulation_projection"}:
            value = abs(value)
        total += weight * value
    return _clip01(total)


def _signed_family_value(channels: dict[str, float], family_name: str) -> float:
    if family_name == "axial_polar_family":
        return _clip_signed(float(channels.get("polarity_projection", 0.0)))
    if family_name == "swirl_circulation_family":
        return _clip_signed(float(channels.get("circulation_projection", 0.0)))
    return 0.0


def _lineage_bundle(bundle: dict[str, Any], track_name: str) -> dict[str, Any]:
    channels = dict(bundle.get("channels", {}))
    family_response = {name: _family_level(channels, name) for name in FAMILY_NAMES}
    signed_family_response = {
        "signed_polarity": _signed_family_value(channels, "axial_polar_family"),
        "signed_circulation": _signed_family_value(channels, "swirl_circulation_family"),
    }
    tonic = family_response["structural_tonic_family"]
    phasic = family_response["dynamic_phasic_family"]
    bandwidth_proxy = _clip01(phasic / max(tonic + 1e-6, 1e-6))
    return {
        "lineage_id": str(bundle.get("bundle_id")),
        "parent_track": track_name,
        "shell_index": int(bundle.get("shell_index", 0)),
        "shell_name": str(bundle.get("shell_name", "")),
        "sector": str(bundle.get("sector", "")),
        "centroid_direction": bundle.get("centroid_direction", [0.0, 0.0, 0.0]),
        "coupling_weight": float(bundle.get("coupling_weight", 0.0)),
        "family_response": family_response,
        "signed_family_response": signed_family_response,
        "bandwidth_proxy": bandwidth_proxy,
        "channels": channels,
        "local_observables": bundle.get("local_observables", {}),
        "propagation_constraints": bundle.get("propagation_constraints", {}),
    }


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _family_summary(lineage_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    family_means = {
        name: _mean([float(bundle["family_response"].get(name, 0.0)) for bundle in lineage_bundles])
        for name in FAMILY_NAMES
    }
    family_std = {
        name: float(np.std([float(bundle["family_response"].get(name, 0.0)) for bundle in lineage_bundles])) if lineage_bundles else 0.0
        for name in FAMILY_NAMES
    }
    signed = {
        "signed_polarity": _mean([float(bundle["signed_family_response"].get("signed_polarity", 0.0)) for bundle in lineage_bundles]),
        "signed_circulation": _mean([float(bundle["signed_family_response"].get("signed_circulation", 0.0)) for bundle in lineage_bundles]),
    }
    return {
        "family_means": family_means,
        "family_std": family_std,
        "signed_family_means": signed,
        "mean_bandwidth_proxy": _mean([float(bundle.get("bandwidth_proxy", 0.0)) for bundle in lineage_bundles]),
    }


def _shell_spectra(lineage_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shells = sorted({int(bundle.get("shell_index", 0)) for bundle in lineage_bundles})
    out: list[dict[str, Any]] = []
    for shell_index in shells:
        shell_bundles = [bundle for bundle in lineage_bundles if int(bundle.get("shell_index", 0)) == shell_index]
        out.append({
            "shell_index": shell_index,
            "bundle_count": int(len(shell_bundles)),
            "summary": _family_summary(shell_bundles),
        })
    return out


def _sector_spectra(lineage_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sectors = sorted({str(bundle.get("sector", "")) for bundle in lineage_bundles})
    out: list[dict[str, Any]] = []
    for sector in sectors:
        sector_bundles = [bundle for bundle in lineage_bundles if str(bundle.get("sector", "")) == sector]
        out.append({
            "sector": sector,
            "bundle_count": int(len(sector_bundles)),
            "summary": _family_summary(sector_bundles),
        })
    return out


def _family_axis_balance_from_sector_spectra(sector_spectra: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_sector = {str(item.get("sector", "")): item for item in sector_spectra}
    out: dict[str, dict[str, float]] = {name: {"x": 0.0, "y": 0.0, "z": 0.0} for name in FAMILY_NAMES}
    for family_name in FAMILY_NAMES:
        for axis in ("x", "y", "z"):
            pos = float(by_sector.get(f"{axis}_pos", {}).get("summary", {}).get("family_means", {}).get(family_name, 0.0))
            neg = float(by_sector.get(f"{axis}_neg", {}).get("summary", {}).get("family_means", {}).get(family_name, 0.0))
            out[family_name][axis] = float(pos - neg)
    return out


def _track_payload(track_name: str, track_payload: dict[str, Any]) -> dict[str, Any]:
    lineage_bundles = [_lineage_bundle(bundle, track_name) for bundle in track_payload.get("local_bundles", [])]
    shell_spectra = _shell_spectra(lineage_bundles)
    sector_spectra = _sector_spectra(lineage_bundles)
    return {
        "track_name": track_name,
        "track_mode": str(track_payload.get("track_mode", "")),
        "lineage_bundles": lineage_bundles,
        "family_summary": _family_summary(lineage_bundles),
        "shell_spectra": shell_spectra,
        "sector_spectra": sector_spectra,
        "family_axis_balance": _family_axis_balance_from_sector_spectra(sector_spectra),
        "source_spatial_metrics": track_payload.get("spatial_metrics", {}),
        "source_direction_vector": track_payload.get("direction_vector", [0.0, 0.0, 0.0]),
        "source_circulation_vector": track_payload.get("circulation_vector", [0.0, 0.0, 0.0]),
    }


def build_interface_lineage_trace(interface_network_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in interface_network_trace:
        tracks = row.get("tracks", {})
        rows.append({
            "time": float(row.get("time", 0.0)),
            "stimulus_mode": row.get("stimulus_mode"),
            "stimulus_active": bool(row.get("stimulus_active", False)),
            "transition_state": row.get("transition_state", "baseline"),
            "lineage_structure": {
                "principle": "channel-family lineage view of interface transduction; no semantic recognition embedded in the channels",
                "track_names": TRACK_NAMES,
                "family_names": FAMILY_NAMES,
                "family_channels": FAMILY_CHANNELS,
            },
            "tracks": {
                track_name: _track_payload(track_name, tracks.get(track_name, {}))
                for track_name in TRACK_NAMES
            },
        })
    return rows


def _summarize_track(trace: list[dict[str, Any]], track_name: str) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "active_num_samples": 0,
            "family_means": {name: 0.0 for name in FAMILY_NAMES},
            "active_family_means": {name: 0.0 for name in FAMILY_NAMES},
            "mean_bandwidth_proxy": 0.0,
            "active_mean_bandwidth_proxy": 0.0,
            "mean_signed_polarity": 0.0,
            "mean_signed_circulation": 0.0,
            "active_mean_signed_polarity": 0.0,
            "active_mean_signed_circulation": 0.0,
            "family_axis_balance": {name: {"x": 0.0, "y": 0.0, "z": 0.0} for name in FAMILY_NAMES},
            "active_family_axis_balance": {name: {"x": 0.0, "y": 0.0, "z": 0.0} for name in FAMILY_NAMES},
            "shell_spectra": [],
            "sector_spectra": [],
        }
    track_rows = [row["tracks"][track_name] for row in trace]
    active_track_rows = [row["tracks"][track_name] for row in trace if bool(row.get("stimulus_active", False))]

    def _family_means(rows: list[dict[str, Any]]) -> dict[str, float]:
        return {
            name: _mean([float(r.get("family_summary", {}).get("family_means", {}).get(name, 0.0)) for r in rows])
            for name in FAMILY_NAMES
        }

    def _signed_mean(rows: list[dict[str, Any]], key: str) -> float:
        return _mean([float(r.get("family_summary", {}).get("signed_family_means", {}).get(key, 0.0)) for r in rows])

    shell_index_set = sorted({int(s.get("shell_index", 0)) for r in track_rows for s in r.get("shell_spectra", [])})
    shell_spectra = []
    for shell_index in shell_index_set:
        shell_summaries = [s for r in track_rows for s in r.get("shell_spectra", []) if int(s.get("shell_index", 0)) == shell_index]
        shell_spectra.append({
            "shell_index": shell_index,
            "family_means": {
                name: _mean([float(s.get("summary", {}).get("family_means", {}).get(name, 0.0)) for s in shell_summaries])
                for name in FAMILY_NAMES
            },
            "mean_bandwidth_proxy": _mean([float(s.get("summary", {}).get("mean_bandwidth_proxy", 0.0)) for s in shell_summaries]),
        })
    sector_name_set = sorted({str(s.get("sector", "")) for r in track_rows for s in r.get("sector_spectra", [])})
    sector_spectra = []
    for sector_name in sector_name_set:
        sector_summaries = [s for r in track_rows for s in r.get("sector_spectra", []) if str(s.get("sector", "")) == sector_name]
        sector_spectra.append({
            "sector": sector_name,
            "family_means": {
                name: _mean([float(s.get("summary", {}).get("family_means", {}).get(name, 0.0)) for s in sector_summaries])
                for name in FAMILY_NAMES
            },
            "mean_bandwidth_proxy": _mean([float(s.get("summary", {}).get("mean_bandwidth_proxy", 0.0)) for s in sector_summaries]),
        })

    return {
        "num_samples": int(len(track_rows)),
        "active_num_samples": int(len(active_track_rows)),
        "family_means": _family_means(track_rows),
        "active_family_means": _family_means(active_track_rows),
        "mean_bandwidth_proxy": _mean([float(r.get("family_summary", {}).get("mean_bandwidth_proxy", 0.0)) for r in track_rows]),
        "active_mean_bandwidth_proxy": _mean([float(r.get("family_summary", {}).get("mean_bandwidth_proxy", 0.0)) for r in active_track_rows]),
        "mean_signed_polarity": _signed_mean(track_rows, "signed_polarity"),
        "mean_signed_circulation": _signed_mean(track_rows, "signed_circulation"),
        "active_mean_signed_polarity": _signed_mean(active_track_rows, "signed_polarity"),
        "active_mean_signed_circulation": _signed_mean(active_track_rows, "signed_circulation"),
        "family_axis_balance": _family_axis_balance_from_sector_spectra([s for r in track_rows for s in r.get("sector_spectra", [])]),
        "active_family_axis_balance": _family_axis_balance_from_sector_spectra([s for r in active_track_rows for s in r.get("sector_spectra", [])]),
        "shell_spectra": shell_spectra,
        "sector_spectra": sector_spectra,
        "mean_transfer_std": _mean([float(r.get("source_spatial_metrics", {}).get("transfer_std", 0.0)) for r in track_rows]),
    }


def summarize_interface_lineage_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    if not trace:
        return {
            "num_samples": 0,
            "track_names": TRACK_NAMES,
            "family_names": FAMILY_NAMES,
            "family_channels": FAMILY_CHANNELS,
            "tracks": {name: _summarize_track([], name) for name in TRACK_NAMES},
        }
    return {
        "num_samples": int(len(trace)),
        "track_names": TRACK_NAMES,
        "family_names": FAMILY_NAMES,
        "family_channels": FAMILY_CHANNELS,
        "tracks": {name: _summarize_track(trace, name) for name in TRACK_NAMES},
    }
