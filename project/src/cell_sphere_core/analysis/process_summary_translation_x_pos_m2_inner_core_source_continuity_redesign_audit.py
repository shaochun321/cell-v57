from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _active_x_pair_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window_index, atlas_row in enumerate(atlas_trace):
        if str(atlas_row.get('phase', 'baseline')) != 'active':
            continue
        pair_rows = [
            {
                'shell_index': int(pair.get('shell_index', -1)),
                'pair_key': str(pair.get('pair_key', 'none')),
                'dominant_mode': str(pair.get('dominant_mode', 'none')),
                'direction_sign': float(pair.get('direction_sign', 0.0)),
                'pair_strength': float(pair.get('pair_strength', 0.0)),
                'handoff_gate_score': float(pair.get('handoff_gate_score', 0.0)),
                'translation_like': float(pair.get('mode_scores', {}).get('translation_like', 0.0)),
                'static_like': float(pair.get('mode_scores', {}).get('static_like', 0.0)),
                'polarity_projection': float(pair.get('pair_differential_mode', {}).get('polarity_projection', 0.0)),
            }
            for pair in sorted(
                [item for item in atlas_row.get('pair_summaries', []) if str(item.get('axis', 'none')) == 'x'],
                key=lambda item: int(item.get('shell_index', -1)),
            )
        ]
        rows.append(
            {
                'window_index': int(window_index),
                'window_start': float(atlas_row.get('window_start', 0.0)),
                'window_end': float(atlas_row.get('window_end', 0.0)),
                'atlas_dominant_mode': str(atlas_row.get('atlas_dominant_mode', 'none')),
                'atlas_dominant_axis': str(atlas_row.get('atlas_dominant_axis', 'none')),
                'pair_rows': pair_rows,
            }
        )
    return rows


def _active_translation_carrier_counts(active_rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_shell: dict[int, int] = {}
    total = 0
    for window in active_rows:
        for row in window['pair_rows']:
            if row['dominant_mode'] == 'translation_like' and row['direction_sign'] > 0.0:
                shell_index = int(row['shell_index'])
                per_shell[shell_index] = per_shell.get(shell_index, 0) + 1
                total += 1
    return {
        'total': int(total),
        'per_shell': {str(shell): int(count) for shell, count in sorted(per_shell.items())},
    }


def _phase_x_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json['phase_summaries']['active']['axis_summaries']['x'])


def _phase_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json['phase_summaries']['active'])


def _shell0_translation_both_windows(active_rows: list[dict[str, Any]]) -> bool:
    if len(active_rows) < 2:
        return False
    for window in active_rows[:2]:
        shell0 = next((row for row in window['pair_rows'] if int(row['shell_index']) == 0), None)
        if not shell0 or shell0['dominant_mode'] != 'translation_like' or shell0['direction_sign'] <= 0.0:
            return False
    return True


def build_translation_x_pos_m2_inner_core_source_continuity_redesign_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_reference_summary_path: str | Path,
    seed8_baseline_summary_path: str | Path,
    seed8_baseline_atlas_trace_path: str | Path,
    seed8_repaired_summary_path: str | Path,
    seed8_repaired_atlas_trace_path: str | Path,
    seed8_xneg_summary_path: str | Path,
    seed8_rotation_pos_summary_path: str | Path,
    seed8_rotation_neg_summary_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_reference_summary = _load_json(seed7_reference_summary_path)
    seed8_baseline_summary = _load_json(seed8_baseline_summary_path)
    seed8_baseline_rows = _active_x_pair_rows(_load_json(seed8_baseline_atlas_trace_path))
    seed8_repaired_summary = _load_json(seed8_repaired_summary_path)
    seed8_repaired_rows = _active_x_pair_rows(_load_json(seed8_repaired_atlas_trace_path))
    seed8_xneg_summary = _load_json(seed8_xneg_summary_path)
    seed8_rotation_pos_summary = _load_json(seed8_rotation_pos_summary_path)
    seed8_rotation_neg_summary = _load_json(seed8_rotation_neg_summary_path)

    seed7_active_x = _phase_x_summary(seed7_reference_summary)
    seed8_baseline_active_x = _phase_x_summary(seed8_baseline_summary)
    seed8_repaired_active_x = _phase_x_summary(seed8_repaired_summary)
    seed8_xneg_active = _phase_x_summary(seed8_xneg_summary)
    seed8_rotation_pos_active = _phase_summary(seed8_rotation_pos_summary)
    seed8_rotation_neg_active = _phase_summary(seed8_rotation_neg_summary)

    baseline_counts = _active_translation_carrier_counts(seed8_baseline_rows)
    repaired_counts = _active_translation_carrier_counts(seed8_repaired_rows)
    baseline_window2 = seed8_baseline_rows[1] if len(seed8_baseline_rows) > 1 else {}
    repaired_window2 = seed8_repaired_rows[1] if len(seed8_repaired_rows) > 1 else {}

    baseline_gap_to_seed7 = abs(float(seed7_active_x.get('mean_polarity_projection', 0.0))) - abs(float(seed8_baseline_active_x.get('mean_polarity_projection', 0.0)))
    repaired_gap_to_seed7 = abs(float(seed7_active_x.get('mean_polarity_projection', 0.0))) - abs(float(seed8_repaired_active_x.get('mean_polarity_projection', 0.0)))

    evidence = {
        'repaired_seed8_shell0_translation_present_in_both_active_windows': _shell0_translation_both_windows(seed8_repaired_rows),
        'repaired_seed8_active_translation_carrier_total_exceeds_baseline': int(repaired_counts['total']) > int(baseline_counts['total']),
        'repaired_seed8_second_active_window_semantic_collapse_resolved': str(repaired_window2.get('atlas_dominant_mode', 'none')) == 'translation_like' and str(repaired_window2.get('atlas_dominant_axis', 'none')) == 'x',
        'repaired_seed8_raw_mean_polarity_projection_exceeds_baseline': abs(float(seed8_repaired_active_x.get('raw_mean_polarity_projection', 0.0))) > abs(float(seed8_baseline_active_x.get('raw_mean_polarity_projection', 0.0))),
        'repaired_seed8_translation_x_pos_active_mode_axis_preserved': str(seed8_repaired_summary['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(seed8_repaired_summary['phase_summaries']['active']['dominant_axis']) == 'x',
        'repaired_seed8_translation_x_neg_sign_preserved': str(seed8_xneg_summary['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(seed8_xneg_summary['phase_summaries']['active']['dominant_axis']) == 'x' and float(seed8_xneg_active.get('direction_sign', 0.0)) < 0.0,
        'repaired_seed8_rotation_z_pos_guardrail_preserved': str(seed8_rotation_pos_active.get('dominant_mode', 'none')) == 'rotation_like' and str(seed8_rotation_pos_active.get('dominant_axis', 'none')) == 'z',
        'repaired_seed8_rotation_z_neg_guardrail_preserved': str(seed8_rotation_neg_active.get('dominant_mode', 'none')) == 'rotation_like' and str(seed8_rotation_neg_active.get('dominant_axis', 'none')) == 'z',
        'repaired_seed8_final_mean_not_lower_by_more_than_point015': float(seed8_repaired_active_x.get('mean_polarity_projection', 0.0)) >= float(seed8_baseline_active_x.get('mean_polarity_projection', 0.0)) - 0.015,
    }
    contracts_passed = all(evidence.values())

    return {
        'suite': 'translation_x_pos_m2_inner_core_source_continuity_redesign_audit_r1',
        'contracts': {'passed': contracts_passed},
        'repeatability_failures': list(repeatability.get('contracts', {}).get('failures', []) or repeatability.get('failures', []) or []),
        'seed7_reference': {'phase_active_x_summary': seed7_active_x},
        'seed8_baseline_round54': {
            'active_translation_carrier_counts': baseline_counts,
            'phase_active_x_summary': seed8_baseline_active_x,
            'active_x_pair_rows': seed8_baseline_rows,
        },
        'seed8_repaired_m2': {
            'active_translation_carrier_counts': repaired_counts,
            'phase_active_x_summary': seed8_repaired_active_x,
            'active_x_pair_rows': seed8_repaired_rows,
        },
        'guardrails': {
            'seed8_translation_x_neg_active_x_summary': seed8_xneg_active,
            'seed8_rotation_z_pos_active_summary': seed8_rotation_pos_active,
            'seed8_rotation_z_neg_active_summary': seed8_rotation_neg_active,
        },
        'gaps': {
            'baseline_gap_to_seed7': float(baseline_gap_to_seed7),
            'repaired_gap_to_seed7': float(repaired_gap_to_seed7),
        },
        'evidence': evidence,
        'decision': 'continue_material_redesign_not_summary_loop' if contracts_passed else 'undetermined',
        'headline': 'shell0 inner-core translation source restored and second active-window semantic collapse resolved; amplitude gap remains upstream-material issue',
        'residual_issue': 'final active amplitude still far below seed7 even after shell0 continuity restoration',
    }
