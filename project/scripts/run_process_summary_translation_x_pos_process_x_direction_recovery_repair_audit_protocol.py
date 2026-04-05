from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_process_x_direction_recovery_repair_audit import (
    build_translation_x_pos_process_x_direction_recovery_repair_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run translation_x_pos process x-direction recovery repair audit.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-translation-process-trace', required=True)
    ap.add_argument('--seed7-translation-shell-trace', required=True)
    ap.add_argument('--seed7-summary-analysis', required=True)
    ap.add_argument('--seed8-translation-process-trace', required=True)
    ap.add_argument('--seed8-translation-shell-trace', required=True)
    ap.add_argument('--seed8-summary-analysis', required=True)
    ap.add_argument('--seed8-rotation-process-trace', required=True)
    ap.add_argument('--seed8-rotation-shell-trace', required=True)
    ap.add_argument('--seed8-rotation-summary-analysis', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_process_x_direction_recovery_repair_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_translation_process_trace_path=args.seed7_translation_process_trace,
        seed7_translation_shell_trace_path=args.seed7_translation_shell_trace,
        seed7_summary_analysis_path=args.seed7_summary_analysis,
        seed8_translation_process_trace_path=args.seed8_translation_process_trace,
        seed8_translation_shell_trace_path=args.seed8_translation_shell_trace,
        seed8_summary_analysis_path=args.seed8_summary_analysis,
        seed8_rotation_process_trace_path=args.seed8_rotation_process_trace,
        seed8_rotation_shell_trace_path=args.seed8_rotation_shell_trace,
        seed8_rotation_summary_analysis_path=args.seed8_rotation_summary_analysis,
    )
    (outdir / 'process_summary_translation_x_pos_process_x_direction_recovery_repair_audit.json').write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
