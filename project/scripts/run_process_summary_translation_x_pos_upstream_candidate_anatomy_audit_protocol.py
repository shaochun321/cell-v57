from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_upstream_candidate_anatomy_audit import build_translation_x_pos_upstream_candidate_anatomy_audit


def main() -> None:
    ap = argparse.ArgumentParser(description='Audit translation_x_pos upstream candidate anatomy before atlas handoff.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-process-trace', required=True)
    ap.add_argument('--seed7-shell-trace', required=True)
    ap.add_argument('--seed7-atlas-trace', required=True)
    ap.add_argument('--seed8-process-trace', required=True)
    ap.add_argument('--seed8-shell-trace', required=True)
    ap.add_argument('--seed8-atlas-trace', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_upstream_candidate_anatomy_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_process_trace_path=args.seed7_process_trace,
        seed7_shell_trace_path=args.seed7_shell_trace,
        seed7_atlas_trace_path=args.seed7_atlas_trace,
        seed8_process_trace_path=args.seed8_process_trace,
        seed8_shell_trace_path=args.seed8_shell_trace,
        seed8_atlas_trace_path=args.seed8_atlas_trace,
    )
    out = outdir / 'process_summary_translation_x_pos_upstream_candidate_anatomy_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'audit output: {out}')


if __name__ == '__main__':
    main()
