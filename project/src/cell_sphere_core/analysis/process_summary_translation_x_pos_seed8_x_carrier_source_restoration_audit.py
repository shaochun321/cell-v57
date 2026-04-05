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
        pair_rows: list[dict[str, Any]] = []
        for pair in sorted(
            [item for item in atlas_row.get('pair_summaries', []) if str(item.get('axis', 'none')) == 'x'],
            key=lambda item: int(item.get('shell_index', -1)),
        ):
            mode_scores = dict(pair.get('mode_scores', {}))
            pair_rows.append(
                {
                    'shell_index': int(pair.get('shell_index', -1)),
                    'pair_key': str(pair.get('pair_key', 'none')),
                    'dominant_mode': str(pair.get('dominant_mode', 'none')),
                    'dominant_axis': str(pair.get('dominant_axis', 'none')),
                    'mode_margin': float(pair.get('mode_margin', 0.0)),
                    'pair_strength': float(pair.get('pair_strength', 0.0)),
                    'direction_sign': float(pair.get('direction_sign', 0.0)),
                    'translation_like': float(mode_scores.get('translation_like', 0.0)),
                    'static_like': float(mode_scores.get('static_like', 0.0)),
                    'rotation_like': float(mode_scores.get('rotation_like', 0.0)),
                }
            )
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
        'total': total,
        'per_shell': {str(shell): int(count) for shell, count in sorted(per_shell.items())},
    }


def _inner_shells_missing(seed8_counts: dict[str, Any]) -> bool:
    per_shell = seed8_counts['per_shell']
    return int(per_shell.get('0', 0)) == 0 and int(per_shell.get('1', 0)) == 0


def _seed7_inner_shells_present(seed7_counts: dict[str, Any]) -> bool:
    per_shell = seed7_counts['per_shell']
    return int(per_shell.get('0', 0)) >= 1 and int(per_shell.get('1', 0)) >= 1


def _seed8_outer_shells_survive(seed8_counts: dict[str, Any]) -> bool:
    per_shell = seed8_counts['per_shell']
    return int(per_shell.get('2', 0)) >= 1 and int(per_shell.get('3', 0)) >= 1


def _seed8_shell2_retention_loss(seed8_active_rows: list[dict[str, Any]]) -> bool:
    shell2_modes: list[str] = []
    for window in seed8_active_rows:
        shell2 = next((row for row in window['pair_rows'] if int(row['shell_index']) == 2), None)
        if shell2 is not None:
            shell2_modes.append(str(shell2['dominant_mode']))
    return len(shell2_modes) >= 2 and shell2_modes[0] == 'translation_like' and shell2_modes[1] == 'static_like'


def _seed8_inner_shells_ultraweak_static(seed8_active_rows: list[dict[str, Any]]) -> bool:
    inner_rows: list[dict[str, Any]] = []
    for window in seed8_active_rows:
        inner_rows.extend(
            row for row in window['pair_rows'] if int(row['shell_index']) in (0, 1)
        )
    return bool(inner_rows) and all(
        row['dominant_mode'] == 'static_like' and row['pair_strength'] <= 0.07 for row in inner_rows
    )


def _phase_x_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json['phase_summaries']['active']['axis_summaries']['x'])


def _render_seed_summary(summary_json: dict[str, Any], active_rows: list[dict[str, Any]], carrier_counts: dict[str, Any]) -> dict[str, Any]:
    active_x = _phase_x_summary(summary_json)
    return {
        'active_translation_carrier_counts': carrier_counts,
        'phase_active_x_summary': {
            'raw_mean_polarity_projection': float(active_x.get('raw_mean_polarity_projection', 0.0)),
            'mean_polarity_projection': float(active_x.get('mean_polarity_projection', 0.0)),
            'support_weighted_mean_polarity_projection': float(active_x.get('support_weighted_mean_polarity_projection', 0.0)),
            'carrier_floor_weighted_polarity_projection': float(active_x.get('carrier_floor_weighted_polarity_projection', 0.0)),
            'translation_carrier_pair_count': int(active_x.get('translation_carrier_pair_count', 0)),
            'carrier_floor_pair_count': int(active_x.get('carrier_floor_pair_count', 0)),
            'strongest_shell': int(active_x.get('strongest_shell', -1)),
            'mean_shell_strengths': dict(active_x.get('mean_shell_strengths', {})),
        },
        'active_x_pair_rows': active_rows,
    }


def build_translation_x_pos_seed8_x_carrier_source_restoration_audit(
    *,
    repeatability_audit_path: str | Path,
    seed7_summary_path: str | Path,
    seed7_atlas_trace_path: str | Path,
    seed8_summary_path: str | Path,
    seed8_atlas_trace_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed7_summary = _load_json(seed7_summary_path)
    seed8_summary = _load_json(seed8_summary_path)
    seed7_active_rows = _active_x_pair_rows(_load_json(seed7_atlas_trace_path))
    seed8_active_rows = _active_x_pair_rows(_load_json(seed8_atlas_trace_path))
    seed7_counts = _active_translation_carrier_counts(seed7_active_rows)
    seed8_counts = _active_translation_carrier_counts(seed8_active_rows)

    seed7_active_x = _phase_x_summary(seed7_summary)
    seed8_active_x = _phase_x_summary(seed8_summary)

    evidence = {
        'seed7_inner_shell_translation_carriers_present': _seed7_inner_shells_present(seed7_counts),
        'seed8_inner_shell_translation_carriers_missing': _inner_shells_missing(seed8_counts),
        'seed8_outer_shell_translation_carriers_survive': _seed8_outer_shells_survive(seed8_counts),
        'seed8_shell2_retention_loss_between_active_windows': _seed8_shell2_retention_loss(seed8_active_rows),
        'seed8_inner_shells_are_ultraweak_static_rows': _seed8_inner_shells_ultraweak_static(seed8_active_rows),
        'seed8_active_translation_carrier_total_below_seed7': int(seed8_counts['total']) < int(seed7_counts['total']),
        'seed8_phase_translation_carrier_pair_count_below_seed7': int(seed8_active_x.get('translation_carrier_pair_count', 0)) < int(seed7_active_x.get('translation_carrier_pair_count', 0)),
        'seed8_phase_carrier_floor_pair_count_below_seed7': int(seed8_active_x.get('carrier_floor_pair_count', 0)) < int(seed7_active_x.get('carrier_floor_pair_count', 0)),
        'seed8_strongest_shell_shifted_outward': int(seed7_active_x.get('strongest_shell', -1)) in (0, 1) and int(seed8_active_x.get('strongest_shell', -1)) in (2, 3),
    }

    contracts_passed = all(evidence.values())
    inferred_primary_source = 'translation_x_pos_seed8_x_carrier_generation_loss' if contracts_passed else 'undetermined'
    secondary_contributors: list[str] = []
    if contracts_passed:
        secondary_contributors = [
            'shell2_retention_loss_in_second_active_window',
            'inner_shell_ultraweak_static_contamination',
        ]

    return {
        'suite': 'translation_x_pos_seed8_x_carrier_source_restoration_audit_r1',
        'contracts': {'passed': contracts_passed},
        'baseline_repeatability_failures': repeatability.get('failures', []),
        'seed7': _render_seed_summary(seed7_summary, seed7_active_rows, seed7_counts),
        'seed8': _render_seed_summary(seed8_summary, seed8_active_rows, seed8_counts),
        'evidence': evidence,
        'inferred_primary_source': inferred_primary_source,
        'secondary_contributors': secondary_contributors,
        'repair_recommendation': {
            'next_step': 'stop_summary_microblends_and_restore_upstream_x_carrier_sources',
            'primary_branch': 'carrier_generation_restoration',
            'secondary_branch': 'shell2_active_retention_restoration',
            'isolate': ['rotation_z_overall_mode_cross_seed_instability'],
        },
    }
