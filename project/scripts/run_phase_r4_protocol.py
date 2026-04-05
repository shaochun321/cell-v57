from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
SRC_DIR = PROJECT_ROOT / 'src'
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_ROOT / '.mplconfig'))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.phase_r4 import summarize_phase_r4_audit
from run_phase_r2_protocol import parse_list, _run_one


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run Phase R.4 directional extension audit for rotation stability.')
    p.add_argument('--num-cells', type=int, default=70)
    p.add_argument('--t-end', type=float, default=0.12)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--translation-accel', type=float, default=80.0)
    p.add_argument('--rotation-alphas', type=str, default='300,340,380,420,460')
    p.add_argument('--swirl-gains', type=str, default='0.90,1.00,1.10,1.20,1.30')
    p.add_argument('--outdir', type=str, default='outputs/phase_r4_sample')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    alphas = parse_list(args.rotation_alphas)
    gains = parse_list(args.swirl_gains)
    report: dict[str, object] = {
        'metadata': {
            'rotation_alphas': alphas,
            'swirl_gains': gains,
            'num_cells': args.num_cells,
            't_end': args.t_end,
            'dt': args.dt,
            'phase': 'Phase R.4',
            'frontier_direction': 'lower_alpha',
        }
    }
    central_alpha = alphas[min(len(alphas)//2, len(alphas)-1)] if alphas else 420.0
    central_gain = gains[min(len(gains)//2, len(gains)-1)] if gains else 1.1
    report['translation_guard'] = _run_one(
        outdir, 'translation_guard',
        num_cells=args.num_cells, t_end=args.t_end, dt=args.dt,
        translation_accel=args.translation_accel, rotation_alpha=central_alpha,
        swirl_gain=central_gain,
        circulation_gain=1.05 + 0.22 * (central_gain - 1.0),
        axial_base=max(0.66, 0.90 - 0.14 * max(0.0, central_gain - 1.0)),
        transfer_base=min(1.06, 0.96 + 0.05 * max(0.0, central_gain - 1.0)),
        circulation_feed=0.18 + 0.08 * max(0.0, central_gain - 1.0),
        vestibular_motion='translation', vestibular_linear_accel=args.translation_accel,
        vestibular_linear_axis='x', vestibular_linear_sign=1.0,
    )

    scan_rows = []
    for alpha in alphas:
        for gain in gains:
            circulation_gain = 1.05 + 0.22 * (gain - 1.0)
            axial_base = max(0.66, 0.90 - 0.14 * max(0.0, gain - 1.0))
            transfer_base = min(1.06, 0.96 + 0.05 * max(0.0, gain - 1.0))
            circulation_feed = 0.18 + 0.08 * max(0.0, gain - 1.0)
            case_id = f'rot_a{alpha:.0f}_g{gain:.2f}'
            scan_rows.append({
                'case_id': case_id,
                'rotation_alpha': alpha,
                'swirl_gain': gain,
                'circulation_gain': circulation_gain,
                'axial_base': axial_base,
                'transfer_base': transfer_base,
                'circulation_feed': circulation_feed,
                'rotation_pos': _run_one(
                    outdir, case_id + '_pos',
                    num_cells=args.num_cells, t_end=args.t_end, dt=args.dt,
                    translation_accel=args.translation_accel, rotation_alpha=alpha,
                    swirl_gain=gain, circulation_gain=circulation_gain,
                    axial_base=axial_base, transfer_base=transfer_base,
                    circulation_feed=circulation_feed,
                    vestibular_motion='rotation', vestibular_angular_accel=alpha,
                    vestibular_rotation_axis='z', vestibular_rotation_sign=1.0,
                ),
                'rotation_neg': _run_one(
                    outdir, case_id + '_neg',
                    num_cells=args.num_cells, t_end=args.t_end, dt=args.dt,
                    translation_accel=args.translation_accel, rotation_alpha=alpha,
                    swirl_gain=gain, circulation_gain=circulation_gain,
                    axial_base=axial_base, transfer_base=transfer_base,
                    circulation_feed=circulation_feed,
                    vestibular_motion='rotation', vestibular_angular_accel=alpha,
                    vestibular_rotation_axis='z', vestibular_rotation_sign=-1.0,
                ),
            })
    report['rotation_scan'] = scan_rows
    report_path = outdir / 'phase_r4_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = summarize_phase_r4_audit(report)
    audit_path = outdir / 'phase_r4_audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'协议报告: {report_path}')
    print(f'Phase R.4 审计: {audit_path}')


if __name__ == '__main__':
    main()
