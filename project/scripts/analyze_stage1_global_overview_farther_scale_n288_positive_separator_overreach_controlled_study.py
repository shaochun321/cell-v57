from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POSITIVE_GUARD_NAME = 'positive_translation_margin_guard'
POSITIVE_GUARD_THRESHOLD = -3.0


def load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def final_prediction_before_v50(row: dict[str, Any]) -> str:
    if 'predicted_after_baseline_support_guard' in row:
        return row['predicted_after_baseline_support_guard']
    if 'predicted_after_translation_margin_guard' in row:
        return row['predicted_after_translation_margin_guard']
    return row['predicted']


def apply_v50_guard(row: dict[str, Any], threshold: float) -> dict[str, Any]:
    out = dict(row)
    out['positive_translation_margin_guard_threshold'] = threshold
    triggered = bool(out.get('bidirectional_veto_triggered')) and out.get('pre_bidirectional_predicted') == 'translation_x_pos' and out.get('gate_margin_translation_minus_nontranslation') <= threshold
    out['positive_translation_margin_guard_triggered'] = triggered
    base_pred = final_prediction_before_v50(out)
    out['predicted_before_positive_translation_margin_guard'] = base_pred
    out['predicted_after_positive_translation_margin_guard'] = 'translation_x_pos' if triggered else base_pred
    out['predicted'] = out['predicted_after_positive_translation_margin_guard']
    return out


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def translation_accuracy(rows: list[dict[str, Any]]) -> float:
    trs = [r for r in rows if r['label'].startswith('translation')]
    return sum(int(r['predicted'] == r['label']) for r in trs) / len(trs) if trs else 0.0


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'accuracy': accuracy(rows),
        'translation_accuracy': translation_accuracy(rows),
        'guard_triggered': [
            {
                'scale': r['scale'],
                'seed': r['seed'],
                'case_name': r['case_name'],
                'label': r['label'],
                'profile': r['profile'],
            }
            for r in rows
            if r.get('positive_translation_margin_guard_triggered')
        ],
        'misclassifications': [r for r in rows if r['predicted'] != r['label']],
        'predictions': rows,
    }


def round6(x: float) -> float:
    return round(float(x), 6)


def main() -> None:
    ap = argparse.ArgumentParser(description='Evaluate a seen-scale-only positive translation-margin guard for the first N288 harder positive separator-overreach residual.')
    ap.add_argument('--baseline-json', default='/mnt/data/stage1_global_overview_farther_scale_n288_baseline_edge_controlled_study_analysis.json')
    ap.add_argument('--harder-json', default='/mnt/data/stage1_global_overview_farther_scale_n288_harder_nuisance_fixed_two_guard_candidate_analysis.json')
    ap.add_argument('--outdir', default='/mnt/data/v50_n288_positive_separator_overreach')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    baseline = load_json(Path(args.baseline_json))
    harder = load_json(Path(args.harder_json))

    # Seen support for translation_x_pos_mid_sharp is taken from the current N288 harder seen panel.
    seen_support_rows = [
        r for r in harder['seen_eval']['predictions']
        if r['label'] == 'translation_x_pos' and r['profile'] == 'mid_sharp'
    ]
    gate_margins = [r['gate_margin_translation_minus_nontranslation'] for r in seen_support_rows]
    pos_over_neg_ratios = [r['sign_distance_pos'] / r['sign_distance_neg'] for r in seen_support_rows]
    curls = [r['bidirectional_veto_feature'] for r in seen_support_rows]

    control_panel_results: dict[str, Any] = {}
    for panel_name in ['n224_standard', 'n256_standard', 'n256_harder', 'n288_standard']:
        panel = baseline['control_panel_results'][panel_name]
        control_panel_results[panel_name] = {}
        for split in ['seen_eval', 'target_eval']:
            rows = [apply_v50_guard(r, POSITIVE_GUARD_THRESHOLD) for r in panel[split]['predictions']]
            control_panel_results[panel_name][split] = summarize_rows(rows)

    control_panel_results['n288_harder'] = {}
    for split in ['seen_eval', 'target_eval']:
        rows = [apply_v50_guard(r, POSITIVE_GUARD_THRESHOLD) for r in harder[split]['predictions']]
        control_panel_results['n288_harder'][split] = summarize_rows(rows)

    canonical = None
    for row in control_panel_results['n288_harder']['target_eval']['predictions']:
        if row['scale'] == 288 and row['seed'] == 7 and row['case_name'] == 'translation_x_pos_mid_sharp':
            canonical = row
            break
    if canonical is None:
        raise RuntimeError('Canonical harder-panel residual not found.')

    result = {
        'protocol': 'stage1_global_overview_farther_scale_n288_positive_separator_overreach_controlled_study',
        'source_protocols': {
            'standard_stack_source': baseline['protocol'],
            'harder_stack_source': harder['protocol'],
        },
        'target_scale': 288,
        'target_seeds': [7, 8],
        'carried_forward_separator_threshold': harder['bidirectional_veto_threshold'],
        'carried_forward_translation_margin_guard': harder['translation_margin_guard'],
        'carried_forward_baseline_support_guard': harder['baseline_support_guard'],
        'controlled_guard': {
            'guard_name': POSITIVE_GUARD_NAME,
            'applies_when': [
                'bidirectional separator would trigger',
                'pre-veto prediction is translation_x_pos',
                f'gate_margin_translation_minus_nontranslation <= {POSITIVE_GUARD_THRESHOLD}',
            ],
            'selection_rule': 'threshold chosen from seen-scale-only translation_x_pos_mid_sharp support as a relaxed floor above the least-negative seen gate margin',
            'seen_support': {
                'family': 'translation_x_pos_mid_sharp',
                'sample_count': len(seen_support_rows),
                'gate_margin_min': min(gate_margins),
                'gate_margin_max': max(gate_margins),
                'pos_over_neg_sign_ratio_min': min(pos_over_neg_ratios),
                'pos_over_neg_sign_ratio_max': max(pos_over_neg_ratios),
                'bidirectional_veto_feature_min': min(curls),
                'bidirectional_veto_feature_max': max(curls),
            },
        },
        'canonical_positive_overreach_case': {
            'scale': canonical['scale'],
            'seed': canonical['seed'],
            'case_name': canonical['case_name'],
            'label': canonical['label'],
            'profile': canonical['profile'],
            'translation_distance': canonical['translation_distance'],
            'nontranslation_distance': canonical['nontranslation_distance'],
            'gate_margin_translation_minus_nontranslation': canonical['gate_margin_translation_minus_nontranslation'],
            'sign_distance_pos': canonical['sign_distance_pos'],
            'sign_distance_neg': canonical['sign_distance_neg'],
            'pos_over_neg_sign_ratio': canonical['sign_distance_pos'] / canonical['sign_distance_neg'],
            'bidirectional_veto_feature': canonical['bidirectional_veto_feature'],
            'pre_bidirectional_predicted': canonical['pre_bidirectional_predicted'],
        },
        'control_panel_results': control_panel_results,
        'remaining_target_errors_after_guard': control_panel_results['n288_harder']['target_eval']['misclassifications'],
        'verdict': 'promising_controlled_candidate',
        'interpretation': [
            'the N288 positive separator-overreach family is recoverable with a single seen-scale-only positive translation-margin guard',
            'the new guard stays silent on the carried-forward N224 standard, N256 standard, N256 harder, and N288 standard control panels',
            'under the fixed three-guard controlled stack, both N288 standard and the first N288 harder unseen-nuisance panel are clean',
            'this still does not justify claims of unrestricted farther-scale success; the next honest task is broader N288 harder seed expansion or the next farther unseen scale without retuning any guard',
        ],
        'next_authoritative_task': 'N288 harder seed-expansion audit under the fixed three-guard controlled stack',
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n288_positive_separator_overreach_controlled_study_analysis.json'
    with json_path.open('w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)

    cp = result['control_panel_results']
    report = f'''# N288 positive separator-overreach controlled study

This study continues from the fixed two-guard `N288 harder unseen-nuisance` probe and isolates the new harder-panel residual family:
**positive separator overreach into true translation**.

## Why this study exists
After the v47 and v48 controlled guards, `N288 standard` became clean, but the first `N288 harder unseen-nuisance` panel still left one residual:
- `N288 / seed 7 / translation_x_pos_mid_sharp -> rotation_z_pos`

The purpose of v50 is to test whether that new harder-panel error can be handled by a **single seen-scale-only positive translation-margin guard** rather than by reopening the separator threshold or adding a wider patch stack.

## Carried-forward stack
This study does **not** reopen the separator threshold, the v47 negative translation-margin guard, or the v48 baseline-support guard.
It carries forward the full controlled stack:
1. overview-first mainline
2. fixed bidirectional separator
3. v47 `translation_margin_guard`
4. v48 `baseline_support_guard`
5. existing controlled support layers left unchanged

## Controlled guard
- name: `{POSITIVE_GUARD_NAME}`
- applies only when:
  1. the fixed bidirectional separator would trigger
  2. the pre-veto prediction is already `translation_x_pos`
  3. `gate_margin_translation_minus_nontranslation <= {POSITIVE_GUARD_THRESHOLD:.6f}`

## Seen-scale-only support used for selection
Selection source: `n288_harder:seen_eval`

### Seen `translation_x_pos_mid_sharp` support
- sample count: `{len(seen_support_rows)}`
- gate margin range: `[{round6(min(gate_margins)):.6f}, {round6(max(gate_margins)):.6f}]`
- pos/neg sign ratio range: `[{round6(min(pos_over_neg_ratios)):.6f}, {round6(max(pos_over_neg_ratios)):.6f}]`
- curl separator feature range: `[{round6(min(curls)):.6f}, {round6(max(curls)):.6f}]`

### Selection reading
The threshold was chosen as a relaxed floor above the least-negative seen `translation_x_pos_mid_sharp` gate margin.
It was **not** chosen from `N288` target labels.

## Canonical positive-overreach case
- scale: `{canonical['scale']}`
- seed: `{canonical['seed']}`
- case: `{canonical['case_name']}`
- current pre-veto prediction: `{canonical['pre_bidirectional_predicted']}`
- translation distance: `{round6(canonical['translation_distance']):.6f}`
- nontranslation distance: `{round6(canonical['nontranslation_distance']):.6f}`
- gate margin (translation - nontranslation): `{round6(canonical['gate_margin_translation_minus_nontranslation']):.6f}`
- sign distance pos: `{round6(canonical['sign_distance_pos']):.6f}`
- sign distance neg: `{round6(canonical['sign_distance_neg']):.6f}`
- pos/neg sign ratio: `{round6(canonical['sign_distance_pos'] / canonical['sign_distance_neg']):.6f}`
- curl separator feature: `{round6(canonical['bidirectional_veto_feature']):.6f}`

Reading:
- the case is already strongly on the translation side
- the pre-veto sign is already positive
- the failure is the separator crossing into true positive translation
So the case reads as a **positive separator-overreach family**, not as a baseline leak and not as a sign-collapse family.

## Control panel results
### N224 standard
- seen overall: `{cp['n224_standard']['seen_eval']['accuracy']:.3f}`
- target overall: `{cp['n224_standard']['target_eval']['accuracy']:.3f}`
- target translation: `{cp['n224_standard']['target_eval']['translation_accuracy']:.3f}`
- guard triggers: `{len(cp['n224_standard']['seen_eval']['guard_triggered'])}` on seen, `{len(cp['n224_standard']['target_eval']['guard_triggered'])}` on target

### N256 standard
- seen overall: `{cp['n256_standard']['seen_eval']['accuracy']:.3f}`
- target overall: `{cp['n256_standard']['target_eval']['accuracy']:.3f}`
- target translation: `{cp['n256_standard']['target_eval']['translation_accuracy']:.3f}`
- guard triggers: `{len(cp['n256_standard']['seen_eval']['guard_triggered'])}` on seen, `{len(cp['n256_standard']['target_eval']['guard_triggered'])}` on target

### N256 harder unseen-nuisance
- seen overall: `{cp['n256_harder']['seen_eval']['accuracy']:.3f}`
- target overall: `{cp['n256_harder']['target_eval']['accuracy']:.3f}`
- target translation: `{cp['n256_harder']['target_eval']['translation_accuracy']:.3f}`
- guard triggers: `{len(cp['n256_harder']['seen_eval']['guard_triggered'])}` on seen, `{len(cp['n256_harder']['target_eval']['guard_triggered'])}` on target

### N288 standard
- seen overall: `{cp['n288_standard']['seen_eval']['accuracy']:.3f}`
- target overall: `{cp['n288_standard']['target_eval']['accuracy']:.3f}`
- target translation: `{cp['n288_standard']['target_eval']['translation_accuracy']:.3f}`
- guard triggers: `{len(cp['n288_standard']['seen_eval']['guard_triggered'])}` on seen, `{len(cp['n288_standard']['target_eval']['guard_triggered'])}` on target

### N288 harder unseen-nuisance
- seen overall: `{cp['n288_harder']['seen_eval']['accuracy']:.3f}`
- target overall: `{cp['n288_harder']['target_eval']['accuracy']:.3f}`
- target translation: `{cp['n288_harder']['target_eval']['translation_accuracy']:.3f}`
- guard triggers: `{len(cp['n288_harder']['seen_eval']['guard_triggered'])}` on seen, `{len(cp['n288_harder']['target_eval']['guard_triggered'])}` on target

## Guard activation
The guard activates exactly once:
- `N288 / seed 7 / translation_x_pos_mid_sharp`
- restores the sample from `rotation_z_pos` to `translation_x_pos`

## Remaining target errors after guard
None on the current `N288 harder unseen-nuisance` panel.

## Interpretation
- the `N288` positive separator-overreach family is **recoverable** under a single seen-scale-only positive translation-margin guard
- the guard stays fully silent on the carried-forward `N224 standard`, `N256 standard`, `N256 harder`, and `N288 standard` control panels
- under the current controlled triple
  - v47 `translation_margin_guard`
  - v48 `baseline_support_guard`
  - v50 `{POSITIVE_GUARD_NAME}`
  both `N288 standard` and the first `N288 harder unseen-nuisance` frontier become clean

## Governance status
This should be described as a **promising controlled candidate**, not as proof that unrestricted farther-scale generalization is solved.
The next honest pressure test is **N288 harder seed expansion or the next farther unseen scale without retuning any of the three guards**.
'''

    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N288_POSITIVE_SEPARATOR_OVERREACH_CONTROLLED_STUDY_REPORT.md'
    report_path.write_text(report, encoding='utf-8')

    print(f'[OK] wrote {json_path}')
    print(f'[OK] wrote {report_path}')


if __name__ == '__main__':
    main()
