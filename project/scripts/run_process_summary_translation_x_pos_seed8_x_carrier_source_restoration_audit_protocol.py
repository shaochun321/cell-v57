from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_seed8_x_carrier_source_restoration_audit import (
    build_translation_x_pos_seed8_x_carrier_source_restoration_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Audit translation_x_pos seed8 x-carrier source restoration needs.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-summary', required=True)
    ap.add_argument('--seed7-atlas-trace', required=True)
    ap.add_argument('--seed8-summary', required=True)
    ap.add_argument('--seed8-atlas-trace', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_seed8_x_carrier_source_restoration_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_summary_path=args.seed7_summary,
        seed7_atlas_trace_path=args.seed7_atlas_trace,
        seed8_summary_path=args.seed8_summary,
        seed8_atlas_trace_path=args.seed8_atlas_trace,
    )
    out = outdir / 'process_summary_translation_x_pos_seed8_x_carrier_source_restoration_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'audit output: {out}')


if __name__ == '__main__':
    main()
