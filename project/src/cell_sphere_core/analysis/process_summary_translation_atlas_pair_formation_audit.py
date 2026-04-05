from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import numpy as np

TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _sign_matches(value: float, expected: float, *, eps: float = 1e-12) -> bool:
    if abs(value) < eps:
        return False
    return float(np.sign(value)) == float(np.sign(expected))


def _active_x_summary(case_row: dict[str, Any]) -> dict[str, Any]:
    return dict(case_row.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get('x', {}))


def audit_translation_atlas_pair_formation(repeatability_report: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in repeatability_report.get('seeds', [])]
    runs: dict[int, dict[str, Any]] = {}
    for run in repeatability_report.get('seed_runs', []):
        seed = int(run.get('seed', 0))
        analysis = dict(run.get('analysis', {}))
        if not analysis and run.get('analysis_path'):
            analysis = _load_json(run['analysis_path'])
        runs[seed] = analysis
    if not seeds:
        seeds = sorted(runs)
    reference_seed = seeds[0] if seeds else 0

    reference_shells: dict[str, int] = {}
    for case_name in TRANSLATION_CASES:
        ref_case = runs.get(reference_seed, {}).get('cases', {}).get(case_name, {})
        reference_shells[case_name] = int(_active_x_summary(ref_case).get('strongest_shell', -1))

    per_seed: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []
    evidence = {
        'family_wide_raw_sign_inversion': False,
        'shell_interface_redistribution_detected': False,
        'atlas_pair_formation_collapse_detected': False,
        'pair_sign_failure_detected': False,
        'x_axis_support_survives_detected': False,
    }

    for seed in seeds:
        row: dict[str, Any] = {'seed': seed, 'cases': {}}
        family_raw_inversion = True
        family_shell_redistribution = True
        family_pair_collapse = True
        family_pair_sign_failure = True
        family_x_axis_support_survives = True

        for case_name, expected_sign in TRANSLATION_CASES.items():
            case = runs.get(seed, {}).get('cases', {}).get(case_name, {})
            active_x = _active_x_summary(case)
            strongest_shell = int(active_x.get('strongest_shell', -1))
            ref_shell = reference_shells.get(case_name, strongest_shell)
            shell_strengths = {int(k): float(v) for k, v in dict(active_x.get('mean_shell_strengths', {})).items()}
            max_shell = max(shell_strengths) if shell_strengths else -1
            outer_dominant = max_shell >= 0 and strongest_shell >= max(1, (max_shell + 1) // 2)
            shell_shift = strongest_shell != ref_shell

            mean_pol = float(active_x.get('mean_polarity_projection', 0.0))
            raw_sign_ok = _sign_matches(mean_pol, expected_sign)

            support_scores = dict(active_x.get('support_scores', {}))
            x_translation_support = float(support_scores.get('translation_like', 0.0))
            x_static_support = float(support_scores.get('static_like', 0.0))
            x_support_survives = x_translation_support > 0.0 and x_translation_support >= 0.35 * x_static_support

            sp = dict(active_x.get('strongest_pair', {}))
            sp_mode = str(sp.get('dominant_mode', 'mixed'))
            sp_axis = str(sp.get('dominant_axis', 'none'))
            sp_scores = dict(sp.get('mode_scores', {}))
            sp_translation = float(sp_scores.get('translation_like', 0.0))
            sp_static = float(sp_scores.get('static_like', 0.0))
            sp_margin = sp_translation - sp_static
            sp_pol = float(sp.get('differential_channels', {}).get('polarity_projection', 0.0))
            sp_sign_ok = _sign_matches(sp_pol, expected_sign)
            pair_collapse = (sp_mode != 'translation_like') or (sp_axis != 'x') or (sp_margin <= 0.0)

            family_raw_inversion = family_raw_inversion and (not raw_sign_ok)
            family_shell_redistribution = family_shell_redistribution and shell_shift and outer_dominant
            family_pair_collapse = family_pair_collapse and pair_collapse
            family_pair_sign_failure = family_pair_sign_failure and (not sp_sign_ok)
            family_x_axis_support_survives = family_x_axis_support_survives and x_support_survives

            row['cases'][case_name] = {
                'expected_sign': expected_sign,
                'mean_polarity_projection': mean_pol,
                'raw_sign_ok': raw_sign_ok,
                'strongest_shell': strongest_shell,
                'reference_shell': ref_shell,
                'shell_shift': shell_shift,
                'outer_shell_dominant': outer_dominant,
                'x_translation_support': x_translation_support,
                'x_static_support': x_static_support,
                'x_axis_support_survives': x_support_survives,
                'strongest_pair_mode': sp_mode,
                'strongest_pair_axis': sp_axis,
                'strongest_pair_translation_score': sp_translation,
                'strongest_pair_static_score': sp_static,
                'strongest_pair_translation_margin': sp_margin,
                'strongest_pair_polarity_projection': sp_pol,
                'strongest_pair_sign_ok': sp_sign_ok,
                'pair_formation_collapse': pair_collapse,
            }

        row['family_raw_inversion'] = family_raw_inversion
        row['family_shell_interface_redistribution'] = family_shell_redistribution
        row['family_atlas_pair_formation_collapse'] = family_pair_collapse
        row['family_pair_sign_failure'] = family_pair_sign_failure
        row['family_x_axis_support_survives'] = family_x_axis_support_survives
        per_seed.append(row)

    evidence['family_wide_raw_sign_inversion'] = any(r['family_raw_inversion'] for r in per_seed)
    evidence['shell_interface_redistribution_detected'] = any(r['family_shell_interface_redistribution'] for r in per_seed)
    evidence['atlas_pair_formation_collapse_detected'] = any(r['family_atlas_pair_formation_collapse'] for r in per_seed)
    evidence['pair_sign_failure_detected'] = any(r['family_pair_sign_failure'] for r in per_seed)
    evidence['x_axis_support_survives_detected'] = any(r['family_x_axis_support_survives'] for r in per_seed)

    if (
        evidence['family_wide_raw_sign_inversion']
        and evidence['shell_interface_redistribution_detected']
        and evidence['atlas_pair_formation_collapse_detected']
    ):
        primary = 'atlas_pair_formation_collapse'
        secondary = ['shell_interface_redistribution']
        if evidence['pair_sign_failure_detected']:
            secondary.append('pair_polarity_failure')
        warnings.append('translation x-axis support survives at the axis level in at least one seed, but the strongest outer x-pair collapses to static-like, so atlas pair formation is the nearer failure point')
    elif evidence['family_wide_raw_sign_inversion'] and evidence['shell_interface_redistribution_detected']:
        primary = 'shell_interface_redistribution'
        secondary = []
    else:
        primary = 'undetermined'
        secondary = []
        failures.append('unable to separate shell-interface redistribution from atlas pair formation collapse with current repeatability payload')

    return {
        'suite': 'process_summary_translation_atlas_pair_formation_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'reference_shells': reference_shells,
        'evidence': evidence,
        'inferred_primary_source': primary,
        'secondary_contributors': secondary,
        'per_seed': per_seed,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }



def audit_translation_atlas_pair_formation_files(*, repeatability_report_path: str | Path) -> dict[str, Any]:
    return audit_translation_atlas_pair_formation(_load_json(repeatability_report_path))
