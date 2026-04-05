from scripts.analyze_stage1_global_overview_farther_scale_n192_bidirectional_rotation_veto_candidate import FIXED_THRESHOLD, replay_rows


def test_bidirectional_rotation_veto_relabels_high_curl_translation_to_rotation() -> None:
    rows = [
        {
            'label': 'rotation_z_pos',
            'predicted': 'translation_x_pos',
            'stage1_predicted': 'translation',
            'generalized_veto_feature': FIXED_THRESHOLD + 0.5,
            'seed': 11,
            'case_name': 'rotation_z_pos_early_soft',
        },
        {
            'label': 'translation_x_pos',
            'predicted': 'translation_x_pos',
            'stage1_predicted': 'translation',
            'generalized_veto_feature': FIXED_THRESHOLD - 0.5,
            'seed': 11,
            'case_name': 'translation_x_pos_early_soft',
        },
    ]

    result = replay_rows(rows, FIXED_THRESHOLD)
    assert result['accuracy'] == 1.0
    assert result['predictions'][0]['predicted'] == 'rotation_z_pos'
    assert result['predictions'][0]['bidirectional_veto_triggered'] is True
    assert result['predictions'][1]['predicted'] == 'translation_x_pos'
    assert result['predictions'][1]['bidirectional_veto_triggered'] is False
