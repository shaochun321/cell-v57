from __future__ import annotations

from pathlib import Path
from typing import Any
import json

EXPECTED_SIGNS = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _float(v: Any) -> float:
    return float(v)


def _sign_matches(value: float, expected: float, *, eps: float = 1e-12) -> bool:
    if abs(value) < eps:
        return False
    return (value > 0.0) == (expected > 0.0)


def audit_translation_mirrored_carrier_geometry(*, seed_profiles_payload: dict[str, Any], decomposition_payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    seeds = [int(s) for s in seed_profiles_payload.get('seeds', [])]
    reference_seed = int(seed_profiles_payload.get('reference_seed', seeds[0] if seeds else 0))
    cases = seed_profiles_payload.get('cases', {})
    decomp_rows = {int(r['seed']): r for r in decomposition_payload.get('per_seed', [])}
    seed8 = decomp_rows.get(8)

    if not {'translation_x_pos', 'translation_x_neg'}.issubset(cases):
        failures.append('missing translation_x_pos or translation_x_neg seed profiles')
    if seed8 is None:
        failures.append('missing seed 8 decomposition row required for mirrored carrier geometry audit')

    per_case: dict[str, Any] = {}
    evidence = {
        'x_pos_pair_orientation_bias_detected': False,
        'x_neg_polarity_basis_asymmetry_detected': False,
        'mirrored_failure_modes_split_detected': False,
        'common_single_geometry_mechanism_rejected': False,
    }

    if not failures:
        failure_modes: dict[str, str] = {}
        for case_name, expected_sign in EXPECTED_SIGNS.items():
            ref = cases[case_name][str(reference_seed)]
            cmp = cases[case_name]['8']
            cmp_pair_shell = str(cmp['strongest_shell_by_pair_strength'])
            cmp_pair = cmp['shell_profiles'][cmp_pair_shell]
            ref_pair_shell = str(ref['strongest_shell_by_pair_strength'])
            ref_pair = ref['shell_profiles'][ref_pair_shell]
            failure_mode = seed8['cases'][case_name]['dominant_failure_mode']
            failure_modes[case_name] = failure_mode
            cmp_sign_ok = _sign_matches(_float(cmp_pair['polarity_signed']), expected_sign)
            ref_sign_ok = _sign_matches(_float(ref_pair['polarity_signed']), expected_sign)
            cmp_translation_minus_static = _float(cmp_pair['translation_score']) - _float(cmp_pair['static_score'])
            ref_translation_minus_static = _float(ref_pair['translation_score']) - _float(ref_pair['static_score'])

            orientation_bias = failure_mode in {'x_axis_competition_override', 'axis_competition_override'}
            polarity_basis_asym = failure_mode in {'polarity_projection_inversion', 'weak_polarity_projection'} and (not cmp_sign_ok)

            if case_name == 'translation_x_pos':
                evidence['x_pos_pair_orientation_bias_detected'] = orientation_bias
            else:
                evidence['x_neg_polarity_basis_asymmetry_detected'] = polarity_basis_asym

            per_case[case_name] = {
                'reference_seed': reference_seed,
                'comparison_seed': 8,
                'dominant_failure_mode_cmp': failure_mode,
                'reference_pair_shell': int(ref_pair_shell),
                'comparison_pair_shell': int(cmp_pair_shell),
                'reference_pair_translation_minus_static': ref_translation_minus_static,
                'comparison_pair_translation_minus_static': cmp_translation_minus_static,
                'reference_pair_polarity_signed': _float(ref_pair['polarity_signed']),
                'comparison_pair_polarity_signed': _float(cmp_pair['polarity_signed']),
                'reference_pair_sign_ok': ref_sign_ok,
                'comparison_pair_sign_ok': cmp_sign_ok,
                'pair_orientation_bias_detected': orientation_bias,
                'polarity_basis_asymmetry_detected': polarity_basis_asym,
            }

        evidence['mirrored_failure_modes_split_detected'] = failure_modes['translation_x_pos'] != failure_modes['translation_x_neg']
        evidence['common_single_geometry_mechanism_rejected'] = evidence['x_pos_pair_orientation_bias_detected'] and evidence['x_neg_polarity_basis_asymmetry_detected']

        if evidence['common_single_geometry_mechanism_rejected']:
            primary = 'mirrored_geometry_bias_decomposes_into_pair_orientation_and_polarity_basis_asymmetry'
            secondary = ['shared_shell_to_carrier_outward_shift']
            warnings.append(
                'translation_x_pos fails mainly by pair-orientation bias after the shared outer shift, while translation_x_neg preserves x dominance but fails by polarity-basis asymmetry; mirrored carrier geometry bias therefore decomposes into two post-shift mechanisms rather than one common geometry fault'
            )
        elif evidence['x_pos_pair_orientation_bias_detected']:
            primary = 'pair_orientation_bias'
            secondary = []
        elif evidence['x_neg_polarity_basis_asymmetry_detected']:
            primary = 'polarity_basis_mirror_asymmetry'
            secondary = []
        else:
            primary = 'undetermined'
            secondary = []
            failures.append('unable to distinguish pair-orientation bias from polarity-basis asymmetry')
    else:
        primary = 'undetermined'
        secondary = []

    return {
        'suite': 'process_summary_translation_mirrored_carrier_geometry_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
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


def audit_translation_mirrored_carrier_geometry_files(*, seed_profiles_path: str | Path, decomposition_path: str | Path) -> dict[str, Any]:
    return audit_translation_mirrored_carrier_geometry(
        seed_profiles_payload=_load_json(seed_profiles_path),
        decomposition_payload=_load_json(decomposition_path),
    )
