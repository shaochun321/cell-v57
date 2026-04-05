from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_family_polarity_calibration import summarize_family_polarity_calibration_files


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--repeatability-report', required=True)
    p.add_argument('--family-consensus', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = summarize_family_polarity_calibration_files(
        repeatability_report_path=args.repeatability_report,
        family_consensus_path=args.family_consensus,
    )
    out = outdir / 'process_summary_family_polarity_calibration.json'
    out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
