from __future__ import annotations

from cell_sphere_core.analysis.phase_r4 import summarize_phase_r4_audit


def _case(alpha: float, gain: float, score: float) -> dict:
    # score is mapped into swirl dominance and sign quality so the summary can distinguish strong and weak frontier bands.
    swirl_margin = max(0.0, min(0.3, score - 0.75))
    sign_scale = max(0.0, min(1.0, (score - 0.75) / 0.20))
    pos_circ = 0.0025 * sign_scale
    neg_circ = -0.0022 * sign_scale
    return {
        'rotation_alpha': alpha,
        'swirl_gain': gain,
        'rotation_pos': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {
                    'swirl_circulation_family': 0.10 + swirl_margin,
                    'axial_polar_family': 0.18,
                },
                'active_signed_circulation': pos_circ,
            }}}
        },
        'rotation_neg': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {
                    'swirl_circulation_family': 0.09 + swirl_margin,
                    'axial_polar_family': 0.18,
                },
                'active_signed_circulation': neg_circ,
            }}}
        },
    }


def test_phase_r4_detects_continuing_boundary_band() -> None:
    report = {
        'metadata': {'rotation_alphas': [300, 340, 380], 'swirl_gains': [1.0, 1.1, 1.2], 'frontier_direction': 'lower_alpha'},
        'translation_guard': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {'axial_polar_family': 0.34, 'swirl_circulation_family': 0.18},
                'active_axis_balance': {'x': 0.02},
            }}}
        },
        'rotation_scan': [
            _case(300, 1.0, 0.95), _case(300, 1.1, 0.95), _case(300, 1.2, 0.95),
            _case(340, 1.0, 0.94), _case(340, 1.1, 0.94), _case(340, 1.2, 0.94),
            _case(380, 1.0, 0.88), _case(380, 1.1, 0.88), _case(380, 1.2, 0.88),
        ],
    }
    audit = summarize_phase_r4_audit(report)
    ext = audit['directional_extension']
    assert ext['status'] == 'continues'
    assert ext['direction'] == 'lower_alpha'
    assert ext['frontier_mean'] >= ext['anchor_mean'] - 0.01


def test_phase_r4_detects_rolloff_at_frontier() -> None:
    report = {
        'metadata': {'rotation_alphas': [300, 340, 380], 'swirl_gains': [1.0, 1.1, 1.2, 1.3], 'frontier_direction': 'lower_alpha'},
        'translation_guard': {
            'motif_report': {'tracks': {'layered_coupling_track': {
                'active_family_means': {'axial_polar_family': 0.34, 'swirl_circulation_family': 0.18},
                'active_axis_balance': {'x': 0.02},
            }}}
        },
        'rotation_scan': [
            _case(300, 1.0, 0.94), _case(300, 1.1, 0.78), _case(300, 1.2, 0.77), _case(300, 1.3, 0.77),
            _case(340, 1.0, 0.93), _case(340, 1.1, 0.94), _case(340, 1.2, 0.93), _case(340, 1.3, 0.94),
            _case(380, 1.0, 0.94), _case(380, 1.1, 0.94), _case(380, 1.2, 0.94), _case(380, 1.3, 0.94),
        ],
    }
    audit = summarize_phase_r4_audit(report)
    ext = audit['directional_extension']
    assert ext['status'] == 'degrades'
    assert ext['frontier_mean'] < ext['anchor_mean']
