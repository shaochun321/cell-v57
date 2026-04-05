from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _summary_row(summary_analysis: dict[str, Any], case_name: str) -> dict[str, Any]:
    case = dict(summary_analysis['cases'][case_name])
    active_signature = dict(case.get('active_signature', {}))
    strongest_pair = dict(active_signature.get('strongest_pair', {}))
    return {
        'active_dominant_mode': str(case.get('active_dominant_mode', 'none')),
        'active_dominant_axis': str(case.get('active_dominant_axis', 'none')),
        'active_mean_polarity_projection': float(active_signature.get('mean_polarity_projection', 0.0)),
        'active_direction_sign': float(active_signature.get('direction_sign', 0.0)),
        'strongest_pair_mode': str(strongest_pair.get('dominant_mode', 'none')),
        'strongest_pair_axis': str(strongest_pair.get('axis', 'none')),
        'strongest_pair_polarity_projection': float(strongest_pair.get('differential_channels', {}).get('polarity_projection', 0.0)),
        'strongest_pair_circulation_projection': float(strongest_pair.get('differential_channels', {}).get('circulation_projection', 0.0)),
        'strongest_pair_mode_scores': {
            'static_like': float(strongest_pair.get('mode_scores', {}).get('static_like', 0.0)),
            'translation_like': float(strongest_pair.get('mode_scores', {}).get('translation_like', 0.0)),
            'rotation_like': float(strongest_pair.get('mode_scores', {}).get('rotation_like', 0.0)),
        },
    }


def build_translation_x_family_strongest_pair_translation_mode_restoration_repair_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_summary_analysis_path: str | Path,
    seed8_summary_analysis_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary_analysis = _load_json(seed7_summary_analysis_path)
    seed8_summary_analysis = _load_json(seed8_summary_analysis_path)

    seed7 = {
        'translation_x_pos': _summary_row(seed7_summary_analysis, 'translation_x_pos'),
        'translation_x_neg': _summary_row(seed7_summary_analysis, 'translation_x_neg'),
    }
    seed8 = {
        'translation_x_pos': _summary_row(seed8_summary_analysis, 'translation_x_pos'),
        'translation_x_neg': _summary_row(seed8_summary_analysis, 'translation_x_neg'),
        'rotation_z_pos': _summary_row(seed8_summary_analysis, 'rotation_z_pos'),
    }

    txp7 = seed7['translation_x_pos']
    txn7 = seed7['translation_x_neg']
    txp8 = seed8['translation_x_pos']
    txn8 = seed8['translation_x_neg']
    rzp8 = seed8['rotation_z_pos']

    evidence = {
        'seed7_translation_x_pos_pair_mode_preserved': txp7['strongest_pair_mode'] == 'translation_like' and txp7['strongest_pair_axis'] == 'x',
        'seed7_translation_x_neg_pair_mode_preserved': txn7['strongest_pair_mode'] == 'translation_like' and txn7['strongest_pair_axis'] == 'x',
        'seed8_translation_x_pos_pair_mode_restored': txp8['strongest_pair_mode'] == 'translation_like' and txp8['strongest_pair_axis'] == 'x',
        'seed8_translation_x_neg_pair_mode_restored': txn8['strongest_pair_mode'] == 'translation_like' and txn8['strongest_pair_axis'] == 'x',
        'seed8_translation_x_pos_sign_preserved': txp8['strongest_pair_polarity_projection'] > 0.0,
        'seed8_translation_x_neg_sign_preserved': txn8['strongest_pair_polarity_projection'] < 0.0,
        'seed8_translation_x_pos_active_mode_axis_preserved': txp8['active_dominant_mode'] == 'translation_like' and txp8['active_dominant_axis'] == 'x',
        'seed8_translation_x_neg_active_mode_axis_preserved': txn8['active_dominant_mode'] == 'translation_like' and txn8['active_dominant_axis'] == 'x',
        'seed8_rotation_z_pos_guardrail_preserved': rzp8['active_dominant_mode'] == 'rotation_like' and rzp8['active_dominant_axis'] == 'z',
    }

    contracts_passed = all(evidence.values())

    residual_issue = 'translation_x_pos_active_polarity_amplitude_still_shallow' if 0.0 < abs(txp8['active_mean_polarity_projection']) < 0.03 else 'none'

    return {
        'suite': 'translation_x_family_strongest_pair_translation_mode_restoration_repair_audit_r1',
        'contracts': {'passed': contracts_passed},
        'repeatability_failures': repeatability.get('contracts', {}).get('failures', []),
        'seed7': seed7,
        'seed8': seed8,
        'evidence': evidence,
        'inferred_outcome': 'translation_x_family_strongest_pair_translation_mode_restoration_repair_success' if contracts_passed else 'undetermined',
        'residual_issue': residual_issue,
        'interpretation': {
            'primary_effect': 'restore strongest translation x-family pair mode without losing recovered x-axis or polarity sign',
            'guardrail': 'preserve rotation_z_pos active z classification',
            'next_branch': 'strengthen translation_x_pos active polarity amplitude only if future rounds still need more x-family margin',
        },
    }
