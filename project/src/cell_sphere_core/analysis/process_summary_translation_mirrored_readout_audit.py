from __future__ import annotations

from pathlib import Path
from typing import Any
import json

TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def summarize_active_x_shell_profiles(trace: list[dict[str, Any]]) -> dict[str, Any]:
    by_shell: dict[int, dict[str, list[float] | list[str]]] = {}
    for window in trace:
        if str(window.get('phase', 'baseline')) != 'active':
            continue
        for pair in list(window.get('pair_summaries', [])):
            if str(pair.get('axis', 'none')) != 'x':
                continue
            shell = int(pair.get('shell_index', -1))
            rec = by_shell.setdefault(shell, {
                'pair_strength': [],
                'translation_score': [],
                'static_score': [],
                'rotation_score': [],
                'polarity_signed': [],
                'axial_flux': [],
                'transfer_potential': [],
                'dominant_mode': [],
            })
            rec['pair_strength'].append(float(pair.get('pair_strength', 0.0)))
            rec['translation_score'].append(float(pair.get('mode_scores', {}).get('translation_like', 0.0)))
            rec['static_score'].append(float(pair.get('mode_scores', {}).get('static_like', 0.0)))
            rec['rotation_score'].append(float(pair.get('mode_scores', {}).get('rotation_like', 0.0)))
            rec['polarity_signed'].append(float(pair.get('differential_channels', {}).get('polarity_projection', 0.0)))
            rec['axial_flux'].append(float(pair.get('symmetric_channels', {}).get('axial_flux', 0.0)))
            rec['transfer_potential'].append(float(pair.get('symmetric_channels', {}).get('transfer_potential', 0.0)))
            rec['dominant_mode'].append(str(pair.get('dominant_mode', 'mixed')))

    shell_profiles: dict[str, Any] = {}
    for shell in sorted(by_shell):
        rec = by_shell[shell]
        polarity_signed = [float(v) for v in rec['polarity_signed']]
        polarity_abs = [abs(v) for v in polarity_signed]
        dom_counts: dict[str, int] = {}
        for name in rec['dominant_mode']:
            dom_counts[name] = dom_counts.get(name, 0) + 1
        dominant_mode = max(dom_counts.items(), key=lambda kv: kv[1])[0] if dom_counts else 'mixed'
        profile = {
            'shell_index': int(shell),
            'pair_strength': _mean([float(v) for v in rec['pair_strength']]),
            'translation_score': _mean([float(v) for v in rec['translation_score']]),
            'static_score': _mean([float(v) for v in rec['static_score']]),
            'rotation_score': _mean([float(v) for v in rec['rotation_score']]),
            'polarity_signed': _mean(polarity_signed),
            'polarity_abs': _mean(polarity_abs),
            'axial_flux': _mean([float(v) for v in rec['axial_flux']]),
            'transfer_potential': _mean([float(v) for v in rec['transfer_potential']]),
            'dominant_mode': dominant_mode,
        }
        profile['translation_mass_proxy'] = float(profile['translation_score'] + profile['polarity_abs'] + profile['axial_flux'])
        profile['static_mass_proxy'] = float(profile['static_score'] + profile['transfer_potential'])
        shell_profiles[str(shell)] = profile

    if not shell_profiles:
        return {
            'shell_profiles': {},
            'strongest_shell_by_pair_strength': -1,
            'strongest_shell_by_translation_mass': -1,
            'inner_translation_share': 0.0,
            'outer_translation_share': 0.0,
            'outer_shell_threshold': -1,
        }

    shell_ids = [int(k) for k in shell_profiles.keys()]
    inner_shell = min(shell_ids)
    max_shell = max(shell_ids)
    outer_threshold = max(1, (max_shell + 1) // 2)
    total_translation_mass = sum(float(v['translation_mass_proxy']) for v in shell_profiles.values())
    if total_translation_mass <= 1e-12:
        inner_share = 0.0
        outer_share = 0.0
    else:
        inner_share = float(shell_profiles[str(inner_shell)]['translation_mass_proxy'] / total_translation_mass)
        outer_share = float(sum(float(v['translation_mass_proxy']) for k, v in shell_profiles.items() if int(k) >= outer_threshold) / total_translation_mass)

    strongest_shell_by_pair = max(shell_profiles.values(), key=lambda row: float(row['pair_strength']))['shell_index']
    strongest_shell_by_mass = max(shell_profiles.values(), key=lambda row: float(row['translation_mass_proxy']))['shell_index']
    return {
        'shell_profiles': shell_profiles,
        'strongest_shell_by_pair_strength': int(strongest_shell_by_pair),
        'strongest_shell_by_translation_mass': int(strongest_shell_by_mass),
        'inner_translation_share': inner_share,
        'outer_translation_share': outer_share,
        'outer_shell_threshold': int(outer_threshold),
    }


def summarize_active_x_shell_profiles_from_file(trace_path: str | Path) -> dict[str, Any]:
    return summarize_active_x_shell_profiles(_load_json(trace_path))


def audit_translation_mirrored_readout(seed_profiles_payload: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in seed_profiles_payload.get('seeds', [])]
    reference_seed = int(seed_profiles_payload.get('reference_seed', seeds[0] if seeds else 0))
    cases_payload = dict(seed_profiles_payload.get('cases', {}))

    reference_inner_shares = {
        case: float(dict(cases_payload.get(case, {})).get(str(reference_seed), {}).get('inner_translation_share', 0.0))
        for case in TRANSLATION_CASES
    }

    evidence = {
        'family_wide_raw_sign_inversion': False,
        'translation_mass_relocation_detected': False,
        'pair_weighting_disagreement_detected': False,
        'outer_shell_mode_collapse_detected': False,
    }
    per_seed: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    for seed in seeds:
        seed_row: dict[str, Any] = {'seed': seed, 'cases': {}}
        family_raw_inversion = True
        family_mass_relocation = True
        family_pair_weighting_disagreement = False
        family_outer_mode_collapse = False
        for case_name, expected_sign in TRANSLATION_CASES.items():
            case_seed = dict(cases_payload.get(case_name, {})).get(str(seed), {})
            shell_profiles = dict(case_seed.get('shell_profiles', {}))
            raw_signal = float(case_seed.get('mean_polarity_projection', 0.0))
            sign_ok = raw_signal * expected_sign > 0.0
            inner_share = float(case_seed.get('inner_translation_share', 0.0))
            outer_share = float(case_seed.get('outer_translation_share', 0.0))
            strongest_shell_by_pair = int(case_seed.get('strongest_shell_by_pair_strength', -1))
            strongest_shell_by_mass = int(case_seed.get('strongest_shell_by_translation_mass', -1))
            pair_weighting_disagreement = strongest_shell_by_pair != strongest_shell_by_mass
            strongest_mass_profile = dict(shell_profiles.get(str(strongest_shell_by_mass), {}))
            strongest_mass_mode = str(strongest_mass_profile.get('dominant_mode', 'mixed'))
            outer_mode_collapse = strongest_mass_mode != 'translation_like'
            reference_inner_share = reference_inner_shares.get(case_name, 0.0)
            mass_relocation = (inner_share < max(0.5 * reference_inner_share, 0.20)) and (outer_share > 0.60)

            family_raw_inversion = family_raw_inversion and (not sign_ok)
            family_mass_relocation = family_mass_relocation and mass_relocation
            family_pair_weighting_disagreement = family_pair_weighting_disagreement or pair_weighting_disagreement
            family_outer_mode_collapse = family_outer_mode_collapse or outer_mode_collapse

            seed_row['cases'][case_name] = {
                'expected_sign': expected_sign,
                'mean_polarity_projection': raw_signal,
                'raw_sign_ok': sign_ok,
                'reference_inner_translation_share': reference_inner_share,
                'inner_translation_share': inner_share,
                'outer_translation_share': outer_share,
                'strongest_shell_by_pair_strength': strongest_shell_by_pair,
                'strongest_shell_by_translation_mass': strongest_shell_by_mass,
                'pair_weighting_disagreement': pair_weighting_disagreement,
                'strongest_mass_mode': strongest_mass_mode,
                'outer_mode_collapse': outer_mode_collapse,
                'mass_relocation_detected': mass_relocation,
                'shell_profiles': shell_profiles,
            }
        seed_row['family_raw_inversion'] = family_raw_inversion
        seed_row['family_mass_relocation'] = family_mass_relocation
        seed_row['family_pair_weighting_disagreement'] = family_pair_weighting_disagreement
        seed_row['family_outer_mode_collapse'] = family_outer_mode_collapse
        per_seed.append(seed_row)

    evidence['family_wide_raw_sign_inversion'] = any(r['family_raw_inversion'] for r in per_seed)
    evidence['translation_mass_relocation_detected'] = any(r['family_mass_relocation'] for r in per_seed)
    evidence['pair_weighting_disagreement_detected'] = any(r['family_pair_weighting_disagreement'] for r in per_seed)
    evidence['outer_shell_mode_collapse_detected'] = any(r['family_outer_mode_collapse'] for r in per_seed)

    if evidence['family_wide_raw_sign_inversion'] and evidence['translation_mass_relocation_detected']:
        primary = 'translation_signal_mass_relocation'
        secondary = []
        if evidence['pair_weighting_disagreement_detected']:
            secondary.append('pair_channel_weighting')
        if evidence['outer_shell_mode_collapse_detected']:
            secondary.append('outer_shell_translation_mode_collapse')
        warnings.append('translation raw sign inversion follows a strong inner-to-outer shift in translation-mass proxy, so pair weighting alone is not the primary driver')
    elif evidence['family_wide_raw_sign_inversion'] and evidence['pair_weighting_disagreement_detected']:
        primary = 'pair_channel_weighting'
        secondary = []
    else:
        primary = 'undetermined'
        secondary = []
        failures.append('unable to distinguish translation signal-mass relocation from pair weighting with current mirrored readout profiles')

    return {
        'suite': 'process_summary_translation_mirrored_readout_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
        'reference_inner_translation_shares': reference_inner_shares,
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


def audit_translation_mirrored_readout_files(*, seed_profiles_path: str | Path) -> dict[str, Any]:
    return audit_translation_mirrored_readout(_load_json(seed_profiles_path))
