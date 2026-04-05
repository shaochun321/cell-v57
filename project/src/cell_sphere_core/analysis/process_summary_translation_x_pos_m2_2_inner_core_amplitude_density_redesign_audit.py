from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _phase_x_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json['phase_summaries']['active']['axis_summaries']['x'])


def _phase_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json['phase_summaries']['active'])


def _active_x_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for window_index, window in enumerate(atlas_trace):
        if str(window.get('phase', 'baseline')) != 'active':
            continue
        rows = []
        for pair in sorted([item for item in window.get('pair_summaries', []) if str(item.get('axis', 'none')) == 'x'], key=lambda item: int(item.get('shell_index', -1))):
            rows.append({
                'shell_index': int(pair.get('shell_index', -1)),
                'dominant_mode': str(pair.get('dominant_mode', 'none')),
                'direction_sign': float(pair.get('direction_sign', 0.0)),
                'pair_strength': float(pair.get('pair_strength', 0.0)),
                'handoff_gate_score': float(pair.get('handoff_gate_score', 0.0)),
                'translation_like': float(pair.get('mode_scores', {}).get('translation_like', 0.0)),
                'static_like': float(pair.get('mode_scores', {}).get('static_like', 0.0)),
                'polarity_projection': float(pair.get('pair_differential_mode', {}).get('polarity_projection', 0.0)),
            })
        out.append({
            'window_index': int(window_index),
            'atlas_dominant_mode': str(window.get('atlas_dominant_mode', 'none')),
            'atlas_dominant_axis': str(window.get('atlas_dominant_axis', 'none')),
            'pair_rows': rows,
        })
    return out


def _shell0_positive_translation_both_windows(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    for window in rows[:2]:
        shell0 = next((r for r in window['pair_rows'] if int(r['shell_index']) == 0), None)
        if not shell0:
            return False
        if not (shell0['dominant_mode'] == 'translation_like' and shell0['direction_sign'] > 0.0):
            return False
    return True


def build_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit(
    *,
    round52_seed8_summary_path: str | Path,
    round57_seed8_summary_path: str | Path,
    round57_seed8_atlas_trace_path: str | Path,
    round58_seed8_summary_path: str | Path,
    round58_seed8_atlas_trace_path: str | Path,
    round58_seed8_xneg_summary_path: str | Path,
    round58_seed8_rotation_pos_summary_path: str | Path,
    round58_seed8_rotation_neg_summary_path: str | Path,
    repeatability_audit_path: str | Path,
) -> dict[str, Any]:
    round52 = _load_json(round52_seed8_summary_path)
    round57 = _load_json(round57_seed8_summary_path)
    round58 = _load_json(round58_seed8_summary_path)
    round57_rows = _active_x_rows(_load_json(round57_seed8_atlas_trace_path))
    round58_rows = _active_x_rows(_load_json(round58_seed8_atlas_trace_path))
    xneg = _load_json(round58_seed8_xneg_summary_path)
    rot_pos = _load_json(round58_seed8_rotation_pos_summary_path)
    rot_neg = _load_json(round58_seed8_rotation_neg_summary_path)
    repeatability = _load_json(repeatability_audit_path)

    r52x = _phase_x_summary(round52)
    r57x = _phase_x_summary(round57)
    r58x = _phase_x_summary(round58)
    xneg_active = _phase_x_summary(xneg)
    rot_pos_active = _phase_summary(rot_pos)
    rot_neg_active = _phase_summary(rot_neg)

    evidence = {
        'round58_seed8_shell0_translation_present_in_both_active_windows': _shell0_positive_translation_both_windows(round58_rows),
        'round58_seed8_final_mean_exceeds_round57': float(r58x.get('mean_polarity_projection', 0.0)) > float(r57x.get('mean_polarity_projection', 0.0)),
        'round58_seed8_raw_mean_exceeds_round57': float(r58x.get('raw_mean_polarity_projection', 0.0)) > float(r57x.get('raw_mean_polarity_projection', 0.0)),
        'round58_seed8_translation_x_pos_active_mode_axis_preserved': str(round58['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(round58['phase_summaries']['active']['dominant_axis']) == 'x',
        'round58_seed8_translation_x_neg_sign_preserved': str(xneg['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(xneg['phase_summaries']['active']['dominant_axis']) == 'x' and float(xneg_active.get('direction_sign', 0.0)) < 0.0,
        'round58_seed8_rotation_z_pos_guardrail_preserved': str(rot_pos_active.get('dominant_mode', 'none')) == 'rotation_like' and str(rot_pos_active.get('dominant_axis', 'none')) == 'z',
        'round58_seed8_rotation_z_neg_guardrail_preserved': str(rot_neg_active.get('dominant_mode', 'none')) == 'rotation_like' and str(rot_neg_active.get('dominant_axis', 'none')) == 'z',
        'round58_seed8_final_mean_still_below_round52_frozen_baseline': float(r58x.get('mean_polarity_projection', 0.0)) < float(r52x.get('mean_polarity_projection', 0.0)),
    }
    contracts_passed = all(v for k, v in evidence.items() if k != 'round58_seed8_final_mean_still_below_round52_frozen_baseline')
    delta_to_round57 = float(r58x.get('mean_polarity_projection', 0.0)) - float(r57x.get('mean_polarity_projection', 0.0))
    gap_to_round52 = float(r52x.get('mean_polarity_projection', 0.0)) - float(r58x.get('mean_polarity_projection', 0.0))

    return {
        'suite': 'translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit_r1',
        'contracts': {'passed': contracts_passed},
        'evidence': evidence,
        'repeatability_failures': list(repeatability.get('contracts', {}).get('failures', []) or repeatability.get('failures', []) or []),
        'seed8_round52_frozen_reference': {'phase_active_x_summary': r52x},
        'seed8_round57_m2_continuity': {'phase_active_x_summary': r57x, 'active_x_pair_rows': round57_rows},
        'seed8_round58_m2_2_density': {'phase_active_x_summary': r58x, 'active_x_pair_rows': round58_rows},
        'guardrails': {
            'seed8_translation_x_neg_active_x_summary': xneg_active,
            'seed8_rotation_z_pos_active_summary': rot_pos_active,
            'seed8_rotation_z_neg_active_summary': rot_neg_active,
        },
        'deltas': {
            'round58_minus_round57_final_mean': float(delta_to_round57),
            'round52_minus_round58_gap': float(gap_to_round52),
        },
        'decision': 'continue_inner_core_material_redesign' if contracts_passed else 'undetermined',
        'headline': 'shell0 inner-core amplitude density strengthened; guardrails preserved; final mean still below frozen round52 baseline',
        'residual_issue': 'joint shell0/shell1 high-amplitude density still insufficient to match frozen round52 summary level',
    }
