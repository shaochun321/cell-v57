from __future__ import annotations

from cell_sphere_core.analysis.phase_r5 import summarize_phase_r5_audit


def _repeat(score: float, seed: int) -> dict:
    swirl_margin = max(0.0, min(0.3, score - 0.70))
    sign_scale = max(0.0, min(1.0, (score - 0.70) / 0.25))
    return {
        'repeat_id': f'r{seed}',
        'rng_seed': seed,
        'rotation_pos': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {'swirl_circulation_family': 0.12 + swirl_margin, 'axial_polar_family': 0.18},
                'active_signed_circulation': 0.002 * sign_scale,
            }}}
        },
        'rotation_neg': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {'swirl_circulation_family': 0.11 + swirl_margin, 'axial_polar_family': 0.18},
                'active_signed_circulation': -0.0018 * sign_scale,
            }}}
        },
    }


def test_phase_r5_repeatability_summary_prefers_stable_patch() -> None:
    report = {
        'metadata': {'rotation_alphas': [300, 320], 'swirl_gains': [1.05, 1.10], 'seeds': [7, 8, 9]},
        'translation_guard': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {'axial_polar_family': 0.35, 'swirl_circulation_family': 0.18},
                'active_axis_balance': {'x': 0.03},
            }}}
        },
        'rotation_scan': [
            {'case_id': 'a300_g105', 'rotation_alpha': 300, 'swirl_gain': 1.05, 'repeats': [_repeat(0.90, 7), _repeat(0.91, 8), _repeat(0.90, 9)]},
            {'case_id': 'a300_g110', 'rotation_alpha': 300, 'swirl_gain': 1.10, 'repeats': [_repeat(0.89, 7), _repeat(0.90, 8), _repeat(0.88, 9)]},
            {'case_id': 'a320_g105', 'rotation_alpha': 320, 'swirl_gain': 1.05, 'repeats': [_repeat(0.84, 7), _repeat(0.88, 8), _repeat(0.79, 9)]},
            {'case_id': 'a320_g110', 'rotation_alpha': 320, 'swirl_gain': 1.10, 'repeats': [_repeat(0.83, 7), _repeat(0.84, 8), _repeat(0.82, 9)]},
        ],
    }
    audit = summarize_phase_r5_audit(report)
    assert audit['best_config']['case_id'] in {'a300_g105', 'a300_g110', 'a320_g105', 'a320_g110'}
    assert audit['best_config']['repeatability_score'] > 0.85
    assert audit['local_repeatability_plateau']['plateau_score'] > 0.8
