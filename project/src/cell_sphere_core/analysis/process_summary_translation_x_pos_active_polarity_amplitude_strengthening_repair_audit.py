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
        'active_raw_mean_polarity_projection': float(active_signature.get('raw_mean_polarity_projection', 0.0)),
        'active_support_weighted_mean_polarity_projection': float(active_signature.get('support_weighted_mean_polarity_projection', 0.0)),
        'active_direction_sign': float(active_signature.get('direction_sign', 0.0)),
        'strongest_pair_mode': str(strongest_pair.get('dominant_mode', 'none')),
        'strongest_pair_axis': str(strongest_pair.get('axis', 'none')),
        'strongest_pair_polarity_projection': float(strongest_pair.get('differential_channels', {}).get('polarity_projection', 0.0)),
        'strongest_pair_mode_scores': {
            'static_like': float(strongest_pair.get('mode_scores', {}).get('static_like', 0.0)),
            'translation_like': float(strongest_pair.get('mode_scores', {}).get('translation_like', 0.0)),
            'rotation_like': float(strongest_pair.get('mode_scores', {}).get('rotation_like', 0.0)),
        },
    }


def build_translation_x_pos_active_polarity_amplitude_strengthening_repair_audit(
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
        'seed7_translation_x_pos_positive_amplitude_preserved': txp7['active_mean_polarity_projection'] > 0.10,
        'seed7_translation_x_neg_negative_amplitude_preserved': txn7['active_mean_polarity_projection'] < -0.10,
        'seed8_translation_x_pos_active_amplitude_strengthened': txp8['active_mean_polarity_projection'] > 0.03,
        'seed8_translation_x_pos_strengthened_above_raw_mean': abs(txp8['active_mean_polarity_projection']) > abs(txp8['active_raw_mean_polarity_projection']),
        'seed8_translation_x_pos_weighted_support_remains_positive': txp8['active_support_weighted_mean_polarity_projection'] > 0.03,
        'seed8_translation_x_neg_sign_preserved': txn8['active_mean_polarity_projection'] < 0.0,
        'seed8_translation_x_pos_strongest_pair_mode_preserved': txp8['strongest_pair_mode'] == 'translation_like' and txp8['strongest_pair_axis'] == 'x',
        'seed8_translation_x_neg_strongest_pair_mode_preserved': txn8['strongest_pair_mode'] == 'translation_like' and txn8['strongest_pair_axis'] == 'x',
        'seed8_translation_x_pos_active_mode_axis_preserved': txp8['active_dominant_mode'] == 'translation_like' and txp8['active_dominant_axis'] == 'x',
        'seed8_translation_x_neg_active_mode_axis_preserved': txn8['active_dominant_mode'] == 'translation_like' and txn8['active_dominant_axis'] == 'x',
        'seed8_rotation_z_pos_guardrail_preserved': rzp8['active_dominant_mode'] == 'rotation_like' and rzp8['active_dominant_axis'] == 'z',
    }
    contracts_passed = all(evidence.values())

    seed8_gap_to_seed7 = float(txp7['active_mean_polarity_projection'] - txp8['active_mean_polarity_projection'])
    residual_issue = 'seed8_translation_x_pos_amplitude_gap_to_seed7_remains' if seed8_gap_to_seed7 > 0.10 else 'none'

    return {
        'suite': 'translation_x_pos_active_polarity_amplitude_strengthening_repair_audit_r1',
        'contracts': {'passed': contracts_passed},
        'repeatability_failures': repeatability.get('contracts', {}).get('failures', []),
        'seed7': seed7,
        'seed8': seed8,
        'evidence': evidence,
        'inferred_outcome': 'translation_x_pos_active_polarity_amplitude_strengthening_repair_success' if contracts_passed else 'undetermined',
        'residual_issue': residual_issue,
        'interpretation': {
            'primary_effect': 'strengthen shallow seed8 translation_x_pos active polarity amplitude by summarizing active x-pair polarity with translation-support weighting instead of raw dilution by weak static pairs',
            'guardrail': 'preserve strongest-pair translation mode, x-axis identity, polarity sign, and rotation_z_pos active z classification',
            'next_branch': 'optional only if future rounds still require seed8 x-pos amplitude to approach seed7 more closely',
        },
        'seed8_translation_x_pos_gap_to_seed7': seed8_gap_to_seed7,
    }
