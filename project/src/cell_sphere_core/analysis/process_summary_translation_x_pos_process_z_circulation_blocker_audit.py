from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _fmt_mode_axis(mode: str, axis: str) -> str:
    return f"{mode}/{axis}"


def _active_process_rows(process_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(process_trace):
        if str(row.get('phase', 'baseline')) != 'active':
            continue
        contrib = dict(row.get('channel_contributions', {}))
        rows.append(
            {
                'window_index': int(index),
                'window_start': float(row.get('window_start', 0.0)),
                'window_end': float(row.get('window_end', 0.0)),
                'process': _fmt_mode_axis(str(row.get('dominant_mode', 'none')), str(row.get('dominant_axis', 'none'))),
                'translation_like': float(contrib.get('translation_like', 0.0)),
                'rotation_like': float(contrib.get('rotation_like', 0.0)),
                'static_like': float(contrib.get('static_like', 0.0)),
                'mean_axial_flux': float(contrib.get('mean_axial_flux', 0.0)),
                'mean_swirl_flux': float(contrib.get('mean_swirl_flux', 0.0)),
                'mean_x_direction': float(contrib.get('mean_x_direction', 0.0)),
                'mean_z_circulation': float(contrib.get('mean_z_circulation', 0.0)),
                'mean_translation_channel': float(contrib.get('mean_translation_channel', 0.0)),
                'mean_rotation_channel': float(contrib.get('mean_rotation_channel', 0.0)),
                'mode_margin': float(row.get('mode_margin', 0.0)),
            }
        )
    return rows


def _active_shell_rows(shell_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(shell_trace):
        if str(row.get('phase', 'baseline')) != 'active':
            continue
        summaries = []
        for shell in sorted(row.get('shell_summaries', []), key=lambda item: int(item.get('shell_index', -1))):
            summaries.append(
                {
                    'shell_index': int(shell.get('shell_index', -1)),
                    'dominant_mode': str(shell.get('dominant_mode', 'none')),
                    'dominant_axis': str(shell.get('dominant_axis', 'none')),
                    'x_balance': float(dict(shell.get('axis_polarity_balance', {})).get('x', 0.0)),
                    'y_balance': float(dict(shell.get('axis_polarity_balance', {})).get('y', 0.0)),
                    'z_balance': float(dict(shell.get('axis_polarity_balance', {})).get('z', 0.0)),
                }
            )
        rows.append(
            {
                'window_index': int(index),
                'shell': _fmt_mode_axis(str(row.get('shell_dominant_mode', 'none')), str(row.get('shell_dominant_axis', 'none'))),
                'upstream_process': _fmt_mode_axis(str(row.get('upstream_dominant_mode', 'none')), str(row.get('upstream_dominant_axis', 'none'))),
                'shell_summaries': summaries,
            }
        )
    return rows


def _all_shell_summaries_static(shell_payload: dict[str, Any]) -> bool:
    return all(
        summary['dominant_mode'] == 'static_like'
        for row in shell_payload['active_shell_windows']
        for summary in row['shell_summaries']
    )


def _seed7_process_is_clean(seed7: dict[str, Any]) -> bool:
    return all(
        row['process'] == 'translation_like/x'
        and row['translation_like'] > row['rotation_like']
        and row['mean_x_direction'] > row['mean_z_circulation']
        for row in seed7['active_process_windows']
    )


def _seed8_process_is_z_blocked(seed8: dict[str, Any]) -> bool:
    return all(
        row['process'] == 'rotation_like/z'
        and row['rotation_like'] > row['translation_like']
        and row['mean_z_circulation'] > row['mean_x_direction']
        for row in seed8['active_process_windows']
    )


def _seed7_shell_override_promotes_x(seed7: dict[str, Any]) -> bool:
    return all(row['shell'] == 'translation_like/x' for row in seed7['active_shell_windows'])


def _seed8_shell_override_never_forms(seed8: dict[str, Any]) -> bool:
    return all(row['shell'] == 'static_like/none' for row in seed8['active_shell_windows'])


def build_translation_x_pos_process_z_circulation_blocker_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_process_trace_path: str | Path,
    seed7_shell_trace_path: str | Path,
    seed8_process_trace_path: str | Path,
    seed8_shell_trace_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7 = {
        'active_process_windows': _active_process_rows(_load_json(seed7_process_trace_path)),
        'active_shell_windows': _active_shell_rows(_load_json(seed7_shell_trace_path)),
    }
    seed8 = {
        'active_process_windows': _active_process_rows(_load_json(seed8_process_trace_path)),
        'active_shell_windows': _active_shell_rows(_load_json(seed8_shell_trace_path)),
    }

    evidence = {
        'seed7_process_translation_reference_is_clean': _seed7_process_is_clean(seed7),
        'seed8_process_is_rotation_z_before_shell': _seed8_process_is_z_blocked(seed8),
        'seed7_shell_override_promotes_translation_x': _seed7_shell_override_promotes_x(seed7),
        'seed8_shell_override_never_forms_after_process_z_rotation': _seed8_shell_override_never_forms(seed8),
        'seed7_and_seed8_shell_summaries_are_both_locally_static': _all_shell_summaries_static(seed7) and _all_shell_summaries_static(seed8),
    }
    contracts_passed = all(evidence.values())
    inferred_primary_source = 'translation_x_pos_process_z_circulation_blocker' if contracts_passed else 'undetermined'
    secondary: list[str] = []
    if contracts_passed:
        secondary = [
            'x_direction_attenuation_before_shell_candidate_maturation',
            'shell_static_summaries_are_downstream_not_primary',
            'repair_should_move_earlier_than_shell_window_override',
        ]

    return {
        'suite': 'translation_x_pos_process_z_circulation_blocker_audit_r1',
        'contracts': {'passed': contracts_passed},
        'baseline_repeatability_failures': repeatability.get('failures', []),
        'seed7': seed7,
        'seed8': seed8,
        'evidence': evidence,
        'inferred_primary_source': inferred_primary_source,
        'secondary_contributors': secondary,
        'interpretation': {
            'primary_branch': 'process_z_circulation_blocker',
            'secondary_branch': 'shell_candidate_maturation_loss',
            'project_rule': 'continue_only_on_front_end_direction_organization',
        },
    }
