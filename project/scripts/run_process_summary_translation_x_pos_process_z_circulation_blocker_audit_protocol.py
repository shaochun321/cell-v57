from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_process_z_circulation_blocker_audit import (
    build_translation_x_pos_process_z_circulation_blocker_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run translation_x_pos process z-circulation blocker audit.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-process-trace', required=True)
    ap.add_argument('--seed7-shell-trace', required=True)
    ap.add_argument('--seed8-process-trace', required=True)
    ap.add_argument('--seed8-shell-trace', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_process_z_circulation_blocker_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_process_trace_path=args.seed7_process_trace,
        seed7_shell_trace_path=args.seed7_shell_trace,
        seed8_process_trace_path=args.seed8_process_trace,
        seed8_shell_trace_path=args.seed8_shell_trace,
    )
    (outdir / 'process_summary_translation_x_pos_process_z_circulation_blocker_audit.json').write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
