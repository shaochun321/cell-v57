from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cell_sphere_core.analysis.process_summary_family_guided_consensus import summarize_family_guided_case_consensus_files


def run_protocol(args: argparse.Namespace) -> dict[str, Any]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    consensus = summarize_family_guided_case_consensus_files(
        repeatability_report_path=args.repeatability_report,
        family_audit_path=args.family_audit,
    )
    outpath = outdir / 'process_summary_family_guided_case_consensus.json'
    outpath.write_text(json.dumps(consensus, indent=2), encoding='utf-8')
    return {
        'outdir': str(outdir),
        'consensus': consensus,
        'consensus_path': str(outpath),
    }


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Build family-guided case consensus from repeatability outputs.')
    p.add_argument('--repeatability-report', required=True)
    p.add_argument('--family-audit', required=True)
    p.add_argument('--outdir', required=True)
    return p


def main() -> None:
    args = build_argparser().parse_args()
    payload = run_protocol(args)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
