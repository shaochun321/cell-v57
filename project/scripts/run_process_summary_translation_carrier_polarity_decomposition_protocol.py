from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_carrier_polarity_decomposition import (
    decompose_translation_carrier_polarity_files,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        '--carrier-audit',
        default=str(ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json'),
    )
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, str | dict]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = decompose_translation_carrier_polarity_files(carrier_audit_path=args.carrier_audit)
    out_path = outdir / 'process_summary_translation_carrier_polarity_decomposition.json'
    out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return {'decomposition_path': str(out_path), 'decomposition': payload}


def main() -> None:
    args = parse_args()
    result = run_protocol(args)
    print(result['decomposition_path'])


if __name__ == '__main__':
    main()
