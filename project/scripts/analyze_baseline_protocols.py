from __future__ import annotations

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt

TRACKS = ['discrete_channel_track', 'local_propagation_track', 'layered_coupling_track']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze compact baseline protocol results.')
    p.add_argument('--input', required=True, type=str)
    p.add_argument('--title', type=str, default='Baseline protocol analysis')
    p.add_argument('--output', required=True, type=str)
    return p.parse_args()


def _track(report_case: dict, track: str) -> dict:
    return report_case.get('interface_network_diagnostics', {}).get('tracks', {}).get(track, {})


def _track_active_channels(report_case: dict, track: str) -> dict:
    return _track(report_case, track).get('active_summary', {}).get('mean_global_channels', {})


def _x_balance(report_case: dict, track: str, *, active: bool) -> float:
    payload = _track(report_case, track)
    source = payload.get('active_summary', {}) if active else payload
    axis_balance = source.get('axis_balance', {})
    return float(axis_balance.get('x', 0.0))


def _signed_circulation(report_case: dict, track: str, *, active: bool) -> float:
    payload = _track(report_case, track)
    source = payload.get('active_summary', {}) if active else payload
    circ_balance = source.get('circulation_axis_balance', {})
    return float(circ_balance.get('z', 0.0))


def build_analysis(report: dict) -> dict:
    cases = report['cases']
    static_case = cases['floating_static']
    analysis = {
        'suite': 'baseline_protocols',
        'static': {
            'near_sphere_score': float(static_case.get('near_sphere_score', 0.0)),
            'tail_kinetic_mean': float(static_case.get('equilibrium_diagnostics', {}).get('tail_kinetic_mean', 0.0)),
            'quasi_static': bool(static_case.get('equilibrium_diagnostics', {}).get('is_quasi_static', False)),
            'floor_contact_ratio': float(static_case.get('final_metrics', {}).get('floor_contact_ratio', 0.0)),
        },
        'translation': {'tracks': {}},
        'rotation': {'tracks': {}},
    }
    for track in TRACKS:
        pos_case = cases['translation_x_pos']
        neg_case = cases['translation_x_neg']
        pos_active = _track_active_channels(pos_case, track)
        neg_active = _track_active_channels(neg_case, track)
        pos_margin = float(pos_active.get('axial_flux', 0.0) - pos_active.get('swirl_flux', 0.0))
        neg_margin = float(neg_active.get('axial_flux', 0.0) - neg_active.get('swirl_flux', 0.0))
        xb_pos = _x_balance(pos_case, track, active=True)
        xb_neg = _x_balance(neg_case, track, active=True)
        analysis['translation']['tracks'][track] = {
            'translation_margin_pos': pos_margin,
            'translation_margin_neg': neg_margin,
            'x_axis_balance_pos': xb_pos,
            'x_axis_balance_neg': xb_neg,
            'sign_flip': bool(xb_pos * xb_neg < 0.0),
            'mean_translation_margin': 0.5 * (pos_margin + neg_margin),
            'x_axis_balance_abs_mean': 0.5 * (abs(xb_pos) + abs(xb_neg)),
        }

        pos_case = cases['rotation_z_pos']
        neg_case = cases['rotation_z_neg']
        pos_active = _track_active_channels(pos_case, track)
        neg_active = _track_active_channels(neg_case, track)
        pos_margin = float(pos_active.get('swirl_flux', 0.0) - pos_active.get('axial_flux', 0.0))
        neg_margin = float(neg_active.get('swirl_flux', 0.0) - neg_active.get('axial_flux', 0.0))
        circ_pos = _signed_circulation(pos_case, track, active=True)
        circ_neg = _signed_circulation(neg_case, track, active=True)
        analysis['rotation']['tracks'][track] = {
            'rotation_margin_pos': pos_margin,
            'rotation_margin_neg': neg_margin,
            'signed_circulation_pos': circ_pos,
            'signed_circulation_neg': circ_neg,
            'sign_flip': bool(circ_pos * circ_neg < 0.0),
            'mean_rotation_margin': 0.5 * (pos_margin + neg_margin),
            'signed_circulation_abs_mean': 0.5 * (abs(circ_pos) + abs(circ_neg)),
        }
    return analysis


def render_png(analysis: dict, output_dir: Path, title: str) -> None:
    tracks = TRACKS
    tvals = [analysis['translation']['tracks'][t]['mean_translation_margin'] for t in tracks]
    rvals = [analysis['rotation']['tracks'][t]['mean_rotation_margin'] for t in tracks]
    plt.figure(figsize=(8, 4))
    xs = list(range(len(tracks)))
    plt.plot(xs, tvals, marker='o', label='translation margin')
    plt.plot(xs, rvals, marker='o', label='rotation margin')
    plt.xticks(xs, [t.replace('_track', '') for t in tracks], rotation=15)
    plt.ylabel('mean active margin')
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'baseline_protocol_overview.png', dpi=180)
    plt.close()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = json.loads(input_path.read_text(encoding='utf-8'))
    analysis = build_analysis(report)
    (output_dir / 'baseline_protocol_analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
    render_png(analysis, output_dir, args.title)


if __name__ == '__main__':
    main()
