from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_inner_core_source_continuity_redesign_audit import (
    build_translation_x_pos_m2_inner_core_source_continuity_redesign_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run the M2 inner-core source continuity redesign audit.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-reference-summary', required=True)
    ap.add_argument('--seed8-baseline-summary', required=True)
    ap.add_argument('--seed8-baseline-atlas-trace', required=True)
    ap.add_argument('--seed8-repaired-summary', required=True)
    ap.add_argument('--seed8-repaired-atlas-trace', required=True)
    ap.add_argument('--seed8-xneg-summary', required=True)
    ap.add_argument('--seed8-rotation-pos-summary', required=True)
    ap.add_argument('--seed8-rotation-neg-summary', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = build_translation_x_pos_m2_inner_core_source_continuity_redesign_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_reference_summary_path=args.seed7_reference_summary,
        seed8_baseline_summary_path=args.seed8_baseline_summary,
        seed8_baseline_atlas_trace_path=args.seed8_baseline_atlas_trace,
        seed8_repaired_summary_path=args.seed8_repaired_summary,
        seed8_repaired_atlas_trace_path=args.seed8_repaired_atlas_trace,
        seed8_xneg_summary_path=args.seed8_xneg_summary,
        seed8_rotation_pos_summary_path=args.seed8_rotation_pos_summary,
        seed8_rotation_neg_summary_path=args.seed8_rotation_neg_summary,
    )
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / 'process_summary_translation_x_pos_m2_inner_core_source_continuity_redesign_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
