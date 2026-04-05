from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze the M2.2 inner-core amplitude density redesign audit.')
    ap.add_argument('--audit', required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    r52 = float(audit['seed8_round52_frozen_reference']['phase_active_x_summary']['mean_polarity_projection'])
    r57 = float(audit['seed8_round57_m2_continuity']['phase_active_x_summary']['mean_polarity_projection'])
    r58 = float(audit['seed8_round58_m2_2_density']['phase_active_x_summary']['mean_polarity_projection'])
    payload = {
        'round52_frozen_seed8_final_mean': r52,
        'round57_m2_seed8_final_mean': r57,
        'round58_m2_2_seed8_final_mean': r58,
        'round58_minus_round57_final_mean': float(audit['deltas']['round58_minus_round57_final_mean']),
        'round52_minus_round58_gap': float(audit['deltas']['round52_minus_round58_gap']),
        'decision': audit['decision'],
    }
    (outdir / 'process_summary_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit_analysis.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    plt.figure(figsize=(6.4, 4.2))
    labels = ['round52\nfrozen', 'round57\nm2', 'round58\nm2.2']
    values = [r52, r57, r58]
    plt.bar(labels, values)
    plt.ylabel('seed8 active x mean polarity')
    plt.title('M2.2 inner-core amplitude density redesign')
    plt.tight_layout()
    plt.savefig(outdir / 'process_summary_translation_x_pos_m2_2_inner_core_amplitude_density_redesign_audit.png', dpi=160)


if __name__ == '__main__':
    main()
