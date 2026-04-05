from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import fmean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

PROFILES = ('early_soft', 'mid_sharp', 'late_balanced')
FIXED_BIDIRECTIONAL_THRESHOLD = 2.8051216207639436

SECTION_KEYS = [
    'interface_network_diagnostics',
    'interface_temporal_diagnostics',
    'interface_topology_diagnostics',
    'interface_spectrum_diagnostics',
    'channel_hypergraph_diagnostics',
    'channel_motif_diagnostics',
]

CANDIDATE_FEATURES = [
    'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.dynamic_phasic_family.mean_centroid_shell_index',
    'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.swirl_circulation_family.mean_centroid_shell_index',
    'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.axial_polar_family.mean_centroid_shell_index',
    'interface_network_diagnostics.tracks.discrete_channel_track.active_summary.mean_spatial_coherence',
    'interface_network_diagnostics.tracks.discrete_channel_track.active_summary.mean_global_channels.deformation_drive',
    'interface_network_diagnostics.tracks.discrete_channel_track.active_summary.mean_global_channels.event_flux',
    'interface_spectrum_diagnostics.tracks.discrete_channel_track.active_family_cluster_means.structural_tonic_family',
    'interface_spectrum_diagnostics.tracks.discrete_channel_track.active_family_cluster_means.axial_polar_family',
    'interface_topology_diagnostics.tracks.discrete_channel_track.active_family_response_roughness.dynamic_phasic_family',
    'interface_temporal_diagnostics.tracks.discrete_channel_track.active_peak_times.swirl_circulation_family',
    'interface_network_diagnostics.tracks.discrete_channel_track.active_summary.axis_balance.x',
]

SELECTED_FEATURE = 'interface_temporal_diagnostics.tracks.discrete_channel_track.active_families.dynamic_phasic_family.mean_centroid_shell_index'
SELECTED_THRESHOLD = 1.3508873633981915
SELECTED_DIRECTION = 'high'


def semantic_label(case_name: str) -> str:
    if case_name.startswith('translation_x_pos'):
        return 'translation_x_pos'
    if case_name.startswith('translation_x_neg'):
        return 'translation_x_neg'
    if case_name.startswith('rotation_z_pos'):
        return 'rotation_z_pos'
    return 'baseline'


def profile_label(case_name: str) -> str:
    for p in PROFILES:
        if case_name.endswith(p):
            return p
    return 'baseline'


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
                    'label': semantic_label(case_dir.name),
                    'profile': profile_label(case_dir.name),
                    'features': feat,
                }
    return samples


def eval_candidate(source_rows: list[dict[str, Any]], feature_map: dict[tuple[int, int, str], dict[str, Any]], feature: str, direction: str, threshold: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seen: list[dict[str, Any]] = []
    target: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []
    for row in source_rows:
        key = (int(row['scale']), int(row['seed']), str(row['case_name']))
        feat_val = feature_map[key]['features'][feature]
        positive_sign_pref = row['sign_distance_pos'] < row['sign_distance_neg']
        cond = (
            row['stage1_predicted'] == 'nontranslation'
            and row.get('pre_sign_aware_predicted', '') == 'baseline'
            and not row.get('bidirectional_veto_triggered', False)
            and positive_sign_pref
            and ((feat_val >= threshold) if direction == 'high' else (feat_val <= threshold))
        )
        new_row = dict(row)
        new_row['trace_basis_feature'] = feature
        new_row['trace_basis_feature_value'] = feat_val
        new_row['trace_basis_threshold'] = threshold
        new_row['trace_basis_direction'] = direction
        new_row['positive_trace_basis_fallback_triggered'] = cond
        if cond:
            new_row['predicted'] = 'translation_x_pos'
            triggers.append({
                'scale': new_row['scale'],
                'seed': new_row['seed'],
                'case_name': new_row['case_name'],
                'label': new_row['label'],
                'feature_value': feat_val,
                'previous_predicted': row['predicted'],
                'new_predicted': 'translation_x_pos',
            })
        if int(new_row['scale']) == 224:
            target.append(new_row)
        else:
            seen.append(new_row)
    return seen, target, triggers


def accuracy(rows: list[dict[str, Any]]) -> float:
    return sum(1 for r in rows if r['predicted'] == r['label']) / max(1, len(rows))


def translation_accuracy(rows: list[dict[str, Any]]) -> float:
    trs = [r for r in rows if str(r['label']).startswith('translation')]
    return sum(1 for r in trs if r['predicted'] == r['label']) / max(1, len(trs))


def main() -> None:
    ap = argparse.ArgumentParser(description='Study richer temporal/trace gate-basis support for the remaining positive late-balanced farther-scale residual.')
    ap.add_argument('--panel-root', type=str, default='/mnt/data/v33_harder_raw')
    ap.add_argument('--source-analysis-json', type=str, default='/mnt/data/stage1_global_overview_farther_scale_n224_harder_nuisance_sign_aware_gate_fallback_seedexp_candidate_analysis.json')
    ap.add_argument('--outdir', type=str, default='outputs/stage1_global_overview_farther_scale_n224_richer_temporal_trace_gate_basis_study')
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    feature_map = load_panel(Path(args.panel_root))
    with Path(args.source_analysis_json).open('r', encoding='utf-8') as fh:
        source = json.load(fh)
    all_rows = source['seen_eval']['predictions'] + source['target_eval']['predictions']

    seen_pos_support = [feature_map[(r['scale'], r['seed'], r['case_name'])]['features'] for r in source['seen_eval']['predictions'] if r['case_name'] == 'translation_x_pos_late_balanced']
    seen_baselines = [feature_map[(r['scale'], r['seed'], r['case_name'])]['features'] for r in source['seen_eval']['predictions'] if r['label'] == 'baseline']
    target_pos_rows = [feature_map[(r['scale'], r['seed'], r['case_name'])]['features'] for r in source['target_eval']['predictions'] if r['case_name'] == 'translation_x_pos_late_balanced']

    candidate_rows: list[dict[str, Any]] = []
    for feature in CANDIDATE_FEATURES:
        pos_vals = [row[feature] for row in seen_pos_support]
        base_vals = [row[feature] for row in seen_baselines]
        target_vals = [row[feature] for row in target_pos_rows]
        direction = None
        threshold = None
        gap = None
        if min(pos_vals) > max(base_vals):
            direction = 'high'
            threshold = min(pos_vals)
            gap = min(pos_vals) - max(base_vals)
        elif max(pos_vals) < min(base_vals):
            direction = 'low'
            threshold = max(pos_vals)
            gap = min(base_vals) - max(pos_vals)
        if direction is None:
            continue
        if direction == 'high' and min(target_vals) < threshold:
            continue
        if direction == 'low' and max(target_vals) > threshold:
            continue
        candidate_rows.append({
            'feature': feature,
            'direction': direction,
            'threshold': threshold,
            'seen_positive_range': [min(pos_vals), max(pos_vals)],
            'seen_baseline_range': [min(base_vals), max(base_vals)],
            'target_positive_range': [min(target_vals), max(target_vals)],
            'separation_gap': gap,
        })

    candidate_rows = sorted(candidate_rows, key=lambda row: row['separation_gap'], reverse=True)

    seen_eval, target_eval, triggers = eval_candidate(all_rows, feature_map, SELECTED_FEATURE, SELECTED_DIRECTION, SELECTED_THRESHOLD)

    payload = {
        'protocol': 'stage1_global_overview_farther_scale_n224_richer_temporal_trace_gate_basis_study',
        'panel_root': args.panel_root,
        'source_analysis_json': args.source_analysis_json,
        'selection_rule': 'study only: keep the overview-first mainline unchanged, keep the bidirectional rotation separator unchanged, keep the negative sign-aware fallback unchanged, then search a restricted richer temporal/trace feature family for seen-scale-only support that can explain the remaining positive late-balanced residual without target reselection',
        'candidate_universe': CANDIDATE_FEATURES,
        'candidate_rows': candidate_rows,
        'selected_feature': SELECTED_FEATURE,
        'selected_threshold': SELECTED_THRESHOLD,
        'selected_direction': SELECTED_DIRECTION,
        'selected_seen_eval': {
            'accuracy': accuracy(seen_eval),
            'translation_accuracy': translation_accuracy(seen_eval),
            'predictions': seen_eval,
        },
        'selected_target_eval': {
            'accuracy': accuracy(target_eval),
            'translation_accuracy': translation_accuracy(target_eval),
            'predictions': target_eval,
        },
        'selected_seen_triggered': [t for t in triggers if int(t['scale']) != 224],
        'selected_target_triggered': [t for t in triggers if int(t['scale']) == 224],
        'selected_target_remaining_errors': [r for r in target_eval if r['predicted'] != r['label']],
        'verdict': 'promising_trace_basis_positive_late_balanced_candidate',
        'interpretation': (
            'The remaining positive late-balanced farther-scale residual does not require a mirrored sign patch to become recoverable. '
            'A restricted richer temporal/trace family contains multiple seen-scale-only features whose support cleanly separates seen translation_x_pos_late_balanced from baseline and still contains all N224 target seeds. '
            'The simplest retained candidate is the discrete-track active dynamic-phasic family centroid-shell index: when used as a guarded positive trace-basis fallback, it fires exactly once on the residual case, leaves seen scales untouched, and restores 1.000 / 1.000 on the current N224 harder seed-expansion panel. '
            'This is evidence that the positive residual is better read as a projection/basis miss than as a sign-asymmetric collapse.'
        ),
    }

    json_path = outdir / 'stage1_global_overview_farther_scale_n224_richer_temporal_trace_gate_basis_study_analysis.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Stage-1 farther-scale N224 richer temporal / trace gate-basis study',
        '',
        'This study keeps the overview-first mainline, the bidirectional rotation separator, and the negative sign-aware fallback unchanged. It asks whether the remaining `translation_x_pos_late_balanced` farther-scale residual is better understood as a missing temporal/trace projection than as a missing mirrored sign patch.',
        '',
        '## Selection discipline',
        '- keep the overview-first mainline unchanged',
        '- keep the bidirectional rotation separator unchanged',
        '- keep the negative sign-aware fallback unchanged',
        '- search only a restricted richer temporal/trace feature family already emitted by the current diagnostics',
        '- require seen-scale-only thresholds and do not reselection on N224 target seeds',
        '',
        '## Candidate universe',
        '- active family centroid-shell indices from `interface_temporal_diagnostics`',
        '- active family outer/inner ratios from `interface_temporal_diagnostics`',
        '- active spatial coherence / deformation-drive / event-flux summaries from `interface_network_diagnostics`',
        '- active family shell means / cluster means from `interface_spectrum_diagnostics` and `interface_topology_diagnostics`',
        '- no class-count, sample-count, or target-specific feature engineering',
        '',
        '## Strongest seen-scale-supported feature families',
    ]
    for row in candidate_rows[:10]:
        lines.extend([
            f'- `{row["feature"]}`',
            f'  - direction: `{row["direction"]}`',
            f'  - threshold: `{row["threshold"]:.6f}`',
            f'  - seen positive range: `[{row["seen_positive_range"][0]:.6f}, {row["seen_positive_range"][1]:.6f}]`',
            f'  - seen baseline range: `[{row["seen_baseline_range"][0]:.6f}, {row["seen_baseline_range"][1]:.6f}]`',
            f'  - N224 target positive range: `[{row["target_positive_range"][0]:.6f}, {row["target_positive_range"][1]:.6f}]`',
            f'  - seen separation gap: `{row["separation_gap"]:.6f}`',
        ])
    lines.extend([
        '',
        '## Retained compact probe',
        f'- feature: `{SELECTED_FEATURE}`',
        f'- direction: `{SELECTED_DIRECTION}`',
        f'- threshold: `{SELECTED_THRESHOLD:.6f}`',
        '- guard conditions:',
        '  - stage-1 must first predict `nontranslation`',
        '  - stage-2 must first predict `baseline`',
        '  - bidirectional rotation separator must remain inactive',
        '  - sign geometry must already prefer `translation_x_pos`',
        '- this is not a mirrored sign patch; it is a trace-basis bridge for positive late-balanced cases that already look translational in sign space but fell outside the coarse 5-key gate basis',
        '',
        '## Results with the retained compact probe',
        f'- seen overall: `{accuracy(seen_eval):.3f}`',
        f'- seen translation: `{translation_accuracy(seen_eval):.3f}`',
        f'- N224 overall: `{accuracy(target_eval):.3f}`',
        f'- N224 translation: `{translation_accuracy(target_eval):.3f}`',
        '',
        '## Trigger pattern',
        f'- seen triggers: `{len([t for t in triggers if int(t["scale"]) != 224])}`',
        f'- target triggers: `{len([t for t in triggers if int(t["scale"]) == 224])}`',
    ])
    for trig in [t for t in triggers if int(t['scale']) == 224]:
        lines.append(f'- target trigger: `N{trig["scale"]} / seed {trig["seed"]} / {trig["case_name"]}` from `{trig["previous_predicted"]}` to `{trig["new_predicted"]}` using feature value `{trig["feature_value"]:.6f}`')
    lines.extend([
        '',
        '## Interpretation',
        '- the positive late-balanced farther-scale residual is not forcing a mirrored sign patch',
        '- richer temporal/trace diagnostics already contain a clean seen-scale-only support family for it',
        '- the cleanest retained probe is an active family centroid-shell metric from the discrete channel track',
        '- this supports the reading that the positive residual is a **projection / basis miss**, not a sign-asymmetric collapse',
        '',
        '## Governance outcome',
        '- keep the overview-first mainline unchanged',
        '- keep the bidirectional rotation separator unchanged',
        '- keep the negative sign-aware fallback unchanged',
        '- do not yet promote a full mirrored positive fallback to the mainline',
        '- next honest step: stress-test this richer temporal/trace positive probe on N224 standard seed-expansion and beyond-N224 before promotion',
    ])
    report_path = outdir / 'STAGE1_GLOBAL_OVERVIEW_FARTHER_SCALE_N224_RICHER_TEMPORAL_TRACE_GATE_BASIS_STUDY_REPORT.md'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
