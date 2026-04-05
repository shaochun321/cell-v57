from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit import (
    build_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit,
)


def main() -> None:
    ap = argparse.ArgumentParser(description='Run translation_x_pos x-family carrier margin strengthening repair audit.')
    ap.add_argument('--previous-round-audit', required=True)
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-summary-analysis', required=True)
    ap.add_argument('--seed8-summary-analysis', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit(
        previous_round_audit_path=args.previous_round_audit,
        repeatability_audit_path=args.repeatability_audit,
        seed7_summary_analysis_path=args.seed7_summary_analysis,
        seed8_summary_analysis_path=args.seed8_summary_analysis,
    )
    (outdir / 'process_summary_translation_x_pos_x_family_carrier_margin_strengthening_repair_audit.json').write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
