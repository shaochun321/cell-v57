from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit import (
    build_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run the M2.2 inner-core amplitude density redesign audit.')
    ap.add_argument('--round52-seed8-summary', required=True)
    ap.add_argument('--round57-seed8-summary', required=True)
    ap.add_argument('--round57-seed8-atlas-trace', required=True)
    ap.add_argument('--round58-seed8-summary', required=True)
    ap.add_argument('--round58-seed8-atlas-trace', required=True)
    ap.add_argument('--round58-seed8-xneg-summary', required=True)
    ap.add_argument('--round58-seed8-rotation-pos-summary', required=True)
    ap.add_argument('--round58-seed8-rotation-neg-summary', required=True)
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = build_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit(
        round52_seed8_summary_path=args.round52_seed8_summary,
        round57_seed8_summary_path=args.round57_seed8_summary,
        round57_seed8_atlas_trace_path=args.round57_seed8_atlas_trace,
        round58_seed8_summary_path=args.round58_seed8_summary,
        round58_seed8_atlas_trace_path=args.round58_seed8_atlas_trace,
        round58_seed8_xneg_summary_path=args.round58_seed8_xneg_summary,
        round58_seed8_rotation_pos_summary_path=args.round58_seed8_rotation_pos_summary,
        round58_seed8_rotation_neg_summary_path=args.round58_seed8_rotation_neg_summary,
        repeatability_audit_path=args.repeatability_audit,
    )
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / 'process_summary_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
