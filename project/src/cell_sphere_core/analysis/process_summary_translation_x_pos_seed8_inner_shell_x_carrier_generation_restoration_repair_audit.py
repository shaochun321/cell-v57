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


def _first_active_shell1_restored(active_rows: list[dict[str, Any]]) -> bool:
    if not active_rows:
        return False
    shell1 = next((row for row in active_rows[0]['pair_rows'] if int(row['shell_index']) == 1), None)
    return bool(shell1) and shell1['dominant_mode'] == 'translation_like' and shell1['direction_sign'] > 0.0


def build_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_summary_path: str | Path,
    seed7_atlas_trace_path: str | Path,
    seed8_baseline_summary_path: str | Path,
    seed8_baseline_atlas_trace_path: str | Path,
    seed8_repaired_summary_path: str | Path,
    seed8_repaired_atlas_trace_path: str | Path,
    seed8_xneg_summary_path: str | Path,
    seed8_rotation_summary_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary = _load_json(seed7_summary_path)
    seed7_rows = _active_x_pair_rows(_load_json(seed7_atlas_trace_path))
    seed8_base_summary = _load_json(seed8_baseline_summary_path)
    seed8_base_rows = _active_x_pair_rows(_load_json(seed8_baseline_atlas_trace_path))
    seed8_repaired_summary = _load_json(seed8_repaired_summary_path)
    seed8_repaired_rows = _active_x_pair_rows(_load_json(seed8_repaired_atlas_trace_path))
    seed8_xneg_summary = _load_json(seed8_xneg_summary_path)
    seed8_rotation_summary = _load_json(seed8_rotation_summary_path)

    seed7_counts = _active_translation_carrier_counts(seed7_rows)
    seed8_base_counts = _active_translation_carrier_counts(seed8_base_rows)
    seed8_repaired_counts = _active_translation_carrier_counts(seed8_repaired_rows)

    seed7_active_x = _phase_x_summary(seed7_summary)
    seed8_base_active_x = _phase_x_summary(seed8_base_summary)
    seed8_repaired_active_x = _phase_x_summary(seed8_repaired_summary)
    seed8_xneg_active = _phase_x_summary(seed8_xneg_summary)
    seed8_rotation_active = _phase_summary(seed8_rotation_summary)

    evidence = {
        'baseline_seed8_inner_shell_translation_carriers_missing': int(seed8_base_counts['per_shell'].get('0', 0)) == 0 and int(seed8_base_counts['per_shell'].get('1', 0)) == 0,
        'repaired_seed8_inner_shell_translation_carriers_present': int(seed8_repaired_counts['per_shell'].get('1', 0)) >= 1,
        'repaired_seed8_first_active_window_shell1_translation_restored': _first_active_shell1_restored(seed8_repaired_rows),
        'repaired_seed8_active_translation_carrier_total_exceeds_baseline': int(seed8_repaired_counts['total']) > int(seed8_base_counts['total']),
        'repaired_seed8_translation_carrier_pair_count_exceeds_baseline': int(seed8_repaired_active_x.get('translation_carrier_pair_count', 0)) > int(seed8_base_active_x.get('translation_carrier_pair_count', 0)),
        'repaired_seed8_mean_polarity_projection_exceeds_baseline': abs(float(seed8_repaired_active_x.get('mean_polarity_projection', 0.0))) > abs(float(seed8_base_active_x.get('mean_polarity_projection', 0.0))),
        'repaired_seed8_translation_x_pos_active_mode_axis_preserved': str(seed8_repaired_summary['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(seed8_repaired_summary['phase_summaries']['active']['dominant_axis']) == 'x',
        'repaired_seed8_translation_x_neg_sign_preserved': str(seed8_xneg_summary['phase_summaries']['active']['dominant_mode']) == 'translation_like' and str(seed8_xneg_summary['phase_summaries']['active']['dominant_axis']) == 'x' and float(seed8_xneg_active.get('direction_sign', 0.0)) < 0.0,
        'repaired_seed8_rotation_z_guardrail_preserved': str(seed8_rotation_active.get('dominant_mode', 'none')) == 'rotation_like' and str(seed8_rotation_active.get('dominant_axis', 'none')) == 'z',
    }
    contracts_passed = all(evidence.values())

    return {
        'suite': 'translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit_r1',
        'contracts': {'passed': contracts_passed},
        'repeatability_failures': list(repeatability.get('contracts', {}).get('failures', []) or repeatability.get('failures', []) or []),
        'seed7': {
            'active_translation_carrier_counts': seed7_counts,
            'phase_active_x_summary': seed7_active_x,
        },
        'seed8_baseline': {
            'active_translation_carrier_counts': seed8_base_counts,
            'phase_active_x_summary': seed8_base_active_x,
            'active_x_pair_rows': seed8_base_rows,
        },
        'seed8_repaired': {
            'active_translation_carrier_counts': seed8_repaired_counts,
            'phase_active_x_summary': seed8_repaired_active_x,
            'active_x_pair_rows': seed8_repaired_rows,
        },
        'guardrails': {
            'seed8_translation_x_neg_active_x_summary': seed8_xneg_active,
            'seed8_rotation_z_pos_active_summary': seed8_rotation_active,
        },
        'evidence': evidence,
        'inferred_outcome': 'translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_success' if contracts_passed else 'undetermined',
        'residual_issue': 'shell2_second_active_window_retention_still_unresolved',
    }
