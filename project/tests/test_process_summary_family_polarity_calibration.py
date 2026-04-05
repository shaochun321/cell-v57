from __future__ import annotations

from cell_sphere_core.analysis.process_summary_family_polarity_calibration import summarize_family_polarity_calibration


def _make_case(seed: int, *, mode='translation_like', axis='x', x_pol=0.1, z_circ=0.05):
    return {
        'seed': seed,
        'dominant_mode': mode,
        'active_dominant_mode': mode,
        'active_dominant_axis': axis,
        'phase_summaries': {
            'active': {
                'axis_summaries': {
                    'x': {
                        'mean_polarity_projection': x_pol,
                        'mean_circulation_projection': 0.0,
                        'support_scores': {'translation_like': 0.2, 'rotation_like': 0.1, 'static_like': 0.1},
                    },
                    'y': {
                        'mean_polarity_projection': 0.0,
                        'mean_circulation_projection': 0.0,
                        'support_scores': {'translation_like': 0.1, 'rotation_like': 0.1, 'static_like': 0.1},
                    },
                    'z': {
                        'mean_polarity_projection': 0.0,
                        'mean_circulation_projection': z_circ,
                        'support_scores': {'translation_like': 0.1, 'rotation_like': 0.2, 'static_like': 0.1},
                    },
                }
            }
        }
    }


def test_family_polarity_calibration_corrects_global_translation_sign_flip() -> None:
    report = {
        'metadata': {},
        'seed_runs': [
            {'seed': 7, 'analysis': {'cases': {
                'translation_x_pos': _make_case(7, x_pol=0.17),
                'translation_x_neg': _make_case(7, x_pol=-0.18),
                'rotation_z_pos': _make_case(7, mode='rotation_like', axis='z', x_pol=0.0, z_circ=0.05),
                'rotation_z_neg': _make_case(7, mode='rotation_like', axis='z', x_pol=0.0, z_circ=-0.05),
            }}},
            {'seed': 8, 'analysis': {'cases': {
                'translation_x_pos': _make_case(8, x_pol=-0.02),
                'translation_x_neg': _make_case(8, x_pol=0.06),
                'rotation_z_pos': _make_case(8, mode='rotation_like', axis='z', x_pol=0.0, z_circ=0.04),
                'rotation_z_neg': _make_case(8, mode='rotation_like', axis='z', x_pol=0.0, z_circ=-0.04),
            }}}]
    }
    consensus = {
        'families': {
            'translation': {'family_mode_stable': True},
            'rotation': {'family_mode_stable': True},
        },
        'cases': {
            'translation_x_pos': {'consensus_axis': 'x', 'consensus_mode': 'translation_like'},
            'translation_x_neg': {'consensus_axis': 'x', 'consensus_mode': 'translation_like'},
            'rotation_z_pos': {'consensus_axis': 'z', 'consensus_mode': 'rotation_like'},
            'rotation_z_neg': {'consensus_axis': 'z', 'consensus_mode': 'rotation_like'},
        }
    }
    payload = summarize_family_polarity_calibration(report, consensus)
    assert payload['contracts']['passed'] is True
    assert payload['families']['translation']['raw_sign_fraction'] == 0.5
    assert payload['families']['translation']['calibrated_sign_fraction'] == 1.0
    assert payload['cases']['translation_x_pos']['sign_calibration_fixed'] is True
    assert payload['cases']['translation_x_neg']['sign_calibration_fixed'] is True
    assert payload['families']['rotation']['calibrated_sign_fraction'] == 1.0
