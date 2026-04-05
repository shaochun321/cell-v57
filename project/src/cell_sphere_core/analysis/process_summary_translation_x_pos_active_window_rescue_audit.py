from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _x_pos_case(analysis: dict[str, Any]) -> dict[str, Any]:
    return analysis['cases']['translation_x_pos']


def build_translation_x_pos_active_window_rescue_audit(*, repeatability_audit_path: str | Path, seed7_analysis_path: str | Path, seed8_analysis_path: str | Path) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7 = _load_json(seed7_analysis_path)
    seed8 = _load_json(seed8_analysis_path)

    row7 = _x_pos_case(seed7)
    row8 = _x_pos_case(seed8)
    act7 = row7['phase_summaries']['active']
    act8 = row8['phase_summaries']['active']
    sig7 = row7['active_signature']
    sig8 = row8['active_signature']
    strongest7 = sig7['strongest_pair']
    strongest8 = sig8['strongest_pair']

    evidence = {
        'seed7_translation_like_x_reference_is_clean': bool(
            row7['active_dominant_mode'] == 'translation_like'
            and row7['active_dominant_axis'] == 'x'
            and sig7['upstream_axis_match_fraction'] == 1.0
            and strongest7['dominant_mode'] == 'translation_like'
            and strongest7['dominant_axis'] == 'x'
        ),
        'seed8_active_mode_still_translation_like': bool(row8['active_dominant_mode'] == 'translation_like'),
        'seed8_active_axis_is_y_not_x': bool(row8['active_dominant_axis'] == 'y'),
        'seed8_gate_still_passes_pairs': bool(sig8['pair_gate_pass_fraction'] > 0.0 and strongest8['pair_gate_passed']),
        'seed8_upstream_axis_match_collapses_to_zero': bool(sig8['upstream_axis_match_fraction'] == 0.0),
        'seed8_strongest_pair_arrives_as_static_like_none': bool(
            strongest8['dominant_mode'] == 'static_like' and strongest8['dominant_axis'] == 'none'
            and strongest8['upstream_dominant_mode'] == 'static_like' and strongest8['upstream_dominant_axis'] == 'none'
        ),
        'seed8_failure_occurs_before_handoff_gate_can_rescue': bool(
            strongest8['pair_gate_passed']
            and strongest8['handoff_gate_score'] > 0.20
            and strongest8['upstream_dominant_mode'] == 'static_like'
        ),
    }

    if all(evidence.values()):
        inferred_primary_source = 'translation_x_pos_active_window_upstream_static_collapse_before_handoff_gate'
        secondary = [
            'shared_outer_shift_reaches_shell_3_before_axis_rescue',
            'gate_weighted_selection_cannot_recover_x_if_upstream_axis_match_fraction_is_zero',
            'y_axis_wins_because_active_x_candidate_arrives_pre-collapsed',
        ]
    else:
        inferred_primary_source = 'undetermined'
        secondary = []

    return {
        'suite': 'translation_x_pos_active_window_rescue_audit_r1',
        'contracts': {'passed': inferred_primary_source != 'undetermined'},
        'baseline_repeatability_failures': repeatability.get('failures', []),
        'seed7': {
            'overall_mode': row7['dominant_mode'],
            'overall_axis': row7['dominant_axis'],
            'active_mode': row7['active_dominant_mode'],
            'active_axis': row7['active_dominant_axis'],
            'active_signal_sign': sig7['direction_sign'],
            'upstream_axis_match_fraction': sig7['upstream_axis_match_fraction'],
            'strongest_pair_mode': strongest7['dominant_mode'],
            'strongest_pair_axis': strongest7['axis'],
            'strongest_pair_upstream_mode': strongest7['upstream_dominant_mode'],
            'strongest_pair_upstream_axis': strongest7['upstream_dominant_axis'],
            'strongest_shell': sig7['strongest_shell'],
            'active_axis_summaries': {
                ax: {
                    'dominant_mode': act7['axis_summaries'][ax]['dominant_mode'],
                    'mean_pair_strength': act7['axis_summaries'][ax]['mean_pair_strength'],
                    'mean_polarity_projection': act7['axis_summaries'][ax]['mean_polarity_projection'],
                    'mean_handoff_gate_score': act7['axis_summaries'][ax]['mean_handoff_gate_score'],
                    'pair_gate_pass_fraction': act7['axis_summaries'][ax]['pair_gate_pass_fraction'],
                }
                for ax in ('x', 'y', 'z')
            },
        },
        'seed8': {
            'overall_mode': row8['dominant_mode'],
            'overall_axis': row8['dominant_axis'],
            'active_mode': row8['active_dominant_mode'],
            'active_axis': row8['active_dominant_axis'],
            'active_signal_sign': sig8['direction_sign'],
            'upstream_axis_match_fraction': sig8['upstream_axis_match_fraction'],
            'strongest_pair_mode': strongest8['dominant_mode'],
            'strongest_pair_axis': strongest8['axis'],
            'strongest_pair_upstream_mode': strongest8['upstream_dominant_mode'],
            'strongest_pair_upstream_axis': strongest8['upstream_dominant_axis'],
            'strongest_shell': sig8['strongest_shell'],
            'active_axis_summaries': {
                ax: {
                    'dominant_mode': act8['axis_summaries'][ax]['dominant_mode'],
                    'mean_pair_strength': act8['axis_summaries'][ax]['mean_pair_strength'],
                    'mean_polarity_projection': act8['axis_summaries'][ax]['mean_polarity_projection'],
                    'mean_handoff_gate_score': act8['axis_summaries'][ax]['mean_handoff_gate_score'],
                    'pair_gate_pass_fraction': act8['axis_summaries'][ax]['pair_gate_pass_fraction'],
                }
                for ax in ('x', 'y', 'z')
            },
        },
        'evidence': evidence,
        'inferred_primary_source': inferred_primary_source,
        'secondary_contributors': secondary,
    }
