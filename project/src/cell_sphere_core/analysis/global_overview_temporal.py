
from __future__ import annotations

from pathlib import Path
from statistics import fmean
from typing import Any

from .global_overview import load_interface_trace, frame_overview


def summarize_temporal_overview_from_trace(interface_trace: list[dict[str, Any]]) -> dict[str, float]:
    frames = [frame_overview(fr) for fr in interface_trace]
    n = len(frames)
    thirds = [
        (0, max(1, n // 3)),
        (max(1, n // 3), max(2, 2 * n // 3)),
        (max(2, 2 * n // 3), n),
    ]

    out: dict[str, float] = {}
    keys = [
        'translation_dipole_x',
        'translation_dipole_norm',
        'rotation_energy',
        'event_energy',
        'translation_energy',
        'agg_translation',
        'agg_rotation',
        'agg_event',
        'polarity_dipole_x',
        'polarity_dipole_norm',
    ]

    for key in keys:
        vals = [f[key] for f in frames]
        absvals = [abs(v) for v in vals]
        peak_idx = max(range(n), key=lambda i: absvals[i])
        out[f'temporal_{key}_peak_abs'] = absvals[peak_idx]
        out[f'temporal_{key}_mean'] = fmean(vals)
        out[f'temporal_{key}_peak_time_frac'] = peak_idx / max(1, n - 1)

        names = ['early', 'mid', 'late']
        thirds_abs = []
        for nm, (a, b) in zip(names, thirds):
            seg = vals[a:b]
            segabs = [abs(v) for v in seg]
            out[f'temporal_{key}_{nm}_mean'] = fmean(seg)
            out[f'temporal_{key}_{nm}_peak_abs'] = max(segabs) if segabs else 0.0
            thirds_abs.append(out[f'temporal_{key}_{nm}_peak_abs'])

        eps = 1e-9
        out[f'temporal_{key}_early_to_late_peak_ratio'] = thirds_abs[0] / (thirds_abs[2] + eps)
        out[f'temporal_{key}_mid_to_late_peak_ratio'] = thirds_abs[1] / (thirds_abs[2] + eps)

    tnorm = [f['translation_dipole_norm'] for f in frames]
    tnorm_peak_idx = max(range(n), key=lambda i: abs(tnorm[i]))
    out['temporal_translation_x_at_translation_peak'] = frames[tnorm_peak_idx]['translation_dipole_x']
    out['temporal_polarity_x_at_translation_peak'] = frames[tnorm_peak_idx]['polarity_dipole_x']
    out['temporal_rotation_energy_at_translation_peak'] = frames[tnorm_peak_idx]['rotation_energy']
    out['temporal_event_energy_at_translation_peak'] = frames[tnorm_peak_idx]['event_energy']
    return out


def extract_temporal_overview_features(run_dir: Path) -> dict[str, float]:
    interface_trace = load_interface_trace(run_dir)
    return summarize_temporal_overview_from_trace(interface_trace)
