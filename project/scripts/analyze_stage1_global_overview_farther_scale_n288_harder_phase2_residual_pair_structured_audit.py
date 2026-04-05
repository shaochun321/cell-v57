from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_phase2_module(path: Path):
    spec = importlib.util.spec_from_file_location('phase2_mod', str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser(description='Structured audit of residual pairs from N288 harder phase-2 target-seed expansion under the fixed v53 stack.')
    ap.add_argument('--source-analysis-json', default='/mnt/data/v54_n288_harder_target_seedexp_phase2_fixed_v53_stack_candidate/stage1_global_overview_farther_scale_n288_harder_target_seedexp_phase2_fixed_v53_stack_candidate_analysis.json')
    ap.add_argument('--seen-root', default='/mnt/data/v53_n288_harder_seen78_raw')
    ap.add_argument('--phase2-script', default='/mnt/data/v53_full/project/scripts/analyze_stage1_global_overview_farther_scale_n288_harder_target_seedexp_phase2_fixed_v53_stack_candidate.py')
    ap.add_argument('--outdir', default='outputs/stage1_global_overview_farther_scale_n288_harder_phase2_residual_pair_structured_audit')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    analysis = json.loads(Path(args.source_analysis_json).read_text(encoding='utf-8'))
    mod = load_phase2_module(Path(args.phase2_script))
    seen = mod.load_panel(Path(args.seen_root))
    feat_keys = sorted(set(mod.GATE_KEYS + mod.NONTRANSLATION_KEYS + mod.SIGN_KEYS))
    means, stds = mod.zscore_fit(seen, feat_keys)
    seen_z = mod.zscore_apply(seen, means, stds)
    t_center = mod.class_mean(seen_z, lambda s: s['label'].startswith('translation'), mod.GATE_KEYS)
    nt_center = mod.class_mean(seen_z, lambda s: not s['label'].startswith('translation'), mod.GATE_KEYS)

    def family_stats(case_name: str):
        rows = []
        for s in seen_z:
            if s['case_name'] == case_name:
                dt = mod.squared_distance(s['z'], t_center, mod.GATE_KEYS)
                dnt = mod.squared_distance(s['z'], nt_center, mod.GATE_KEYS)
                rows.append({
                    'seed': s['seed'],
                    'gate_margin_translation_minus_nontranslation': dt - dnt,
                    'bidirectional_veto_feature': s['features'][mod.BIDIRECTIONAL_VETO_KEY],
                    'trace_basis_feature_value': s['features'][mod.POSITIVE_TRACE_FEATURE],
                })
        return {
            'case_name': case_name,
            'sample_count': len(rows),
            'gate_margin_min': min(r['gate_margin_translation_minus_nontranslation'] for r in rows),
            'gate_margin_max': max(r['gate_margin_translation_minus_nontranslation'] for r in rows),
            'curl_min': min(r['bidirectional_veto_feature'] for r in rows),
            'curl_max': max(r['bidirectional_veto_feature'] for r in rows),
            'trace_min': min(r['trace_basis_feature_value'] for r in rows),
            'trace_max': max(r['trace_basis_feature_value'] for r in rows),
            'rows': rows,
        }

    mis = analysis['target_misclassifications']
    pos_cases = [r for r in mis if r['case_name'] == 'rotation_z_pos_mid_sharp' and r['predicted'] == 'translation_x_pos']
    neg_cases = [r for r in mis if r['case_name'] == 'translation_x_neg_early_soft' and r['predicted'] == 'baseline']

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n288_harder_phase2_residual_pair_structured_audit',
        'source_protocol': 'stage1_global_overview_farther_scale_n288_harder_target_seedexp_phase2_fixed_v53_stack_candidate',
        'source_analysis_json': args.source_analysis_json,
        'target_scale': 288,
        'target_seeds': [17, 18, 19, 20, 21, 22, 23, 24],
        'target_panel_result': {
            'overall_accuracy': analysis['target_eval']['accuracy'],
            'translation_accuracy': analysis['target_eval']['translation_accuracy'],
            'remaining_error_count': len(mis),
        },
        'residual_families': [
            {
                'family_id': 'ATLAS-R7',
                'name': 'N288 phase2 positive guard overreach into true rotation',
                'canonical_cases': pos_cases,
                'morphology': 'positive mid-sharp guard overreach into true rotation',
                'separator_status': 'suppressed by positive translation-margin guard',
                'current_best_interpretation': 'the fixed positive translation-margin guard is too permissive for a farther-scale mid-sharp rotation subset with very high curl; this is a carried-forward stack boundary, not evidence of general mainline collapse',
                'seen_reference': {
                    'rotation_z_pos_mid_sharp': family_stats('rotation_z_pos_mid_sharp'),
                    'translation_x_pos_mid_sharp': family_stats('translation_x_pos_mid_sharp'),
                },
                'family_like': len(pos_cases) >= 2,
                'recommended_next_step': 'controlled study candidate priority 1',
            },
            {
                'family_id': 'ATLAS-R8',
                'name': 'N288 phase2 negative early-soft spill to baseline',
                'canonical_cases': neg_cases,
                'morphology': 'negative early-soft gate miss into baseline',
                'separator_status': 'quiet',
                'current_best_interpretation': 'the sample exits translation support before sign/guard logic can help; this is more like a gate/basis spill than a separator problem and should not yet be answered by a mirrored patch',
                'seen_reference': {
                    'translation_x_neg_early_soft': family_stats('translation_x_neg_early_soft'),
                },
                'family_like': len(neg_cases) >= 2,
                'recommended_next_step': 'atlas only for now; do not patch before R7 is isolated',
            },
        ],
        'current_authoritative_next_task': 'stage1_global_overview_farther_scale_n288_harder_phase2_positive_guard_overreach_controlled_study',
        'discipline': 'Do not retune global thresholds. Study the repeated positive family first. Keep the isolated negative early-soft spill in the atlas until it either repeats or survives a dedicated gate/basis audit.',
    }
    (outdir / 'stage1_global_overview_farther_scale_n288_harder_phase2_residual_pair_structured_audit_analysis.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# N288 harder phase-2 residual pair structured audit',
        '',
        'This audit does not add a new rule. It localizes the remaining residuals that appear when the fixed v53 stack is tested on N288 harder target seeds `17-24`.',
        '',
        '## Source panel result',
        f'- N288 overall: `{analysis["target_eval"]["accuracy"]:.3f}`',
        f'- N288 translation: `{analysis["target_eval"]["translation_accuracy"]:.3f}`',
        f'- remaining target errors: `{len(mis)}`',
        '',
        '## Residual family split',
        '- **ATLAS-R7 — positive guard overreach into true rotation**',
        f'  - count: `{len(pos_cases)}`',
        '  - cases:',
    ]
    for r in pos_cases:
        lines.append(f'    - seed {r["seed"]} `{r["case_name"]}`: `{r["label"]}` -> `{r["predicted"]}`; gate margin `{r["gate_margin_translation_minus_nontranslation"]:.6f}`, curl `{r["bidirectional_veto_feature"]:.6f}`')
    lines += [
        '  - reading: the positive translation-margin guard suppresses the separator on a farther-scale mid-sharp rotation subset with very high curl',
        '  - governance: treat this as the first repeated family and study it before adding any other rule',
        '',
        '- **ATLAS-R8 — negative early-soft spill to baseline**',
        f'  - count: `{len(neg_cases)}`',
        '  - cases:',
    ]
    for r in neg_cases:
        lines.append(f'    - seed {r["seed"]} `{r["case_name"]}`: `{r["label"]}` -> `{r["predicted"]}`; gate margin `{r["gate_margin_translation_minus_nontranslation"]:.6f}`, neg/pos ratio `{r["neg_over_pos_sign_ratio"]:.6f}`')
    lines += [
        '  - reading: this is not a separator event; the sample spills to baseline before any sign-aware recovery can act',
        '  - governance: do not answer it with a mirrored quick patch yet',
        '',
        '## Recommended next task',
        '- run **N288 harder phase-2 positive guard overreach controlled study**',
        '- do **not** retune separator or other carried-forward thresholds first',
        '- keep the isolated negative early-soft spill in the atlas until it repeats or survives a dedicated gate/basis audit',
    ]
    (outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N288_HARDER_PHASE2_RESIDUAL_PAIR_STRUCTURED_AUDIT_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
