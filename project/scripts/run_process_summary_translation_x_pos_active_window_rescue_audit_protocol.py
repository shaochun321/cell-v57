from __future__ import annotations

import argparse
import json
from pathlib import Path

from cell_sphere_core.analysis.process_summary_translation_x_pos_active_window_rescue_audit import build_translation_x_pos_active_window_rescue_audit


def main() -> None:
    ap = argparse.ArgumentParser(description='Audit remaining translation_x_pos active-window failure after gate-weighted selection.')
    ap.add_argument('--repeatability-audit', required=True)
    ap.add_argument('--seed7-analysis', required=True)
    ap.add_argument('--seed8-analysis', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = build_translation_x_pos_active_window_rescue_audit(
        repeatability_audit_path=args.repeatability_audit,
        seed7_analysis_path=args.seed7_analysis,
        seed8_analysis_path=args.seed8_analysis,
    )
    out = outdir / 'process_summary_translation_x_pos_active_window_rescue_audit.json'
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'审计输出: {out}')


if __name__ == '__main__':
    main()
