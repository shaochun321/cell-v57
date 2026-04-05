from __future__ import annotations

from pathlib import Path
from typing import Any
import json

TRANSLATION_CASES = {
    'translation_x_pos': 1.0,
    'translation_x_neg': -1.0,
}


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _sign_matches(value: float, expected: float, *, eps: float = 1e-12) -> bool:
    if abs(value) < eps:
        return False
    return (value > 0.0) == (expected > 0.0)


def _case_summary_path(report_path: str | Path, case_name: str) -> Path:
    return Path(report_path).resolve().parent / case_name / 'summary.json'


def _active_x_summary(case_analysis: dict[str, Any]) -> dict[str, Any]:
    return dict(case_analysis.get('phase_summaries', {}).get('active', {}).get('axis_summaries', {}).get('x', {}))


def audit_translation_shell_to_atlas_handoff(repeatability_report: dict[str, Any]) -> dict[str, Any]:
    seeds = [int(s) for s in repeatability_report.get('seeds', [])]
    seed_runs = list(repeatability_report.get('seed_runs', []))
    if not seeds:
        seeds = [int(run.get('seed', 0)) for run in seed_runs]
    reference_seed = seeds[0] if seeds else 0

    per_seed: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []
    evidence = {
        'family_wide_raw_sign_inversion': False,
        'shell_interface_outer_shift_detected': False,
        'interface_translation_survives_detected': False,
        'atlas_pair_collapse_detected': False,
        'shell_to_atlas_handoff_loss_detected': False,
    }

    for run in seed_runs:
        seed = int(run.get('seed', 0))
        analysis = _load_json(run['analysis_path'])
        row: dict[str, Any] = {'seed': seed, 'cases': {}}
        family_raw_inversion = True
        family_outer_shift = True
        family_interface_translation_survives = True
        family_pair_collapse = True
        family_handoff_loss = True

        for case_name, expected_sign in TRANSLATION_CASES.items():
            summary = _load_json(_case_summary_path(run['report_path'], case_name))
            case_analysis = dict(analysis.get('cases', {}).get(case_name, {}))
            active_x = _active_x_summary(case_analysis)
            active_interface = dict(summary.get('mirror_interface_diagnostics', {}).get('active_summary', {}))
            axial_family = dict(
                summary.get('interface_temporal_diagnostics', {})
                .get('tracks', {})
                .get('discrete_channel_track', {})
                .get('families', {})
                .get('axial_polar_family', {})
            )

            raw_pol = float(active_x.get('mean_polarity_projection', 0.0))
            raw_sign_ok = _sign_matches(raw_pol, expected_sign)
            interface_class = str(active_interface.get('dominant_interface_class', 'unknown'))
            interface_translation_survives = interface_class == 'translation'

            inner_level = float(axial_family.get('mean_inner_level', 0.0))
            outer_level = float(axial_family.get('mean_outer_level', 0.0))
            outer_inner_ratio = float(axial_family.get('mean_outer_inner_ratio', 0.0))
            peak_shell = float(axial_family.get('mean_peak_shell_index', -1.0))
            outer_shift = outer_inner_ratio > 4.0 and peak_shell >= 1.5

            sp = dict(active_x.get('strongest_pair', {}))
            sp_mode = str(sp.get('dominant_mode', 'mixed'))
            sp_axis = str(sp.get('dominant_axis', 'none'))
            sp_scores = dict(sp.get('mode_scores', {}))
            sp_translation = float(sp_scores.get('translation_like', 0.0))
            sp_static = float(sp_scores.get('static_like', 0.0))
            sp_margin = sp_translation - sp_static
            pair_collapse = (sp_mode != 'translation_like') or (sp_axis != 'x') or (sp_margin <= 0.0)

            handoff_loss = interface_translation_survives and pair_collapse

            family_raw_inversion = family_raw_inversion and (not raw_sign_ok)
            family_outer_shift = family_outer_shift and outer_shift
            family_interface_translation_survives = family_interface_translation_survives and interface_translation_survives
            family_pair_collapse = family_pair_collapse and pair_collapse
            family_handoff_loss = family_handoff_loss and handoff_loss

            row['cases'][case_name] = {
                'expected_sign': expected_sign,
                'raw_mean_polarity_projection': raw_pol,
                'raw_sign_ok': raw_sign_ok,
                'interface_dominant_class': interface_class,
                'interface_translation_survives': interface_translation_survives,
                'interface_translation_channel': float(active_interface.get('mean_translation_channel', 0.0)),
                'interface_rotation_channel': float(active_interface.get('mean_rotation_channel', 0.0)),
                'interface_margin': float(active_interface.get('mean_interface_margin', 0.0)),
                'axial_family_inner_level': inner_level,
                'axial_family_outer_level': outer_level,
                'axial_family_outer_inner_ratio': outer_inner_ratio,
                'axial_family_peak_shell_index': peak_shell,
                'outer_shift_detected': outer_shift,
                'atlas_strongest_shell': int(active_x.get('strongest_shell', -1)),
                'atlas_strongest_pair_shell': int(sp.get('shell_index', -1)),
                'atlas_strongest_pair_mode': sp_mode,
                'atlas_strongest_pair_axis': sp_axis,
                'atlas_translation_score': sp_translation,
                'atlas_static_score': sp_static,
                'atlas_translation_margin': sp_margin,
                'atlas_pair_collapse': pair_collapse,
                'shell_to_atlas_handoff_loss': handoff_loss,
            }

        row['family_raw_inversion'] = family_raw_inversion
        row['family_shell_interface_outer_shift'] = family_outer_shift
        row['family_interface_translation_survives'] = family_interface_translation_survives
        row['family_atlas_pair_collapse'] = family_pair_collapse
        row['family_shell_to_atlas_handoff_loss'] = family_handoff_loss
        per_seed.append(row)

    evidence['family_wide_raw_sign_inversion'] = any(r['family_raw_inversion'] for r in per_seed)
    evidence['shell_interface_outer_shift_detected'] = any(r['family_shell_interface_outer_shift'] for r in per_seed)
    evidence['interface_translation_survives_detected'] = any(r['family_interface_translation_survives'] for r in per_seed)
    evidence['atlas_pair_collapse_detected'] = any(r['family_atlas_pair_collapse'] for r in per_seed)
    evidence['shell_to_atlas_handoff_loss_detected'] = any(r['family_shell_to_atlas_handoff_loss'] for r in per_seed)

    if (
        evidence['family_wide_raw_sign_inversion']
        and evidence['shell_interface_outer_shift_detected']
        and evidence['interface_translation_survives_detected']
        and evidence['atlas_pair_collapse_detected']
        and evidence['shell_to_atlas_handoff_loss_detected']
    ):
        primary = 'shell_to_atlas_handoff_loss'
        secondary = ['shell_interface_redistribution', 'atlas_pair_formation_collapse']
        warnings.append(
            'translation remains translation-dominant at the interface-family layer after outward shift, but the handoff into the strongest atlas x-pair collapses to static-like'
        )
    elif evidence['family_wide_raw_sign_inversion'] and evidence['shell_interface_outer_shift_detected']:
        primary = 'shell_interface_redistribution'
        secondary = []
    else:
        primary = 'undetermined'
        secondary = []
        failures.append('unable to localize translation failure to the shell-to-atlas handoff with current repeatability payload')

    return {
        'suite': 'process_summary_translation_shell_to_atlas_handoff_audit',
        'seeds': seeds,
        'reference_seed': reference_seed,
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


def audit_translation_shell_to_atlas_handoff_files(*, repeatability_report_path: str | Path) -> dict[str, Any]:
    return audit_translation_shell_to_atlas_handoff(_load_json(repeatability_report_path))
