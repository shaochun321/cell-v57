#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / 'outputs' / 'stage1_global_overview_farther_scale_n288_standard_residual_pair_structured_audit'
OUTDIR.mkdir(parents=True, exist_ok=True)

src_n288 = ROOT / 'outputs' / 'stage1_global_overview_farther_scale_n288_standard_full_stack_candidate' / 'stage1_global_overview_farther_scale_n288_standard_full_stack_candidate_analysis.json'
src_n256 = ROOT / 'outputs' / 'stage1_global_overview_farther_scale_n256_standard_full_stack_seedexp_candidate' / 'stage1_global_overview_farther_scale_n256_standard_full_stack_seedexp_candidate_analysis.json'

with open(src_n288) as f:
    n288 = json.load(f)
with open(src_n256) as f:
    n256 = json.load(f)

pred288 = n288['target_eval']['predictions']
mis288 = n288['target_misclassifications']
pred256 = n256['target_eval']['predictions']
seen288 = n288['seen_eval']['predictions']

# Select structured residual pair
neg_case = next(x for x in mis288 if x['case_name'] == 'translation_x_neg_early_sharp')
base_case = next(x for x in mis288 if x['case_name'] == 'baseline')

# Reference cases at N256 and seen scales
neg_refs_256 = [x for x in pred256 if x['case_name'] == 'translation_x_neg_early_sharp']
base_refs_256 = [x for x in pred256 if x['case_name'] == 'baseline']
neg_refs_seen = [x for x in seen288 if x['case_name'] == 'translation_x_neg_early_sharp']
base_refs_seen = [x for x in seen288 if x['case_name'] == 'baseline']

analysis = {
    'protocol': 'stage1_global_overview_farther_scale_n288_standard_residual_pair_structured_audit',
    'source_protocol': n288['protocol'],
    'target_scale': 288,
    'target_seeds': n288['target_seeds'],
    'source_analysis_file': str(src_n288.relative_to(ROOT)),
    'pair_count': len(mis288),
    'residual_pair': mis288,
    'negative_early_sharp_translation_case': {
        'case': neg_case,
        'n256_reference_cases': neg_refs_256,
        'seen_reference_cases': neg_refs_seen,
        'diagnosis': 'separator_overreach_into_true_translation',
        'evidence': {
            'pre_veto_translation_correct': neg_case['pre_bidirectional_predicted'] == 'translation_x_neg',
            'veto_only_failure': neg_case['bidirectional_veto_triggered'] is True,
            'curl_at_n288_exceeds_threshold': neg_case['bidirectional_veto_feature'],
            'threshold': n288['bidirectional_veto_threshold'],
            'sign_still_prefers_negative': neg_case['sign_distance_neg'] < neg_case['sign_distance_pos'],
            'n256_curl_range_same_case': [x['bidirectional_veto_feature'] for x in neg_refs_256],
        },
        'interpretation': 'The N288 seed-7 translation_x_neg_early_sharp case still lands on the translation side and retains strong negative-sign coherence, but its curl-like separator feature rises above the fixed farther-scale veto threshold. This is best read as separator overreach into a true translation case, not as a gate collapse or sign loss.'
    },
    'baseline_edge_case': {
        'case': base_case,
        'n256_reference_cases': base_refs_256,
        'seen_reference_cases': base_refs_seen,
        'diagnosis': 'baseline_edge_leak_into_translation',
        'evidence': {
            'gate_margin_translation_minus_nontranslation': base_case['gate_margin_translation_minus_nontranslation'],
            'n256_baseline_gate_margins': [x['gate_margin_translation_minus_nontranslation'] for x in base_refs_256],
            'low_curl_not_separator_issue': base_case['bidirectional_veto_feature'],
            'baseline_stage1_crossing_is_small': abs(base_case['gate_margin_translation_minus_nontranslation']),
        },
        'interpretation': 'The N288 seed-8 baseline case crosses only slightly onto the translation side before being read as translation_x_pos. Compared with the comfortably positive baseline margins at N256, this is a small baseline-edge leak rather than a separator problem. It suggests a new boundary squeeze near the baseline/translation interface.'
    },
    'route_status': 'mainline_unchanged',
    'next_authoritative_task': 'N288 pair-specific controlled audit before running harder nuisance',
    'high_level_interpretation': 'The first beyond-N256 failures are not a generic farther-scale collapse. They split into two structured families: a separator overreach into true negative early-sharp translation, and a narrow baseline-edge leak into positive translation.'
}

report = f'''# N288 standard residual pair structured audit

This audit examines the two residual target errors that first appear at the farther unseen scale `N288` under the fixed full-stack readout.

## Pair summary
- target scale: `288`
- target seeds: `{n288['target_seeds']}`
- seen overall: `{n288['seen_eval']['accuracy']:.3f}`
- target overall: `{n288['target_eval']['accuracy']:.3f}`
- target translation: `{n288['target_eval']['translation_accuracy']:.3f}`
- support activations: negative fallback `0`, positive trace bridge `0`

## Residual 1 — `translation_x_neg_early_sharp` -> `rotation_z_pos`
### Structured diagnosis
`separator_overreach_into_true_translation`

### Why
- pre-veto prediction is already `translation_x_neg`
- negative sign remains strongly favored
- failure happens only because the fixed bidirectional curl separator triggers at `N288`
- N256 and seen references for the same case family stay well below the separator threshold

### Key values at failure
- translation distance: `{neg_case['translation_distance']:.6f}`
- nontranslation distance: `{neg_case['nontranslation_distance']:.6f}`
- gate margin (translation - nontranslation): `{neg_case['gate_margin_translation_minus_nontranslation']:.6f}`
- sign distance pos: `{neg_case['sign_distance_pos']:.6f}`
- sign distance neg: `{neg_case['sign_distance_neg']:.6f}`
- curl separator feature: `{neg_case['bidirectional_veto_feature']:.6f}`
- separator threshold: `{n288['bidirectional_veto_threshold']:.6f}`

## Residual 2 — `baseline` -> `translation_x_pos`
### Structured diagnosis
`baseline_edge_leak_into_translation`

### Why
- curl is low, so this is not a separator event
- the stage-1 crossing is very small (`{base_case['gate_margin_translation_minus_nontranslation']:.6f}`)
- compared with N256 baseline references, this case has a much tighter gate margin and falls just onto the translation side
- once there, sign readout prefers the positive branch

### Key values at failure
- translation distance: `{base_case['translation_distance']:.6f}`
- nontranslation distance: `{base_case['nontranslation_distance']:.6f}`
- gate margin (translation - nontranslation): `{base_case['gate_margin_translation_minus_nontranslation']:.6f}`
- sign distance pos: `{base_case['sign_distance_pos']:.6f}`
- sign distance neg: `{base_case['sign_distance_neg']:.6f}`
- curl separator feature: `{base_case['bidirectional_veto_feature']:.6f}`

## Route interpretation
These two residuals do **not** support a route change yet.
They are structured and heterogeneous:
1. one is a true-translation case being overruled by the farther-scale separator
2. one is a narrow baseline-edge leak into the translation branch

The next clean move is a pair-specific controlled audit before escalating to `N288` harder nuisance.
'''

(OUTDIR / 'stage1_global_overview_farther_scale_n288_standard_residual_pair_structured_audit_analysis.json').write_text(json.dumps(analysis, indent=2))
(OUTDIR / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N288_STANDARD_RESIDUAL_PAIR_STRUCTURED_AUDIT_REPORT.md').write_text(report)
print('[OK] wrote audit outputs')
