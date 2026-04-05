from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit import (
    build_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run translation_x_pos seed8 inner-shell x-carrier generation restoration repair audit.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-summary', required=True)
    ap.add_argument('--seed7-atlas-trace', required=True)
    ap.add_argument('--seed8-baseline-summary', required=True)
    ap.add_argument('--seed8-baseline-atlas-trace', required=True)
    ap.add_argument('--seed8-repaired-summary', required=True)
    ap.add_argument('--seed8-repaired-atlas-trace', required=True)
    ap.add_argument('--seed8-xneg-summary', required=True)
    ap.add_argument('--seed8-rotation-summary', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = build_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_summary_path=args.seed7_summary,
        seed7_atlas_trace_path=args.seed7_atlas_trace,
        seed8_baseline_summary_path=args.seed8_baseline_summary,
        seed8_baseline_atlas_trace_path=args.seed8_baseline_atlas_trace,
        seed8_repaired_summary_path=args.seed8_repaired_summary,
        seed8_repaired_atlas_trace_path=args.seed8_repaired_atlas_trace,
        seed8_xneg_summary_path=args.seed8_xneg_summary,
        seed8_rotation_summary_path=args.seed8_rotation_summary,
    )
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / 'process_summary_translation_x_pos_seed8_inner_shell_x_carrier_generation_restoration_repair_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
