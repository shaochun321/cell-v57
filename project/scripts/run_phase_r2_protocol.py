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

from cell_sphere_core.analysis.phase_r2 import summarize_phase_r2_audit
from cell_sphere_core.engine.main_loop import GravityConfig, run_gravity


def parse_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(',') if part.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run Phase R.2 focused rotation sensitivity audit.')
    p.add_argument('--num-cells', type=int, default=70)
    p.add_argument('--t-end', type=float, default=0.12)
    p.add_argument('--dt', type=float, default=0.001)
    p.add_argument('--translation-accel', type=float, default=80.0)
    p.add_argument('--rotation-alphas', type=str, default='420,460,500,540')
    p.add_argument('--swirl-gains', type=str, default='1.00,1.10,1.20,1.30')
    p.add_argument('--outdir', type=str, default='outputs/phase_r2_sample')
    return p.parse_args()


def _extract_report(summary: dict) -> dict:
    return dict(summary.get('channel_motif_diagnostics', {}))


def _run_one(base_outdir: Path, name: str, *, num_cells: int, t_end: float, dt: float, translation_accel: float, rotation_alpha: float, swirl_gain: float = 1.0, circulation_gain: float = 1.10, axial_base: float = 0.90, transfer_base: float = 0.96, circulation_feed: float = 0.18, **kwargs) -> dict:
    cfg = GravityConfig(
        num_cells=num_cells,
        t_end=t_end,
        dt=dt,
        disable_gravity=True,
        sensor_record_every=10,
        record_every=10,
        vestibular_onset_fraction=0.20,
        vestibular_duration_fraction=0.60,
        interface_layered_rotation_swirl_gain=swirl_gain,
        interface_layered_rotation_circulation_gain=circulation_gain,
        interface_layered_rotation_axial_base=axial_base,
        interface_layered_rotation_transfer_base=transfer_base,
        interface_layered_rotation_circulation_feed=circulation_feed,
        **kwargs,
    )
    outdir = base_outdir / name
    result = run_gravity(cfg, outdir=outdir, save_outputs=True)
    return {'summary': result.summary, 'motif_report': _extract_report(result.summary)}


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
        }
    }
    # translation guard uses central-ish settings, not tuned for best-score hunting.
    central_alpha = alphas[len(alphas) // 2] if alphas else 500.0
    central_gain = gains[len(gains) // 2] if gains else 1.0
    report['translation_guard'] = _run_one(
        outdir,
        'translation_guard',
        num_cells=args.num_cells,
        t_end=args.t_end,
        dt=args.dt,
        translation_accel=args.translation_accel,
        rotation_alpha=central_alpha,
        swirl_gain=central_gain,
        circulation_gain=1.05 + 0.20 * (central_gain - 1.0),
        axial_base=max(0.72, 0.90 - 0.10 * max(0.0, central_gain - 1.0)),
        transfer_base=min(1.05, 0.96 + 0.04 * max(0.0, central_gain - 1.0)),
        vestibular_motion='translation',
        vestibular_linear_accel=args.translation_accel,
        vestibular_linear_axis='x',
        vestibular_linear_sign=1.0,
    )

    scan_rows = []
    for alpha in alphas:
        for gain in gains:
            circulation_gain = 1.05 + 0.22 * (gain - 1.0)
            axial_base = max(0.70, 0.90 - 0.14 * max(0.0, gain - 1.0))
            transfer_base = min(1.05, 0.96 + 0.05 * max(0.0, gain - 1.0))
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
                    outdir,
                    case_id + '_pos',
                    num_cells=args.num_cells,
                    t_end=args.t_end,
                    dt=args.dt,
                    translation_accel=args.translation_accel,
                    rotation_alpha=alpha,
                    swirl_gain=gain,
                    circulation_gain=circulation_gain,
                    axial_base=axial_base,
                    transfer_base=transfer_base,
                    circulation_feed=circulation_feed,
                    vestibular_motion='rotation',
                    vestibular_angular_accel=alpha,
                    vestibular_rotation_axis='z',
                    vestibular_rotation_sign=1.0,
                ),
                'rotation_neg': _run_one(
                    outdir,
                    case_id + '_neg',
                    num_cells=args.num_cells,
                    t_end=args.t_end,
                    dt=args.dt,
                    translation_accel=args.translation_accel,
                    rotation_alpha=alpha,
                    swirl_gain=gain,
                    circulation_gain=circulation_gain,
                    axial_base=axial_base,
                    transfer_base=transfer_base,
                    circulation_feed=circulation_feed,
                    vestibular_motion='rotation',
                    vestibular_angular_accel=alpha,
                    vestibular_rotation_axis='z',
                    vestibular_rotation_sign=-1.0,
                ),
            })
    report['rotation_scan'] = scan_rows
    report_path = outdir / 'phase_r2_protocol_report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    audit = summarize_phase_r2_audit(report)
    audit_path = outdir / 'phase_r2_audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'输出目录: {outdir}')
    print(f'协议报告: {report_path}')
    print(f'Phase R.2 审计: {audit_path}')


if __name__ == '__main__':
    main()
