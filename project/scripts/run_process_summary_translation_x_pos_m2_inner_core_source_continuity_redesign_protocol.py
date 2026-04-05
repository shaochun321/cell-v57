from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.analyze_process_summary_atlas import analyze_report_file
from cell_sphere_core.analysis.mirror_shell_interface import build_mirror_shell_interface_trace_from_files, summarize_mirror_shell_interface_trace
from cell_sphere_core.analysis.mirror_channel_atlas import build_mirror_channel_atlas_trace_from_files, summarize_mirror_channel_atlas_trace
from cell_sphere_core.analysis.process_summary_atlas import build_process_summary_atlas_from_files
from cell_sphere_core.analysis.process_summary_repeatability import summarize_process_summary_repeatability


def _expected(case_name: str) -> dict[str, float]:
    if case_name == 'translation_x_pos':
        return {'x': 1.0}
    if case_name == 'translation_x_neg':
        return {'x': -1.0}
    return {}


def main() -> None:
    ap = argparse.ArgumentParser(description='Rebuild shell/atlas/summary outputs from existing temporal traces for the M2 inner-core source continuity redesign branch.')
    ap.add_argument('--baseline-outdir', required=True)
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--seeds', default='7,8')
    args = ap.parse_args()

    seeds = [int(part.strip()) for part in args.seeds.split(',') if part.strip()]
    base = Path(args.baseline_outdir)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    report = {'suite': 'process_summary_repeatability_protocol', 'seed_runs': [], 'metadata': {'source': str(base)}}
    for seed in seeds:
        seed_src = base / f'seed_{seed}'
        seed_out = out / f'seed_{seed}'
        seed_out.mkdir(parents=True, exist_ok=True)
        cases = sorted([p.name for p in seed_src.iterdir() if p.is_dir() and p.name != 'analysis'])
        proto = {'suite': 'process_summary_atlas_protocol', 'cases': {}, 'report_path': str(seed_out / 'process_summary_atlas_protocol_report.json')}
        for case in cases:
            src_case = seed_src / case
            out_case = seed_out / case
            out_case.mkdir(parents=True, exist_ok=True)
            shell_trace = build_mirror_shell_interface_trace_from_files(
                process_calculator_path=src_case / 'process_calculator_trace.json',
                interface_network_path=src_case / 'interface_network_trace.json',
            )
            shell_path = out_case / 'mirror_shell_interface_trace.json'
            shell_path.write_text(json.dumps(shell_trace, ensure_ascii=False, indent=2), encoding='utf-8')
            atlas_trace = build_mirror_channel_atlas_trace_from_files(
                shell_trace_path=shell_path,
                expected_translation_signs=_expected(case),
            )
            atlas_path = out_case / 'mirror_channel_atlas_trace.json'
            atlas_path.write_text(json.dumps(atlas_trace, ensure_ascii=False, indent=2), encoding='utf-8')
            summary = build_process_summary_atlas_from_files(atlas_trace_path=atlas_path)
            summary_path = out_case / 'process_summary_atlas.json'
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
            proto['cases'][case] = {
                'mirror_shell_interface_summary': summarize_mirror_shell_interface_trace(shell_trace),
                'mirror_channel_atlas_summary': summarize_mirror_channel_atlas_trace(atlas_trace),
                'process_summary_atlas_summary': summary,
            }
        Path(proto['report_path']).write_text(json.dumps(proto, ensure_ascii=False, indent=2), encoding='utf-8')
        analysis = analyze_report_file(report_path=proto['report_path'], output_dir=seed_out / 'analysis', title=f'Process summary atlas repeatability seed {seed}')
        report['seed_runs'].append({'seed': seed, 'report_path': proto['report_path'], 'analysis_path': str(seed_out / 'analysis' / 'process_summary_atlas_analysis.json'), 'analysis': analysis})
    report_path = out / 'process_summary_repeatability_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = summarize_process_summary_repeatability(report)
    audit_path = out / 'process_summary_repeatability_audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(report_path)
    print(audit_path)


if __name__ == '__main__':
    main()
