from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit import (
    build_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--round52-seed8-summary', required=True)
    parser.add_argument('--round59-seed8-summary', required=True)
    parser.add_argument('--round59-seed8-atlas-trace', required=True)
    parser.add_argument('--round60-seed8-summary', required=True)
    parser.add_argument('--round60-seed8-atlas-trace', required=True)
    parser.add_argument('--round60-seed8-xneg-summary', required=True)
    parser.add_argument('--round60-seed8-rotation-pos-summary', required=True)
    parser.add_argument('--round60-seed8-rotation-neg-summary', required=True)
    parser.add_argument('--repeatability-audit', required=True)
    parser.add_argument('--outdir', required=True)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = build_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit(
        round52_seed8_summary_path=args.round52_seed8_summary,
        round59_seed8_summary_path=args.round59_seed8_summary,
        round59_seed8_atlas_trace_path=args.round59_seed8_atlas_trace,
        round60_seed8_summary_path=args.round60_seed8_summary,
        round60_seed8_atlas_trace_path=args.round60_seed8_atlas_trace,
        round60_seed8_xneg_summary_path=args.round60_seed8_xneg_summary,
        round60_seed8_rotation_pos_summary_path=args.round60_seed8_rotation_pos_summary,
        round60_seed8_rotation_neg_summary_path=args.round60_seed8_rotation_neg_summary,
        repeatability_audit_path=args.repeatability_audit,
    )
    outpath = outdir / 'process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit.json'
    outpath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(outpath)


if __name__ == '__main__':
    main()
