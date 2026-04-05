from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _fmt_mode_axis(mode: str, axis: str) -> str:
    return f"{mode}/{axis}"


def _active_window_rows(process_trace: list[dict[str, Any]], shell_trace: list[dict[str, Any]], atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, (process_row, shell_row, atlas_row) in enumerate(zip(process_trace, shell_trace, atlas_trace)):
        if str(process_row.get('phase', 'baseline')) != 'active':
            continue
        strongest_pair = dict(atlas_row.get('strongest_pair', {}))
        rows.append(
            {
                'window_index': int(index),
                'window_start': float(process_row.get('window_start', 0.0)),
                'window_end': float(process_row.get('window_end', 0.0)),
                'process_dominant_mode': str(process_row.get('dominant_mode', 'none')),
                'process_dominant_axis': str(process_row.get('dominant_axis', 'none')),
                'shell_dominant_mode': str(shell_row.get('shell_dominant_mode', 'none')),
                'shell_dominant_axis': str(shell_row.get('shell_dominant_axis', 'none')),
                'atlas_dominant_mode': str(atlas_row.get('atlas_dominant_mode', 'none')),
                'atlas_dominant_axis': str(atlas_row.get('atlas_dominant_axis', 'none')),
                'strongest_pair_mode': str(strongest_pair.get('dominant_mode', 'none')),
                'strongest_pair_axis': str(strongest_pair.get('dominant_axis', 'none')),
            }
        )
    return rows


def _shell_balance_rows(shell_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for index, shell_row in enumerate(shell_trace):
        if str(shell_row.get('phase', 'baseline')) != 'active':
            continue
        balances: list[dict[str, Any]] = []
        for summary in sorted(shell_row.get('shell_summaries', []), key=lambda item: int(item.get('shell_index', -1))):
            axis_balance = dict(summary.get('axis_polarity_balance', {}))
            balances.append(
                {
                    'shell_index': int(summary.get('shell_index', -1)),
                    'x_balance': float(axis_balance.get('x', 0.0)),
                    'y_balance': float(axis_balance.get('y', 0.0)),
                    'z_balance': float(axis_balance.get('z', 0.0)),
                    'top_sector': str(summary.get('top_sector', 'none')),
                    'dominant_mode': str(summary.get('dominant_mode', 'none')),
                    'dominant_axis': str(summary.get('dominant_axis', 'none')),
                }
            )
        payload.append(
            {
                'window_index': int(index),
                'window_start': float(shell_row.get('window_start', 0.0)),
                'window_end': float(shell_row.get('window_end', 0.0)),
                'shell_rows': balances,
            }
        )
    return payload


def _seed_payload(process_trace: list[dict[str, Any]], shell_trace: list[dict[str, Any]], atlas_trace: list[dict[str, Any]]) -> dict[str, Any]:
    active_windows = _active_window_rows(process_trace, shell_trace, atlas_trace)
    active_shell_balance_rows = _shell_balance_rows(shell_trace)
    return {
        'active_windows': active_windows,
        'active_shell_balance_rows': active_shell_balance_rows,
    }


def _seed7_reference_is_clean(seed7: dict[str, Any]) -> bool:
    return all(
        row['process_dominant_mode'] == 'translation_like'
        and row['process_dominant_axis'] == 'x'
        and row['shell_dominant_mode'] == 'translation_like'
        and row['shell_dominant_axis'] == 'x'
        and row['atlas_dominant_mode'] == 'translation_like'
        and row['atlas_dominant_axis'] == 'x'
        and row['strongest_pair_mode'] == 'translation_like'
        and row['strongest_pair_axis'] == 'x'
        for row in seed7['active_windows']
    )


def _seed8_process_breaks_before_shell(seed8: dict[str, Any]) -> bool:
    return all(
        not (row['process_dominant_mode'] == 'translation_like' and row['process_dominant_axis'] == 'x')
        and row['shell_dominant_mode'] == 'static_like'
        and row['shell_dominant_axis'] == 'none'
        and row['strongest_pair_mode'] == 'static_like'
        and row['strongest_pair_axis'] == 'none'
        for row in seed8['active_windows']
    )


def _seed8_shell2_x_survives_but_does_not_mature(seed8: dict[str, Any]) -> bool:
    if not seed8['active_shell_balance_rows']:
        return False
    first_window = seed8['active_shell_balance_rows'][0]
    shell2 = next((row for row in first_window['shell_rows'] if row['shell_index'] == 2), None)
    if shell2 is None:
        return False
    x_abs = abs(float(shell2['x_balance']))
    y_abs = abs(float(shell2['y_balance']))
    close_margin = abs(x_abs - y_abs)
    return x_abs >= y_abs and close_margin <= 0.005


def _seed8_shell3_y_preempts_after_collapse(seed8: dict[str, Any]) -> bool:
    shell3_rows: list[dict[str, Any]] = []
    for window in seed8['active_shell_balance_rows']:
        shell3 = next((row for row in window['shell_rows'] if row['shell_index'] == 3), None)
        if shell3 is not None:
            shell3_rows.append(shell3)
    return bool(shell3_rows) and all(abs(float(row['y_balance'])) > abs(float(row['x_balance'])) for row in shell3_rows)


def _seed8_shell2_can_still_lean_x(seed8: dict[str, Any]) -> bool:
    shell2_rows: list[dict[str, Any]] = []
    for window in seed8['active_shell_balance_rows']:
        shell2 = next((row for row in window['shell_rows'] if row['shell_index'] == 2), None)
        if shell2 is not None:
            shell2_rows.append(shell2)
    return any(abs(float(row['x_balance'])) >= abs(float(row['y_balance'])) for row in shell2_rows)


def _render_window_table(seed_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in seed_payload['active_windows']:
        rows.append(
            {
                'window_index': row['window_index'],
                'window_start': row['window_start'],
                'window_end': row['window_end'],
                'process': _fmt_mode_axis(row['process_dominant_mode'], row['process_dominant_axis']),
                'shell': _fmt_mode_axis(row['shell_dominant_mode'], row['shell_dominant_axis']),
                'atlas': _fmt_mode_axis(row['atlas_dominant_mode'], row['atlas_dominant_axis']),
                'strongest_pair': _fmt_mode_axis(row['strongest_pair_mode'], row['strongest_pair_axis']),
            }
        )
    return rows


def build_translation_x_pos_upstream_candidate_anatomy_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_process_trace_path: str | Path,
    seed7_shell_trace_path: str | Path,
    seed7_atlas_trace_path: str | Path,
    seed8_process_trace_path: str | Path,
    seed8_shell_trace_path: str | Path,
    seed8_atlas_trace_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7 = _seed_payload(
        _load_json(seed7_process_trace_path),
        _load_json(seed7_shell_trace_path),
        _load_json(seed7_atlas_trace_path),
    )
    seed8 = _seed_payload(
        _load_json(seed8_process_trace_path),
        _load_json(seed8_shell_trace_path),
        _load_json(seed8_atlas_trace_path),
    )

    evidence = {
        'seed7_reference_chain_is_clean': _seed7_reference_is_clean(seed7),
        'seed8_process_to_shell_break_occurs_before_handoff': _seed8_process_breaks_before_shell(seed8),
        'seed8_shell2_x_survives_but_does_not_mature': _seed8_shell2_x_survives_but_does_not_mature(seed8),
        'seed8_shell2_can_still_lean_x_locally': _seed8_shell2_can_still_lean_x(seed8),
        'seed8_shell3_y_preempts_after_collapse': _seed8_shell3_y_preempts_after_collapse(seed8),
    }

    contracts_passed = all(evidence.values())
    inferred_primary_source = 'translation_x_pos_upstream_candidate_selection_collapse' if contracts_passed else 'undetermined'
    secondary = []
    if contracts_passed:
        secondary = [
            'outer_shell_y_preemption_after_x_candidate_fails_to_mature',
            'process_to_shell_direction_organization_breaks_before_atlas_handoff',
            'y_axis_visibility_is_secondary_not_primary',
        ]

    return {
        'suite': 'translation_x_pos_upstream_candidate_anatomy_audit_r1',
        'contracts': {'passed': contracts_passed},
        'baseline_repeatability_failures': repeatability.get('failures', []),
        'seed7': {
            'active_windows': _render_window_table(seed7),
            'active_shell_balance_rows': seed7['active_shell_balance_rows'],
        },
        'seed8': {
            'active_windows': _render_window_table(seed8),
            'active_shell_balance_rows': seed8['active_shell_balance_rows'],
        },
        'evidence': evidence,
        'inferred_primary_source': inferred_primary_source,
        'secondary_contributors': secondary,
        'interpretation': {
            'primary_branch': 'selection_collapse',
            'secondary_branch': 'outer_shell_y_preemption',
            'project_rule': 'continue_only_on_front_end_direction_organization',
        },
    }
