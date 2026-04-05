from __future__ import annotations

import json
from pathlib import Path

BASE = Path('/mnt/data')
PHASE2 = json.loads((BASE / 'stage1_global_overview_farther_scale_n288_harder_target_seedexp_phase2_fixed_v53_stack_candidate_analysis.json').read_text())
BROADER = json.loads((BASE / 'stage1_global_overview_farther_scale_n288_harder_target_seedexp_broader_fixed_v52_stack_candidate_analysis.json').read_text())
THRESHOLD = 3.8

seen = PHASE2['seen_eval']['predictions']
pos = [r for r in seen if r['label'] == 'translation_x_pos' and r['profile'] == 'mid_sharp']
rot = [r for r in seen if r['label'] == 'rotation_z_pos' and r['profile'] == 'mid_sharp']

analysis = {
    'protocol': 'stage1_global_overview_farther_scale_n288_harder_phase2_positive_guard_overreach_candidate_definition_audit',
    'candidate': {
        'name': 'positive_guard_overreach_restore',
        'restore_curl_floor': THRESHOLD,
    },
    'broader_target_restore_activations': [r for r in BROADER['target_positive_translation_margin_guard_triggered'] if r['bidirectional_veto_feature'] > THRESHOLD],
    'phase2_restore_activations': [r for r in PHASE2['target_positive_translation_margin_guard_triggered'] if r['bidirectional_veto_feature'] > THRESHOLD],
    'seen_support': {
        'translation_x_pos_mid_sharp_curl_max': max(r['bidirectional_veto_feature'] for r in pos),
        'rotation_z_pos_mid_sharp_curl_min': min(r['bidirectional_veto_feature'] for r in rot),
    },
}
(BASE / 'stage1_global_overview_farther_scale_n288_harder_phase2_positive_guard_overreach_candidate_definition_audit_analysis.json').write_text(json.dumps(analysis, indent=2))
