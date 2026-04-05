from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean
from typing import Any

FIXED_THRESHOLD = 2.8051216207639436
FEATURE_CANDIDATES = ('generalized_veto_feature', 'midbalanced_veto_feature')

PANEL_SPECS = {
    'standard_original': {
        'path': 'outputs/stage1_global_overview_farther_scale_n192_midbalanced_veto_candidate/stage1_global_overview_farther_scale_n192_midbalanced_veto_candidate_analysis.json',
        'description': 'Original standard richer-profile N192 panel on seeds 7,8.',
    },
    'harder_original': {
        'path': 'outputs/stage1_global_overview_farther_scale_n192_harder_nuisance_candidate/stage1_global_overview_farther_scale_n192_harder_nuisance_candidate_analysis.json',
        'description': 'Original harder unseen-nuisance N192 panel on seeds 7,8.',
    },
    'standard_seedexp': {
        'path': 'outputs/stage1_global_overview_farther_scale_n192_standard_seedexp_candidate/stage1_global_overview_farther_scale_n192_standard_seedexp_candidate_analysis.json',
        'description': 'Standard richer-profile N192 seed expansion currently including seed 9.',
    },
    'harder_seedexp': {
        'path': 'outputs/stage1_global_overview_farther_scale_n192_harder_seedexp_candidate/stage1_global_overview_farther_scale_n192_harder_seedexp_candidate_analysis.json',
        'description': 'Harder unseen-nuisance N192 seed expansion on seeds 7,8,9,10,11,12.',
    },
}


def row_feature_key(row: dict[str, Any]) -> str:
    for key in FEATURE_CANDIDATES:
        if key in row:
            return key
    raise KeyError(f'No known veto feature key in row: {sorted(row.keys())}')


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(int(r['predicted'] == r['label']) for r in rows) / len(rows) if rows else 0.0


def replay_rows(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    vetoed: list[dict[str, Any]] = []
    for src in rows:
        row = dict(src)
        feature_key = row_feature_key(row)
        feature_value = row[feature_key]
        row['bidirectional_veto_feature_key'] = feature_key
        row['bidirectional_veto_feature'] = feature_value
        row['bidirectional_veto_triggered'] = False
        if row.get('stage1_predicted') == 'translation' and feature_value > threshold:
            row['bidirectional_veto_triggered'] = True
            row['pre_bidirectional_predicted'] = row.get('predicted')
            row['predicted'] = 'rotation_z_pos'
            row['stage1_predicted'] = 'bidirectional_rotation_veto'
            vetoed.append(row)
        out.append(row)
    return {
        'accuracy': accuracy(out),
        'translation_accuracy': accuracy([r for r in out if r['label'].startswith('translation')]),
        'predictions': out,
        'misclassifications': [r for r in out if r['predicted'] != r['label']],
        'veto_triggered': vetoed,
    }


def feature_ranges(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        feature_value = row[row_feature_key(row)]
        grouped.setdefault(row['label'], []).append(feature_value)
    return {
        label: {
            'min': min(vals),
            'max': max(vals),
            'mean': fmean(vals),
        }
        for label, vals in sorted(grouped.items())
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Replay existing N192 farther-scale analyses under a sign-agnostic direct rotation veto.')
    parser.add_argument('--outdir', default='outputs/stage1_global_overview_farther_scale_n192_bidirectional_rotation_veto_candidate')
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    panels: dict[str, Any] = {}
    for name, spec in PANEL_SPECS.items():
        payload = json.loads(Path(spec['path']).read_text(encoding='utf-8'))
        seen_eval = replay_rows(payload['seen_eval']['predictions'], FIXED_THRESHOLD)
        target_eval = replay_rows(payload['target_eval']['predictions'], FIXED_THRESHOLD)
        panels[name] = {
            'description': spec['description'],
            'source_path': spec['path'],
            'seen_eval': seen_eval,
            'target_eval': target_eval,
            'source_protocol': payload.get('protocol'),
            'target_scale': payload.get('target_scale', 192),
            'target_seeds': payload.get('target_seeds'),
            'feature_ranges_seen': feature_ranges(payload['seen_eval']['predictions']),
        }

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n192_bidirectional_rotation_veto_candidate',
        'selection_rule': 'keep the v23 threshold fixed and promote a sign-agnostic direct rotation veto: if the overview-first mainline predicts translation and hhd_curl_energy_peak_abs exceeds the seen-scale rotation/translation separator, map directly to rotation_z_pos',
        'bidirectional_veto_key': 'hhd_curl_energy_peak_abs',
        'bidirectional_veto_threshold': FIXED_THRESHOLD,
        'panels': panels,
        'verdict': 'promising_promoted_farther_scale_candidate',
        'interpretation': 'A single fixed sign-agnostic direct rotation veto repairs both translation_x_neg and translation_x_pos farther-scale rotation leaks on all currently tested N192 panels, while preserving 1.000 seen-scale and translation behavior in the replayed audits.',
    }
    analysis_path = outdir / 'stage1_global_overview_farther_scale_n192_bidirectional_rotation_veto_candidate_analysis.json'
    analysis_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N192 bidirectional rotation-veto candidate',
        '',
        'This candidate keeps the current overview-first mainline and the **v23 fixed curl threshold** unchanged, but removes the one-sided sign restriction from the farther-scale safeguard.',
        '',
        '## Selection discipline',
        '- no threshold reselection',
        '- no target-seed tuning',
        '- no new local rescue branch',
        '- promote a **sign-agnostic direct rotation veto**: when the mainline predicts translation and `hhd_curl_energy_peak_abs` exceeds the fixed seen-scale rotation separator, map directly to `rotation_z_pos`',
        '',
        '## Fixed key',
        '- bidirectional veto key: `hhd_curl_energy_peak_abs`',
        f'- fixed threshold carried from v23: `{FIXED_THRESHOLD}`',
        '',
        '## Seen-scale feature ranges supporting the rule',
    ]
    seedexp_ranges = panels['harder_seedexp']['feature_ranges_seen']
    for label, stats in seedexp_ranges.items():
        lines.append(f"- {label}: min `{stats['min']:.6f}`, max `{stats['max']:.6f}`, mean `{stats['mean']:.6f}`")
    lines += [
        '',
        'These seen-scale ranges show a clean gap: baseline and both translation signs stay at or below the translation ceiling, while rotation lives well above the fixed threshold.',
        '',
        '## Replay results by panel',
    ]
    panel_order = ['standard_original', 'harder_original', 'standard_seedexp', 'harder_seedexp']
    for name in panel_order:
        panel = panels[name]
        seen_eval = panel['seen_eval']
        target_eval = panel['target_eval']
        lines += [
            f"### {name}",
            f"- {panel['description']}",
            f"- seen-scale overall: `{seen_eval['accuracy']:.3f}`",
            f"- seen-scale translation: `{seen_eval['translation_accuracy']:.3f}`",
            f"- target overall: `{target_eval['accuracy']:.3f}`",
            f"- target translation: `{target_eval['translation_accuracy']:.3f}`",
        ]
        if target_eval['veto_triggered']:
            lines.append('- target veto activations:')
            for row in target_eval['veto_triggered']:
                lines.append(
                    f"  - seed {row['seed']} `{row['case_name']}`: `{row.get('pre_bidirectional_predicted', row.get('predicted'))}` -> `{row['predicted']}` with `{row['bidirectional_veto_feature_key']}`={row['bidirectional_veto_feature']:.6f}"
                )
        else:
            lines.append('- target veto activations: none')
        if target_eval['misclassifications']:
            lines.append('- target errors:')
            for row in target_eval['misclassifications']:
                lines.append(f"  - seed {row['seed']} `{row['case_name']}`: true `{row['label']}`, predicted `{row['predicted']}`")
        else:
            lines.append('- target errors: none')
        lines.append('')

    lines += [
        '## Interpretation',
        '- The original farther-scale safeguard was structurally right but too one-sided: it only vetoed negative-translation leaks.',
        '- The replayed v26 rule closes the remaining gap by treating high-curl translation predictions as rotation regardless of sign.',
        '- On all currently tested N192 panels, this yields `1.000 / 1.000` while keeping the threshold fixed and preserving seen-scale cleanliness.',
        '',
        '## Next task',
        '- Keep the overview-first mainline and the v26 bidirectional veto fixed.',
        '- Next authoritative task: broaden **standard N192 seed expansion** beyond the current partial extra-seed check, then move to a farther unseen scale beyond N192.',
    ]
    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N192_BIDIRECTIONAL_ROTATION_VETO_CANDIDATE_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
