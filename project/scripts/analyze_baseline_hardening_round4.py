from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

TRACKS = ['discrete_channel_track', 'local_propagation_track', 'layered_coupling_track']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze baseline hardening round 4 results.')
    p.add_argument('--input', required=True, type=str)
    p.add_argument('--title', type=str, default='Baseline Hardening Round 4')
    p.add_argument('--output', required=True, type=str)
    return p.parse_args()


def _track(case: dict, track: str) -> dict:
    return case.get('interface_network_diagnostics', {}).get('tracks', {}).get(track, {})


def _active(case: dict, track: str) -> dict:
    return _track(case, track).get('active_summary', {})


def build_analysis(report: dict) -> dict:
    cases = report['cases']
    static_case = cases['floating_static']
    eq = static_case.get('equilibrium_diagnostics', {})
    analysis = {
        'suite': 'baseline_hardening_round4',
        'static': {
            'near_sphere_score': float(static_case.get('near_sphere_score', 0.0)),
            'tail_kinetic_mean': float(eq.get('tail_kinetic_mean', 0.0)),
            'tail_volume_ratio_mean': float(eq.get('tail_volume_ratio_mean', 0.0)),
            'tail_shape_mean': float(eq.get('tail_shape_mean', 0.0)),
            'quietness_score': float(1.0 / (1.0 + eq.get('tail_kinetic_mean', 0.0))),
            'shape_score': float(eq.get('tail_volume_ratio_mean', 0.0) / max(1.0 + eq.get('tail_shape_mean', 0.0), 1e-9)),
        },
        'translation': {'tracks': {}},
        'rotation': {'tracks': {}},
    }
    for track in TRACKS:
        txp = _active(cases['translation_x_pos'], track)
        txn = _active(cases['translation_x_neg'], track)
        x_pos = float(txp.get('axis_balance', {}).get('x', 0.0))
        x_neg = float(txn.get('axis_balance', {}).get('x', 0.0))
        tx_margin_pos = float(txp.get('mean_global_channels', {}).get('axial_flux', 0.0) - txp.get('mean_global_channels', {}).get('swirl_flux', 0.0))
        tx_margin_neg = float(txn.get('mean_global_channels', {}).get('axial_flux', 0.0) - txn.get('mean_global_channels', {}).get('swirl_flux', 0.0))
        analysis['translation']['tracks'][track] = {
            'x_axis_balance_pos': x_pos,
            'x_axis_balance_neg': x_neg,
            'sign_flip': bool(x_pos * x_neg < 0.0),
            'x_axis_balance_abs_mean': 0.5 * (abs(x_pos) + abs(x_neg)),
            'mean_translation_margin': 0.5 * (tx_margin_pos + tx_margin_neg),
        }

        rzp = _active(cases['rotation_z_pos'], track)
        rzn = _active(cases['rotation_z_neg'], track)
        z_pos = float(rzp.get('circulation_axis_balance', {}).get('z', 0.0))
        z_neg = float(rzn.get('circulation_axis_balance', {}).get('z', 0.0))
        margin_pos = float(rzp.get('mean_global_channels', {}).get('swirl_flux', 0.0) - rzp.get('mean_global_channels', {}).get('axial_flux', 0.0))
        margin_neg = float(rzn.get('mean_global_channels', {}).get('swirl_flux', 0.0) - rzn.get('mean_global_channels', {}).get('axial_flux', 0.0))
        analysis['rotation']['tracks'][track] = {
            'signed_circulation_pos': z_pos,
            'signed_circulation_neg': z_neg,
            'sign_flip': bool(z_pos * z_neg < 0.0),
            'signed_circulation_abs_mean': 0.5 * (abs(z_pos) + abs(z_neg)),
            'mean_rotation_margin': 0.5 * (margin_pos + margin_neg),
        }
    return analysis


def render_png(analysis: dict, output_dir: Path, title: str) -> None:
    tracks = TRACKS
    quiet = analysis['static']['quietness_score']
    tx = [analysis['translation']['tracks'][t]['x_axis_balance_abs_mean'] for t in tracks]
    rz = [analysis['rotation']['tracks'][t]['signed_circulation_abs_mean'] for t in tracks]
    txm = [analysis['translation']['tracks'][t]['mean_translation_margin'] for t in tracks]
    rzm = [analysis['rotation']['tracks'][t]['mean_rotation_margin'] for t in tracks]
    xs = list(range(len(tracks)))
    plt.figure(figsize=(9, 4.5))
    plt.plot(xs, tx, marker='o', label='translation |x-balance| mean')
    plt.plot(xs, rz, marker='o', label='rotation |z-circulation| mean')
    plt.plot(xs, txm, marker='o', label='translation axial-swirl margin')
    plt.plot(xs, rzm, marker='o', label='rotation swirl-axial margin')
    plt.axhline(quiet, linestyle='--', label='static quietness score')
    plt.xticks(xs, [t.replace('_track', '') for t in tracks], rotation=15)
    plt.ylabel('response / quietness scale')
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'baseline_hardening_round4_overview.png', dpi=180)
    plt.close()


def main() -> None:
    args = parse_args()
    report = json.loads(Path(args.input).read_text(encoding='utf-8'))
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(report)
    (output_dir / 'baseline_hardening_round4_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, args.title)


if __name__ == '__main__':
    main()
