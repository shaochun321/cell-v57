from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_sign_source_audit import audit_translation_sign_source_files


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--repeatability-report', required=True)
    p.add_argument('--polarity-calibration', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, str | dict]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = audit_translation_sign_source_files(
        repeatability_report_path=args.repeatability_report,
        polarity_calibration_path=args.polarity_calibration,
    )
    out = outdir / 'process_summary_translation_sign_source_audit.json'
    out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return {'audit': payload, 'audit_path': str(out)}


def main() -> None:
    args = parse_args()
    result = run_protocol(args)
    print(result['audit_path'])


if __name__ == '__main__':
    main()
