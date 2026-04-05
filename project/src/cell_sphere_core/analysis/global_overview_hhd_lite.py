from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _norm(v: list[float]) -> float:
    return sum(x * x for x in v) ** 0.5


def load_interface_trace(run_dir: Path) -> list[dict[str, Any]]:
    return json.loads((run_dir / 'interface_trace.json').read_text())


def frame_hhd_lite(frame: dict[str, Any]) -> dict[str, float]:
    """Construct a physically interpretable HHD-lite proxy from interface bundles.

    This is not a full Helmholtz-Hodge decomposition on a continuous mesh.
    It is a low-cost overview proxy that separates three global channels:
    - divergence-like / translation-like response
    - curl-like / rotation-like response
    - harmonic / polarity-gated residual response

    The goal is to test whether a field-decomposition-style overview stabilizes
    cross-scale readout better than local rescue logic.
    """
    div_vec = [0.0, 0.0, 0.0]
    curl_vec = [0.0, 0.0, 0.0]
    harm_vec = [0.0, 0.0, 0.0]
    div_energy = 0.0
    curl_energy = 0.0
    harm_energy = 0.0
    resid_energy = 0.0

    for bundle in frame['interface_bundles']:
        w = float(bundle.get('coupling_weight', 1.0))
        u = [float(x) for x in bundle['centroid_direction']]
        ch = bundle['channels']
        lo = bundle.get('local_observables', {})

        abs_radial_speed = float(lo.get('abs_radial_speed', 0.0))
        tangential_speed = float(lo.get('tangential_speed', 0.0))
        gate = float(lo.get('gate', 1.0))

        translation = w * float(ch.get('translation_signal', 0.0))
        rotation = w * float(ch.get('rotation_signal', 0.0))
        polarity = w * float(ch.get('polarity_signal', 0.0))
        fast_event = w * float(ch.get('fast_event', ch.get('burst_signal', 0.0)))

        div_like = translation * (1.0 + 0.1 * abs_radial_speed)
        curl_like = rotation * (1.0 + 0.1 * tangential_speed)
        harm_like = polarity * gate

        for i in range(3):
            div_vec[i] += u[i] * div_like
            curl_vec[i] += u[i] * curl_like
            harm_vec[i] += u[i] * harm_like

        div_energy += abs(div_like)
        curl_energy += abs(curl_like)
        harm_energy += abs(harm_like)
        resid_energy += abs(fast_event)

    eps = 1e-9
    return {
        'hhd_div_x': div_vec[0],
        'hhd_div_y': div_vec[1],
        'hhd_div_z': div_vec[2],
        'hhd_div_norm': _norm(div_vec),
        'hhd_div_energy': div_energy,
        'hhd_curl_x': curl_vec[0],
        'hhd_curl_y': curl_vec[1],
        'hhd_curl_z': curl_vec[2],
        'hhd_curl_norm': _norm(curl_vec),
        'hhd_curl_energy': curl_energy,
        'hhd_harm_x': harm_vec[0],
        'hhd_harm_y': harm_vec[1],
        'hhd_harm_z': harm_vec[2],
        'hhd_harm_norm': _norm(harm_vec),
        'hhd_harm_energy': harm_energy,
        'hhd_div_to_curl': div_energy / (curl_energy + eps),
        'hhd_div_to_resid': div_energy / (resid_energy + eps),
        'hhd_curl_to_resid': curl_energy / (resid_energy + eps),
    }


def summarize_hhd_lite_from_trace(interface_trace: list[dict[str, Any]]) -> dict[str, float]:
    frames = [frame_hhd_lite(fr) for fr in interface_trace]
    out: dict[str, float] = {}
    for key in frames[0].keys():
        vals = [f[key] for f in frames]
        out[f'{key}_mean'] = mean(vals)
        peak = max(vals, key=lambda x: abs(x))
        out[f'{key}_peak'] = peak
        out[f'{key}_peak_abs'] = max(abs(x) for x in vals)
    return out


def extract_hhd_lite_features(run_dir: Path) -> dict[str, float]:
    return summarize_hhd_lite_from_trace(load_interface_trace(run_dir))
