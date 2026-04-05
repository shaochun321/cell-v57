from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

PROFILES = ('early_sharp', 'mid_balanced', 'late_soft')
SECTION_KEYS = [
    'interface_network_diagnostics',
    'interface_temporal_diagnostics',
    'interface_topology_diagnostics',
    'interface_spectrum_diagnostics',
    'channel_hypergraph_diagnostics',
    'channel_motif_diagnostics',
]

SELECTED_FEATURE = 'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.dynamic_phasic_family.mean_centroid_shell_index'
SELECTED_THRESHOLD = 1.3508873633981915
SELECTED_DIRECTION = 'high'


def flatten_numeric(obj: Any, prefix: str = '') -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f'{prefix}.{k}' if prefix else k
            out.update(flatten_numeric(v, nk))
    elif isinstance(obj, list):
        pass
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = float(obj)
    return out


def load_panel(panel_root: Path) -> dict[tuple[int, int, str], dict[str, Any]]:
    samples: dict[tuple[int, int, str], dict[str, Any]] = {}
    for scale_dir in sorted(panel_root.glob('N*')):
        scale = int(scale_dir.name[1:])
        for seed_dir in sorted(scale_dir.glob('seed_*')):
            seed = int(seed_dir.name.split('_')[1])
            for case_dir in sorted(seed_dir.iterdir()):
                if not case_dir.is_dir():
                    continue
                summary_path = case_dir / 'summary.json'
                if not summary_path.exists():
                    continue
                with summary_path.open('r', encoding='utf-8') as fh:
                    summary = json.load(fh)
                feat = flatten_numeric({k: summary[k] for k in SECTION_KEYS if k in summary})
                samples[(scale, seed, case_dir.name)] = {
                    'scale': scale,
                    'seed': seed,
                    'case_name': case_dir.name,
                    'features': feat,
                }
    return samples


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(1 for r in rows if r['predicted'] == r['label']) / max(1, len(rows))


def translation_accuracy(rows: list[dict[str, Any]]) -> float:
    trs = [r for r in rows if str(r['label']).startswith('translation')]
    return sum(1 for r in trs if r['predicted'] == r['label']) / max(1, len(trs))


def eval_candidate(source_rows: list[dict[str, Any]], feature_map: dict[tuple[int, int, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seen: list[dict[str, Any]] = []
    target: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []
    for row in source_rows:
        key = (int(row['scale']), int(row['seed']), str(row['case_name']))
        feat_val = feature_map[key]['features'][SELECTED_FEATURE]
        positive_sign_pref = row.get('sign_distance_pos', float('inf')) < row.get('sign_distance_neg', float('inf'))
        cond = (
            row['stage1_predicted'] == 'nontranslation'
            and row.get('pre_sign_aware_predicted', row.get('predicted', '')) == 'baseline'
            and not row.get('bidirectional_veto_triggered', False)
            and positive_sign_pref
            and ((feat_val >= SELECTED_THRESHOLD) if SELECTED_DIRECTION == 'high' else (feat_val <= SELECTED_THRESHOLD))
        )
        new_row = dict(row)
        new_row['trace_basis_feature'] = SELECTED_FEATURE
        new_row['trace_basis_feature_value'] = feat_val
        new_row['trace_basis_threshold'] = SELECTED_THRESHOLD
        new_row['trace_basis_direction'] = SELECTED_DIRECTION
        new_row['positive_trace_basis_bridge_triggered'] = cond
        if cond:
            prev = row['predicted']
            new_row['predicted'] = 'translation_x_pos'
            triggers.append({
                'scale': new_row['scale'],
                'seed': new_row['seed'],
                'case_name': new_row['case_name'],
                'label': new_row['label'],
                'feature_value': feat_val,
                'previous_predicted': prev,
                'new_predicted': 'translation_x_pos',
            })
        if int(new_row['scale']) == 224:
            target.append(new_row)
        else:
            seen.append(new_row)
    return seen, target, triggers


def main() -> None:
    ap = argparse.ArgumentParser(description='Validate the richer temporal/trace positive bridge on the N224 standard seed-expansion panel without changing any thresholds.')
    ap.add_argument('--panel-root', type=str, default='/mnt/data/v39_standard_raw')
    ap.add_argument('--source-analysis-json', type=str, default='/mnt/data/stage1_global_overview_farther_scale_n224_sign_aware_gate_fallback_candidate_analysis.json')
    ap.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_standard_seedexp_trace_bridge_probe')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    feature_map = load_panel(Path(args.panel_root))
    with Path(args.source_analysis_json).open('r', encoding='utf-8') as fh:
        source = json.load(fh)
    all_rows = source['seen_eval']['predictions'] + source['target_eval']['predictions']

    seen_eval, target_eval, triggers = eval_candidate(all_rows, feature_map)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_standard_seedexp_trace_bridge_probe',
        'panel_root': args.panel_root,
        'source_analysis_json': args.source_analysis_json,
        'selection_rule': 'keep the overview-first mainline unchanged, keep the bidirectional rotation separator unchanged, keep the negative sign-aware fallback unchanged, and test the fixed positive trace-basis bridge from the N224 harder study on the N224 standard seed-expansion panel without threshold reselection',
        'selected_feature': SELECTED_FEATURE,
        'selected_threshold': SELECTED_THRESHOLD,
        'selected_direction': SELECTED_DIRECTION,
        'seen_eval': {
            'accuracy': accuracy(seen_eval),
            'translation_accuracy': translation_accuracy(seen_eval),
            'predictions': seen_eval,
        },
        'target_eval': {
            'accuracy': accuracy(target_eval),
            'translation_accuracy': translation_accuracy(target_eval),
            'predictions': target_eval,
        },
        'seen_triggered': [t for t in triggers if int(t['scale']) != 224],
        'target_triggered': [t for t in triggers if int(t['scale']) == 224],
        'target_remaining_errors': [r for r in target_eval if r['predicted'] != r['label']],
        'verdict': 'standard_seedexp_trace_bridge_probe',
        'interpretation': 'This probe tests whether the positive trace-basis bridge found on the N224 harder panel is a general farther-scale contamination risk or a controlled bridge. On the standard seed-expansion panel it should either remain silent or only fire on a clearly positive late-balanced/late-soft residual; in either case, seen scales must remain untouched.',
    }
    json_path = outdir / 'stage1_global_overview_farther_scale_n224_standard_seedexp_trace_bridge_probe_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N224 standard seed-expansion trace-bridge probe',
        '',
        'This probe keeps the overview-first mainline, the bidirectional rotation separator, and the negative sign-aware fallback unchanged. It then evaluates the **fixed positive trace-basis bridge** from the N224 harder study on the N224 standard richer-profile seed-expansion panel.',
        '',
        '## Selection discipline',
        '- no threshold reselection',
        '- no target-scale tuning',
        '- no new mirrored sign patch',
        '- keep the fixed positive bridge exactly as chosen in the N224 harder study',
        '',
        '## Fixed positive bridge',
        f'- feature: `{SELECTED_FEATURE}`',
        f'- direction: `{SELECTED_DIRECTION}`',
        f'- threshold: `{SELECTED_THRESHOLD:.6f}`',
        '- guard conditions:',
        '  - stage-1 must first predict `nontranslation`',
        '  - stage-2 must first predict `baseline`',
        '  - bidirectional separator must remain inactive',
        '  - sign geometry must already prefer `translation_x_pos`',
        '',
        '## Results',
        f'- seen overall: `{accuracy(seen_eval):.3f}`',
        f'- seen translation: `{translation_accuracy(seen_eval):.3f}`',
        f'- N224 overall: `{accuracy(target_eval):.3f}`',
        f'- N224 translation: `{translation_accuracy(target_eval):.3f}`',
        '',
        '## Trigger pattern',
        f'- seen triggers: `{len([t for t in triggers if int(t["scale"]) != 224])}`',
        f'- target triggers: `{len([t for t in triggers if int(t["scale"]) == 224])}`',
    ]
    for trig in [t for t in triggers if int(t['scale']) == 224]:
        lines.append(f'- target trigger: `N{trig["scale"]} / seed {trig["seed"]} / {trig["case_name"]}` from `{trig["previous_predicted"]}` to `{trig["new_predicted"]}` using feature value `{trig["feature_value"]:.6f}`')
    remaining = [r for r in target_eval if r['predicted'] != r['label']]
    lines += ['', '## Remaining target errors']
    if remaining:
        for row in remaining:
            lines.append(f'- `seed {row["seed"]} / {row["case_name"]}` -> `{row["predicted"]}`')
    else:
        lines.append('- none')
    lines += [
        '',
        '## Interpretation',
        '- this is a contamination check, not a new candidate search',
        '- if the bridge stays silent on standard N224 while preserving 1.000 / 1.000, that supports reading it as a controlled farther-scale support rather than a broad patch stack risk',
        '- if it fires rarely and correctly, that still supports controlled use',
        '',
        '## Governance outcome',
        '- keep the overview-first mainline unchanged',
        '- keep the bidirectional rotation separator unchanged',
        '- keep the negative sign-aware fallback unchanged',
        '- do not yet promote the positive trace-basis bridge beyond N224 until this standard probe and later beyond-N224 probes are passed',
    ]
    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_STANDARD_SEEDEXP_TRACE_BRIDGE_PROBE_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
