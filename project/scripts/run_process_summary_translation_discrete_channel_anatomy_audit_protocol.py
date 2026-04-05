from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cell_sphere_core.analysis.process_summary_translation_discrete_channel_anatomy_audit import audit_translation_discrete_channel_anatomy_files


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--carrier-json', default=str(ROOT / 'outputs/process_summary_translation_interface_family_carrier_audit_r1/process_summary_translation_interface_family_carrier_audit.json'))
    p.add_argument('--decomposition-json', default=str(ROOT / 'outputs/process_summary_translation_carrier_polarity_decomposition_r1/process_summary_translation_carrier_polarity_decomposition.json'))
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def run_protocol(args: argparse.Namespace) -> dict[str, str | dict]:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = audit_translation_discrete_channel_anatomy_files(carrier_path=args.carrier_json, decomposition_path=args.decomposition_json)
    out_path = outdir / 'process_summary_translation_discrete_channel_anatomy_audit.json'
    out_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return {'audit_path': str(out_path), 'audit': payload}


def main() -> None:
    args = parse_args()
    result = run_protocol(args)
    print(result['audit_path'])


if __name__ == '__main__':
    main()
