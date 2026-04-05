from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', required=True)
    parser.add_argument('--outdir', required=True)
    args = parser.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    r52 = float(audit['seed8_round52_frozen_reference']['phase_active_x_summary']['mean_polarity_projection'])
    r58 = float(audit['seed8_round58_m2_2_density']['phase_active_x_summary']['mean_polarity_projection'])
    r59 = float(audit['seed8_round59_m2_3_joint_density']['phase_active_x_summary']['mean_polarity_projection'])
    d58 = float(audit['seed8_round58_m2_2_density']['joint_inner_core_density'])
    d59 = float(audit['seed8_round59_m2_3_joint_density']['joint_inner_core_density'])

    payload = {
        'round52_frozen_seed8_final_mean': r52,
        'round58_m2_2_seed8_final_mean': r58,
        'round59_m2_3_seed8_final_mean': r59,
        'round59_minus_round58_final_mean': float(r59 - r58),
        'round52_minus_round59_gap': float(r52 - r59),
        'round58_joint_inner_core_density': d58,
        'round59_joint_inner_core_density': d59,
        'round59_minus_round58_joint_density': float(d59 - d58),
        'decision': str(audit.get('decision', 'undetermined')),
    }
    (outdir / 'process_summary_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit_analysis.json').write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    plt.figure(figsize=(8, 4.5))
    plt.plot(['round52 frozen', 'round58 m2.2', 'round59 m2.3'], [r52, r58, r59], marker='o')
    plt.ylabel('seed8 translation_x_pos final active mean')
    plt.title('M2.3 joint shell0/shell1 density redesign')
    plt.tight_layout()
    plt.savefig(outdir / 'process_summary_translation_x_pos_m2_3_joint_shell0_shell1_high_amplitude_density_formation_redesign_audit.png', dpi=160)


if __name__ == '__main__':
    main()
