from __future__ import annotations

from cell_sphere_core.analysis.mirror_channel_atlas import _push_pull_decompose, _shell_to_atlas_handoff_gate
from cell_sphere_core.analysis.mirror_shell_interface import _infer_directional_partition


def test_directional_partition_assigns_axis_and_domain() -> None:
    part_pos = _infer_directional_partition(sector='x_pos')
    part_neg = _infer_directional_partition(sector='x_neg')
    assert part_pos.preferred_axis == 'x'
    assert part_pos.polarity_domain == 'plus'
    assert part_neg.preferred_axis == 'x'
    assert part_neg.polarity_domain == 'minus'


def test_push_pull_decompose_separates_common_and_differential_modes() -> None:
    pos = {'polarity_projection': 0.6, 'axial_flux': 0.9, 'swirl_flux': 0.1}
    neg = {'polarity_projection': -0.2, 'axial_flux': 0.5, 'swirl_flux': 0.1}
    # pad minimal required keys used by decomposition caller contract
    for payload in (pos, neg):
        for key in (
            'deformation_drive', 'vibration_drive', 'event_flux', 'dissipation_load',
            'circulation_projection', 'transfer_potential'
        ):
            payload.setdefault(key, 0.0)
    common, diff = _push_pull_decompose(pos, neg)
    assert common['axial_flux'] == 0.7
    assert abs(diff['polarity_projection'] - 0.8) < 1e-9


def test_shell_to_atlas_handoff_gate_penalizes_cross_axis_and_cross_domain_mismatch() -> None:
    good_pos = {
        'preferred_axis': 'x', 'polarity_domain': 'plus', 'boundary_distance': 1.0,
        'axis_alignment_score': 0.9, 'polarity_domain_score': 0.8,
    }
    good_neg = {
        'preferred_axis': 'x', 'polarity_domain': 'minus', 'boundary_distance': 1.0,
        'axis_alignment_score': 0.85, 'polarity_domain_score': 0.75,
    }
    bad_pos = {
        'preferred_axis': 'y', 'polarity_domain': 'minus', 'boundary_distance': 0.1,
        'axis_alignment_score': 0.1, 'polarity_domain_score': 0.1,
    }
    bad_neg = {
        'preferred_axis': 'y', 'polarity_domain': 'plus', 'boundary_distance': 0.1,
        'axis_alignment_score': 0.1, 'polarity_domain_score': 0.1,
    }
    good = _shell_to_atlas_handoff_gate(pos_unit=good_pos, neg_unit=good_neg, target_axis='x')
    bad = _shell_to_atlas_handoff_gate(pos_unit=bad_pos, neg_unit=bad_neg, target_axis='x')
    assert good['handoff_gate_score'] > bad['handoff_gate_score']
    assert good['cross_axis_leakage'] < bad['cross_axis_leakage']
    assert good['cross_domain_leakage'] < bad['cross_domain_leakage']
    assert good['pair_gate_passed'] is True
