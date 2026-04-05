from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _active_process_rows(process_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(process_trace):
        if str(row.get('phase', 'baseline')) != 'active':
            continue
        contrib = dict(row.get('channel_contributions', {}))
        rows.append(
            {
                'window_index': int(index),
                'process': f"{row.get('dominant_mode', 'none')}/{row.get('dominant_axis', 'none')}",
                'translation_like': float(contrib.get('translation_like', 0.0)),
                'rotation_like': float(contrib.get('rotation_like', 0.0)),
                'mean_x_direction': float(contrib.get('mean_x_direction', 0.0)),
                'mean_z_circulation': float(contrib.get('mean_z_circulation', 0.0)),
                'mode_margin': float(row.get('mode_margin', 0.0)),
            }
        )
    return rows


def _active_shell_rows(shell_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(shell_trace):
        if str(row.get('phase', 'baseline')) != 'active':
            continue
        rows.append(
            {
                'window_index': int(index),
                'shell': f"{row.get('shell_dominant_mode', 'none')}/{row.get('shell_dominant_axis', 'none')}",
                'upstream': f"{row.get('upstream_dominant_mode', 'none')}/{row.get('upstream_dominant_axis', 'none')}",
            }
        )
    return rows


def _summary_row(summary_analysis: dict[str, Any], case_name: str) -> dict[str, Any]:
    case = dict(summary_analysis['cases'][case_name])
    active_signature = dict(case.get('active_signature', {}))
    return {
        'dominant_mode': str(case.get('dominant_mode', 'none')),
        'dominant_axis': str(case.get('dominant_axis', 'none')),
        'active_dominant_mode': str(case.get('active_dominant_mode', 'none')),
        'active_dominant_axis': str(case.get('active_dominant_axis', 'none')),
        'active_mean_polarity_projection': float(active_signature.get('mean_polarity_projection', 0.0)),
        'active_direction_sign': float(active_signature.get('direction_sign', 0.0)),
        'upstream_axis_match_fraction': float(active_signature.get('upstream_axis_match_fraction', 0.0)),
    }


def build_translation_x_pos_process_x_direction_recovery_repair_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_translation_process_trace_path: str | Path,
    seed7_translation_shell_trace_path: str | Path,
    seed7_summary_analysis_path: str | Path,
    seed8_translation_process_trace_path: str | Path,
    seed8_translation_shell_trace_path: str | Path,
    seed8_summary_analysis_path: str | Path,
    seed8_rotation_process_trace_path: str | Path,
    seed8_rotation_shell_trace_path: str | Path,
    seed8_rotation_summary_analysis_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary_analysis = _load_json(seed7_summary_analysis_path)
    seed8_summary_analysis = _load_json(seed8_summary_analysis_path)
    seed8_rotation_summary_analysis = _load_json(seed8_rotation_summary_analysis_path)

    seed7 = {
        'translation_x_pos': {
            'active_process_windows': _active_process_rows(_load_json(seed7_translation_process_trace_path)),
            'active_shell_windows': _active_shell_rows(_load_json(seed7_translation_shell_trace_path)),
            'summary': _summary_row(seed7_summary_analysis, 'translation_x_pos'),
        }
    }
    seed8 = {
        'translation_x_pos': {
            'active_process_windows': _active_process_rows(_load_json(seed8_translation_process_trace_path)),
            'active_shell_windows': _active_shell_rows(_load_json(seed8_translation_shell_trace_path)),
            'summary': _summary_row(seed8_summary_analysis, 'translation_x_pos'),
        },
        'rotation_z_pos': {
            'active_process_windows': _active_process_rows(_load_json(seed8_rotation_process_trace_path)),
            'active_shell_windows': _active_shell_rows(_load_json(seed8_rotation_shell_trace_path)),
            'summary': _summary_row(seed8_rotation_summary_analysis, 'rotation_z_pos'),
        },
    }

    tx7 = seed7['translation_x_pos']
    tx8 = seed8['translation_x_pos']
    rz8 = seed8['rotation_z_pos']

    evidence = {
        'seed7_translation_x_pos_preserved_at_process_level': all(row['process'] == 'translation_like/x' for row in tx7['active_process_windows']),
        'seed7_translation_x_pos_preserved_at_shell_level': all(row['shell'] == 'translation_like/x' for row in tx7['active_shell_windows']),
        'seed7_translation_x_pos_preserved_at_summary_level': tx7['summary']['active_dominant_mode'] == 'translation_like' and tx7['summary']['active_dominant_axis'] == 'x',
        'seed8_translation_x_pos_active_summary_recovered_to_translation_x': tx8['summary']['active_dominant_mode'] == 'translation_like' and tx8['summary']['active_dominant_axis'] == 'x',
        'seed8_translation_x_pos_has_recovered_process_window': any(row['process'] == 'translation_like/x' for row in tx8['active_process_windows']),
        'seed8_translation_x_pos_has_recovered_shell_window': any(row['shell'] == 'translation_like/x' for row in tx8['active_shell_windows']),
        'seed8_rotation_z_pos_guardrail_preserved': rz8['summary']['active_dominant_mode'] == 'rotation_like' and rz8['summary']['active_dominant_axis'] == 'z',
        'seed8_translation_x_pos_residual_sign_instability_remains': tx8['summary']['active_mean_polarity_projection'] <= 0.0,
    }

    contracts_passed = all(
        evidence[key]
        for key in (
            'seed7_translation_x_pos_preserved_at_process_level',
            'seed7_translation_x_pos_preserved_at_shell_level',
            'seed7_translation_x_pos_preserved_at_summary_level',
            'seed8_translation_x_pos_active_summary_recovered_to_translation_x',
            'seed8_translation_x_pos_has_recovered_process_window',
            'seed8_translation_x_pos_has_recovered_shell_window',
            'seed8_rotation_z_pos_guardrail_preserved',
        )
    )

    inferred_outcome = 'translation_x_pos_process_x_direction_recovery_repair_success' if contracts_passed else 'undetermined'
    residual = 'translation_x_pos_active_polarity_sign_not_yet_stable' if evidence['seed8_translation_x_pos_residual_sign_instability_remains'] else 'none'

    return {
        'suite': 'translation_x_pos_process_x_direction_recovery_repair_audit_r1',
        'contracts': {'passed': contracts_passed},
        'repeatability_failures': repeatability.get('failures', []),
        'seed7': seed7,
        'seed8': seed8,
        'evidence': evidence,
        'inferred_outcome': inferred_outcome,
        'residual_issue': residual,
        'interpretation': {
            'primary_effect': 'recover translation_x_pos active mode and axis earlier than gate',
            'guardrail': 'preserve rotation_z_pos active z classification',
            'next_branch': 'repair residual polarity sign instability without undoing process x-direction recovery',
        },
    }
