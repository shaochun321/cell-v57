from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SUPPORT_FEATURES = [
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'temporal_agg_rotation_mid_to_late_peak_ratio',
    'overview_translation_dipole_x_mean',
]
LOW_IS_BAD = {
    'overview_translation_energy_peak_abs',
    'overview_translation_quad_xx_mean',
    'overview_event_energy_peak_abs',
    'overview_translation_dipole_x_mean',
}
HIGH_IS_BAD = {
    'temporal_agg_rotation_mid_to_late_peak_ratio',
}


def margin_to_support(value: float, min_v: float, max_v: float) -> float:
    if value < min_v:
        return value - min_v
    if value > max_v:
        return value - max_v
    return 0.0


def classify_violation(feature: str, value: float, min_v: float, max_v: float) -> str:
    if min_v <= value <= max_v:
        return 'inside_seen_support'
    if value < min_v:
        return 'below_seen_min'
    return 'above_seen_max'


def main() -> None:
    p = argparse.ArgumentParser(description='Study whether the unique N224 late-soft negative-translation residual admits a clean seen-scale-only boundary restoration inside the current gate family.')
    p.add_argument('--audit-json', type=str, default='outputs/stage1_global_overview_farther_scale_n224_latesoft_negative_translation_residual_audit/stage1_global_overview_farther_scale_n224_latesoft_negative_translation_residual_audit_analysis.json')
    p.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_latesoft_negative_boundary_study')
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with open(args.audit_json, 'r', encoding='utf-8') as f:
        audit = json.load(f)

    residual = audit['residual_case']
    n192 = audit['comparison_case_n192']
    seen_ranges = audit['seen_translation_x_neg_late_soft_ranges']

    support_rows: list[dict[str, Any]] = []
    outside_count = 0
    for feature in SUPPORT_FEATURES:
        r = seen_ranges[feature]
        rv = residual['features'][feature]
        nv = n192['features'][feature]
        residual_status = classify_violation(feature, rv, r['min'], r['max'])
        n192_status = classify_violation(feature, nv, r['min'], r['max'])
        if residual_status != 'inside_seen_support':
            outside_count += 1
        support_rows.append({
            'feature': feature,
            'seen_min': r['min'],
            'seen_max': r['max'],
            'seen_mean': r['mean'],
            'n192_value': nv,
            'n192_status': n192_status,
            'n224_residual_value': rv,
            'n224_residual_status': residual_status,
            'n224_support_margin': margin_to_support(rv, r['min'], r['max']),
            'n192_to_n224_delta': residual['features'][feature] - n192['features'][feature],
        })

    sign_persistence = {
        'n192_neg_over_pos_ratio': n192['sign_distance_neg'] / n192['sign_distance_pos'],
        'n224_residual_neg_over_pos_ratio': residual['sign_distance_neg'] / residual['sign_distance_pos'],
        'n192_sign_prefers_neg': n192['sign_distance_neg'] < n192['sign_distance_pos'],
        'n224_residual_sign_prefers_neg': residual['sign_distance_neg'] < residual['sign_distance_pos'],
    }

    dominant_gate_drift = sorted(
        [
            {
                'key': row['feature'],
                'n192_to_n224_delta': row['n192_to_n224_delta'],
                'support_violation': row['n224_residual_status'],
                'support_margin': row['n224_support_margin'],
            }
            for row in support_rows
        ],
        key=lambda row: abs(row['n192_to_n224_delta']),
        reverse=True,
    )

    clean_boundary_restoration_possible = outside_count == 0
    verdict = 'no_clean_seen_scale_only_boundary_fix_inside_current_gate_family'
    interpretation = (
        'The unique N224 late-soft negative-translation residual remains sign-coherent, but it exits seen-scale '
        'translation_x_neg_late_soft support on multiple gate axes at once. This means the current five-key gate family '
        'does not contain a clean seen-scale-only boundary-restoration fix unless one is willing to extrapolate beyond seen support. '
        'The next branch should therefore study a sign-aware gate fallback or a richer temporal/trace gate basis, not another ad hoc farther-scale veto.'
    )

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_latesoft_negative_boundary_study',
        'selection_rule': 'audit-only study using the v30 residual audit and seen-scale translation_x_neg_late_soft support ranges; no new threshold selection and no target-scale tuning',
        'audit_source_protocol': audit['protocol'],
        'support_features': SUPPORT_FEATURES,
        'support_rows': support_rows,
        'outside_seen_support_count': outside_count,
        'sign_persistence': sign_persistence,
        'residual_gate_margin_translation_minus_nontranslation': residual['gate_margin_translation_minus_nontranslation'],
        'n192_gate_margin_translation_minus_nontranslation': n192['gate_margin_translation_minus_nontranslation'],
        'dominant_gate_drift': dominant_gate_drift,
        'clean_boundary_restoration_possible_inside_current_gate_family': clean_boundary_restoration_possible,
        'verdict': verdict,
        'interpretation': interpretation,
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n224_latesoft_negative_boundary_study_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N224 late-soft negative-translation boundary study',
        '',
        'This study asks a narrow question: does the unique `N224 / seed 9 / translation_x_neg_late_soft -> baseline` residual admit a **clean seen-scale-only boundary restoration** inside the current five-key gate family?',
        '',
        '## Selection discipline',
        '- audit only; no new threshold selection',
        '- no target-scale tuning',
        '- no new farther-scale veto family',
        '- use the v30 residual-audit outputs as the factual source of the residual geometry',
        '',
        '## Support features checked against seen `translation_x_neg_late_soft` support',
        f'- {SUPPORT_FEATURES}',
        '',
        '## Result',
        f'- residual gate margin at N224: `{residual["gate_margin_translation_minus_nontranslation"]:.6f}`',
        f'- comparison gate margin at N192: `{n192["gate_margin_translation_minus_nontranslation"]:.6f}`',
        f'- number of checked support features outside seen support at N224: `{outside_count}` / `{len(SUPPORT_FEATURES)}`',
        f'- sign remains coherent toward `translation_x_neg`: `{sign_persistence["n224_residual_sign_prefers_neg"]}`',
        f'- clean boundary restoration inside current gate family: `{clean_boundary_restoration_possible}`',
        '',
        '## Support comparison',
    ]
    for row in support_rows:
        lines.extend([
            f'- `{row["feature"]}`',
            f'  - seen range: `[{row["seen_min"]:.6f}, {row["seen_max"]:.6f}]`',
            f'  - N192 value: `{row["n192_value"]:.6f}` ({row["n192_status"]})',
            f'  - N224 residual value: `{row["n224_residual_value"]:.6f}` ({row["n224_residual_status"]})',
            f'  - N224 support margin: `{row["n224_support_margin"]:.6f}`',
            f'  - N192 -> N224 delta: `{row["n192_to_n224_delta"]:.6f}`',
        ])
    lines.extend([
        '',
        '## Sign persistence',
        f'- N192 neg/pos sign-distance ratio: `{sign_persistence["n192_neg_over_pos_ratio"]:.6f}`',
        f'- N224 residual neg/pos sign-distance ratio: `{sign_persistence["n224_residual_neg_over_pos_ratio"]:.6f}`',
        '- Reading: the residual is still sign-coherent toward `translation_x_neg`; the failure happens before the sign branch is reached.',
        '',
        '## Interpretation',
        '- The residual is not a rotation-leak event and not a sign collapse.',
        '- It exits seen `translation_x_neg_late_soft` support on multiple gate axes at once.',
        '- Therefore a clean seen-scale-only repair **inside the current five-key gate family** is not supported by evidence.',
        '- The next honest branch is to test a **sign-aware gate fallback** or a **richer temporal/trace gate basis**, rather than invent another farther-scale veto.',
        '',
        '## Mainline impact',
        '- keep the overview-first mainline unchanged',
        '- keep the current farther-scale separator unchanged',
        '- do not promote another patch-style farther-scale rule yet',
        '- next authoritative task: sign-aware gate-fallback study for the N224 late-soft negative residual',
    ])

    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_LATESOFT_NEGATIVE_BOUNDARY_STUDY_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
