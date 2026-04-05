from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _float(v: Any) -> float:
    return float(v)


def audit_translation_mirrored_asymmetry(*, seed_profiles_payload: dict[str, Any], decomposition_payload: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in seed_profiles_payload.get('seeds', [])]
    reference_seed = int(seed_profiles_payload.get('reference_seed', seeds[0] if seeds else 0))
    failures: list[str] = []
    warnings: list[str] = []

    cases = seed_profiles_payload.get('cases', {})
    decomp_rows = {int(r['seed']): r for r in decomposition_payload.get('per_seed', [])}

    if 'translation_x_pos' not in cases or 'translation_x_neg' not in cases:
        failures.append('missing translation_x_pos or translation_x_neg in mirrored readout seed profiles')
    if 8 not in decomp_rows:
        failures.append('missing seed 8 decomposition row required for asymmetry audit')

    per_case: dict[str, Any] = {}
    evidence = {
        'shared_outer_shift_detected': False,
        'symmetric_outer_shift_detected': False,
        'post_shift_failure_asymmetry_detected': False,
        'early_shell_to_carrier_diversion_detected': False,
    }

    inner_collapse_values: list[float] = []
    outer_increase_values: list[float] = []
    pair_shell_shifts: list[int] = []
    mass_shell_shifts: list[int] = []
    failure_modes: dict[str, str] = {}

    if not failures:
        for case_name in ('translation_x_pos', 'translation_x_neg'):
            ref = cases[case_name][str(reference_seed)]
            alt = cases[case_name]['8']
            inner_collapse = _float(ref['inner_translation_share']) - _float(alt['inner_translation_share'])
            outer_increase = _float(alt['outer_translation_share']) - _float(ref['outer_translation_share'])
            pair_shell_shift = int(alt['strongest_shell_by_pair_strength']) - int(ref['strongest_shell_by_pair_strength'])
            mass_shell_shift = int(alt['strongest_shell_by_translation_mass']) - int(ref['strongest_shell_by_translation_mass'])
            inner_collapse_values.append(inner_collapse)
            outer_increase_values.append(outer_increase)
            pair_shell_shifts.append(pair_shell_shift)
            mass_shell_shifts.append(mass_shell_shift)
            failure_mode = decomp_rows[8]['cases'][case_name]['dominant_failure_mode']
            failure_modes[case_name] = failure_mode
            per_case[case_name] = {
                'reference_seed': reference_seed,
                'comparison_seed': 8,
                'inner_translation_share_ref': _float(ref['inner_translation_share']),
                'inner_translation_share_cmp': _float(alt['inner_translation_share']),
                'inner_collapse': inner_collapse,
                'outer_translation_share_ref': _float(ref['outer_translation_share']),
                'outer_translation_share_cmp': _float(alt['outer_translation_share']),
                'outer_increase': outer_increase,
                'pair_strength_shell_ref': int(ref['strongest_shell_by_pair_strength']),
                'pair_strength_shell_cmp': int(alt['strongest_shell_by_pair_strength']),
                'pair_strength_shell_shift': pair_shell_shift,
                'translation_mass_shell_ref': int(ref['strongest_shell_by_translation_mass']),
                'translation_mass_shell_cmp': int(alt['strongest_shell_by_translation_mass']),
                'translation_mass_shell_shift': mass_shell_shift,
                'dominant_failure_mode_cmp': failure_mode,
            }

        shared_outer_shift = all(v > 0.45 for v in outer_increase_values) and all(v > 0.6 for v in inner_collapse_values)
        symmetric_outer_shift = (
            max(abs(inner_collapse_values[0] - inner_collapse_values[1]), abs(outer_increase_values[0] - outer_increase_values[1])) < 0.12
            and max(pair_shell_shifts) - min(pair_shell_shifts) == 0
        )
        post_shift_failure_asymmetry = failure_modes.get('translation_x_pos') != failure_modes.get('translation_x_neg')
        early_shell_diversion = not symmetric_outer_shift

        evidence['shared_outer_shift_detected'] = shared_outer_shift
        evidence['symmetric_outer_shift_detected'] = symmetric_outer_shift
        evidence['post_shift_failure_asymmetry_detected'] = post_shift_failure_asymmetry
        evidence['early_shell_to_carrier_diversion_detected'] = early_shell_diversion

        if shared_outer_shift and symmetric_outer_shift and post_shift_failure_asymmetry:
            primary = 'mirrored_carrier_geometry_bias_after_shared_outer_shift'
            secondary = ['shared_shell_to_carrier_outward_shift']
            warnings.append('translation_x_pos and translation_x_neg undergo nearly the same inner-to-outer redistribution under seed 8, but diverge afterward into different carrier failure modes; the dominant asymmetry is therefore later mirrored-carrier geometry bias rather than early shell-to-carrier diversion')
        elif shared_outer_shift and post_shift_failure_asymmetry:
            primary = 'mixed_outer_shift_and_mirrored_asymmetry'
            secondary = ['shared_shell_to_carrier_outward_shift']
        elif early_shell_diversion:
            primary = 'early_shell_to_carrier_diversion'
            secondary = []
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to distinguish mirrored asymmetry from early shell-to-carrier diversion')

        summary = {
            'inner_collapse_range': [min(inner_collapse_values), max(inner_collapse_values)],
            'outer_increase_range': [min(outer_increase_values), max(outer_increase_values)],
            'pair_shell_shifts': pair_shell_shifts,
            'mass_shell_shifts': mass_shell_shifts,
            'failure_modes': failure_modes,
        }
    else:
        primary = 'undetermined'
        secondary = []
        summary = {}

    return {
        'suite': 'process_summary_translation_mirrored_asymmetry_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'summary': summary,
        'evidence': evidence,
        'per_case': per_case,
        'inferred_primary_source': primary,
        'secondary_contributors': secondary,
        'contracts': {
            'passed': not failures,
            'failures': failures,
            'warnings': warnings,
        },
    }


def audit_translation_mirrored_asymmetry_files(*, seed_profiles_path: str | Path, decomposition_path: str | Path) -> dict[str, Any]:
    return audit_translation_mirrored_asymmetry(
        seed_profiles_payload=_load_json(seed_profiles_path),
        decomposition_payload=_load_json(decomposition_path),
    )
