from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys, os

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--calibration-json', required=True)
    p.add_argument('--outdir', required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(args.calibration_json).read_text(encoding='utf-8'))
    analysis = {
        'suite': 'process_summary_family_polarity_calibration',
        'families': {},
        'cases': payload.get('cases', {}),
        'contracts': payload.get('contracts', {}),
    }
    for family_name, fam in payload.get('families', {}).items():
        analysis['families'][family_name] = {
            'raw_sign_fraction': float(fam.get('raw_sign_fraction', 0.0)),
            'calibrated_sign_fraction': float(fam.get('calibrated_sign_fraction', 0.0)),
            'orientation_flip_detected_fraction': float(fam.get('orientation_flip_detected_fraction', 0.0)),
            'sign_factors': list(fam.get('sign_factors', [])),
            'family_mode_stable': bool(fam.get('family_mode_stable', False)),
        }
    (outdir / 'process_summary_family_polarity_calibration_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    os.environ.setdefault('MPLCONFIGDIR', str(outdir / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    families = list(analysis['families'].keys())
    raw = [analysis['families'][f]['raw_sign_fraction'] for f in families]
    cal = [analysis['families'][f]['calibrated_sign_fraction'] for f in families]
    fig, ax = plt.subplots(figsize=(6,4))
    xs = list(range(len(families)))
    ax.bar([x - 0.15 for x in xs], raw, width=0.3, label='raw')
    ax.bar([x + 0.15 for x in xs], cal, width=0.3, label='calibrated')
    ax.set_xticks(xs)
    ax.set_xticklabels(families)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel('expected sign fraction')
    ax.set_title('Family polarity calibration')
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / 'process_summary_family_polarity_calibration.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
