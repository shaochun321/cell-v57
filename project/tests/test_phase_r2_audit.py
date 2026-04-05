from __future__ import annotations

from cell_sphere_core.analysis.phase_r2 import summarize_phase_r2_audit


def _case(swirl: float, axial: float, circ: float) -> dict:
    return {
        'motif_report': {
            'tracks': {
                'layered_coupling_track': {
                    'active_family_means': {
                        'swirl_circulation_family': swirl,
                        'axial_polar_family': axial,
                    },
                    'active_signed_circulation': circ,
                    'active_axis_balance': {'x': 0.4},
                }
            }
        }
    }


def test_phase_r2_audit_identifies_best_rotation_region_and_translation_guard():
    report = {
        'metadata': {'rotation_alphas': [420.0, 500.0], 'swirl_gains': [1.0, 1.2]},
        'translation_guard': _case(swirl=0.20, axial=0.45, circ=0.01),
        'rotation_scan': [
            {
                'case_id': 'weak',
                'rotation_alpha': 420.0,
                'swirl_gain': 1.0,
                'circulation_gain': 1.10,
                'axial_base': 0.90,
                'transfer_base': 0.96,
                'circulation_feed': 0.18,
                'rotation_pos': _case(swirl=0.30, axial=0.28, circ=0.08),
                'rotation_neg': _case(swirl=0.29, axial=0.27, circ=-0.05),
            },
            {
                'case_id': 'strong',
                'rotation_alpha': 500.0,
                'swirl_gain': 1.2,
                'circulation_gain': 1.14,
                'axial_base': 0.86,
                'transfer_base': 0.98,
                'circulation_feed': 0.20,
                'rotation_pos': _case(swirl=0.44, axial=0.24, circ=0.19),
                'rotation_neg': _case(swirl=0.42, axial=0.23, circ=-0.18),
            },
        ],
    }
    audit = summarize_phase_r2_audit(report)
    assert audit['best_config']['case_id'] == 'strong'
    assert audit['best_config']['rotation_score'] > audit['worst_config']['rotation_score']
    assert audit['translation_guard']['translation_guard_score'] >= 0.75
    assert audit['overall']['num_scan_points'] == 2
    assert '500.000' in audit['heatmap']
    assert 'local_robustness' in audit
    assert audit['local_robustness']['neighbor_count'] >= 1
    assert 0.0 <= audit['local_robustness']['stable_region_score'] <= 1.0
