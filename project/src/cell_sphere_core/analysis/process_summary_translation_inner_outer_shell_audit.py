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


def _x_summary(case_row: dict[str, Any]) -> dict[str, Any]:
    return dict(case_row.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get('x', {}))


def audit_translation_inner_outer_shell(repeatability_report: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in repeatability_report.get('seeds', [])]
    runs: dict[int, dict[str, Any]] = {}
    for run in repeatability_report.get('seed_runs', []):
        seed = int(run.get('seed', 0))
        analysis = dict(run.get('analysis', {}))
        if not analysis:
            analysis_path = run.get('analysis_path')
            if analysis_path:
                analysis = _load_json(analysis_path)
        runs[seed] = analysis
    if not seeds:
        seeds = sorted(runs)
    reference_seed = seeds[0] if seeds else 0

    reference_shells: dict[str, int] = {}
    per_seed: list[dict[str, Any]] = []
    for case_name in TRANSLATION_CASES:
        ref_case = runs.get(reference_seed, {}).get('cases', {}).get(case_name, {})
        ref_x = _x_summary(ref_case)
        reference_shells[case_name] = int(ref_x.get('strongest_shell', -1))

    failures: list[str] = []
    warnings: list[str] = []
    evidence = {
        'family_wide_raw_sign_inversion': False,
        'outer_shell_shift_detected': False,
        'strongest_pair_sign_failure_detected': False,
        'strongest_pair_mode_collapse_detected': False,
        'axis_drift_detected': False,
    }
    primary = 'undetermined'
    secondary: list[str] = []

    for seed in seeds:
        row = {'seed': seed, 'cases': {}}
        family_raw_inversion = True
        family_outer_shift = True
        family_pair_sign_failure = True
        family_pair_mode_collapse = True
        any_axis_drift = False
        for case_name, expected_sign in TRANSLATION_CASES.items():
            case = runs.get(seed, {}).get('cases', {}).get(case_name, {})
            x = _x_summary(case)
            strongest_shell = int(x.get('strongest_shell', -1))
            ref_shell = reference_shells.get(case_name, strongest_shell)
            sp = dict(x.get('strongest_pair', {}))
            sp_diff = float(sp.get('differential_channels', {}).get('polarity_projection', 0.0))
            sp_mode = str(sp.get('dominant_mode', 'mixed'))
            sp_axis = str(sp.get('dominant_axis', 'none'))
            mean_pol = float(x.get('mean_polarity_projection', 0.0))
            active_axis = str(case.get('active_dominant_axis', 'none'))
            active_mode = str(case.get('active_dominant_mode', 'mixed'))
            raw_sign_ok = _sign_matches(mean_pol, expected_sign)
            sp_sign_ok = _sign_matches(sp_diff, expected_sign)
            shell_shift = strongest_shell != ref_shell
            max_shell = max([int(k) for k in dict(x.get('mean_shell_strengths', {})).keys()] or [-1])
            outer_dominant = max_shell >= 0 and strongest_shell >= max(1, (max_shell + 1)//2)
            pair_mode_ok = (sp_mode == 'translation_like' and sp_axis == 'x')
            any_axis_drift = any_axis_drift or active_axis != 'x'
            family_raw_inversion = family_raw_inversion and (not raw_sign_ok)
            family_outer_shift = family_outer_shift and shell_shift and outer_dominant
            family_pair_sign_failure = family_pair_sign_failure and (not sp_sign_ok)
            family_pair_mode_collapse = family_pair_mode_collapse and (not pair_mode_ok)
            row['cases'][case_name] = {
                'expected_sign': expected_sign,
                'mean_polarity_projection': mean_pol,
                'raw_sign_ok': raw_sign_ok,
                'strongest_shell': strongest_shell,
                'reference_shell': ref_shell,
                'shell_shift': shell_shift,
                'outer_shell_dominant': outer_dominant,
                'strongest_pair_polarity_projection': sp_diff,
                'strongest_pair_sign_ok': sp_sign_ok,
                'strongest_pair_mode': sp_mode,
                'strongest_pair_axis': sp_axis,
                'strongest_pair_mode_ok': pair_mode_ok,
                'active_dominant_mode': active_mode,
                'active_dominant_axis': active_axis,
            }
        row['family_raw_inversion'] = family_raw_inversion
        row['family_outer_shift'] = family_outer_shift
        row['family_pair_sign_failure'] = family_pair_sign_failure
        row['family_pair_mode_collapse'] = family_pair_mode_collapse
        row['axis_drift_detected'] = any_axis_drift
        per_seed.append(row)

    evidence['family_wide_raw_sign_inversion'] = any(r['family_raw_inversion'] for r in per_seed)
    evidence['outer_shell_shift_detected'] = any(r['family_outer_shift'] for r in per_seed)
    evidence['strongest_pair_sign_failure_detected'] = any(r['family_pair_sign_failure'] for r in per_seed)
    evidence['strongest_pair_mode_collapse_detected'] = any(r['family_pair_mode_collapse'] for r in per_seed)
    evidence['axis_drift_detected'] = any(r['axis_drift_detected'] for r in per_seed)

    if evidence['family_wide_raw_sign_inversion'] and evidence['outer_shell_shift_detected'] and evidence['strongest_pair_sign_failure_detected']:
        primary = 'mirrored_translation_readout_redistribution'
        if evidence['axis_drift_detected']:
            secondary.append('axis_summary_weighting')
        if evidence['strongest_pair_mode_collapse_detected']:
            secondary.append('outer_shell_pair_mode_collapse')
        warnings.append('translation sign inversion is already present in the strongest outer-shell x-pair, so shell weighting alone is insufficient')
    elif evidence['family_wide_raw_sign_inversion'] and evidence['outer_shell_shift_detected']:
        primary = 'shell_aggregation_weighting'
    else:
        failures.append('unable to determine whether translation shell migration reflects weighting or genuine mirrored readout redistribution')

    return {
        'suite': 'process_summary_translation_inner_outer_shell_audit',
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


def audit_translation_inner_outer_shell_files(*, repeatability_report_path: str | Path) -> dict[str, Any]:
    return audit_translation_inner_outer_shell(_load_json(repeatability_report_path))
