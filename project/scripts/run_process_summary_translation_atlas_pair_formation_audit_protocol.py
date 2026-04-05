from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_atlas_pair_formation_audit import (
    audit_translation_atlas_pair_formation_files,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        '--repeatability-report',
        default=str(ROOT / 'outputs/process_summary_repeatability_r1/process_summary_repeatability_protocol_report.json'),
    )
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, str | dict]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    audit = audit_translation_atlas_pair_formation_files(
        repeatability_report_path=args.repeatability_report,
    )
    audit_path = outdir / 'process_summary_translation_atlas_pair_formation_audit.json'
    audit_path.write_text(json.dumps(audit, indent=2), encoding='utf-8')
    return {'audit_path': str(audit_path), 'audit': audit}


def main() -> None:
    args = parse_args()
    result = run_protocol(args)
    print(result['audit_path'])


if __name__ == '__main__':
    main()
