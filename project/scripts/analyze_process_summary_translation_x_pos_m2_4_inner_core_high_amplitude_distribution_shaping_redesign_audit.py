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
    r59 = float(audit['seed8_round59_m2_3_joint_density']['phase_active_x_summary']['mean_polarity_projection'])
    r60 = float(audit['seed8_round60_m2_4_distribution_shaping']['phase_active_x_summary']['mean_polarity_projection'])
    d59 = float(audit['seed8_round59_m2_3_joint_density']['inner_core_density'])
    d60 = float(audit['seed8_round60_m2_4_distribution_shaping']['inner_core_density'])
    payload = {
        'round52_frozen_seed8_final_mean': r52,
        'round59_m2_3_seed8_final_mean': r59,
        'round60_m2_4_seed8_final_mean': r60,
        'round60_minus_round59_final_mean': float(r60 - r59),
        'round52_minus_round60_gap': float(r52 - r60),
        'round59_inner_core_density': d59,
        'round60_inner_core_density': d60,
        'round60_minus_round59_inner_core_density': float(d60 - d59),
        'decision': str(audit.get('decision', 'undetermined')),
    }
    (outdir / 'process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit_analysis.json').write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    plt.figure(figsize=(8, 4.5))
    plt.plot(['round52 frozen', 'round59 m2.3', 'round60 m2.4'], [r52, r59, r60], marker='o')
    plt.ylabel('seed8 translation_x_pos final active mean')
    plt.title('M2.4 inner-core high-amplitude distribution shaping redesign')
    plt.tight_layout()
    plt.savefig(outdir / 'process_summary_translation_x_pos_m2_4_inner_core_high_amplitude_distribution_shaping_redesign_audit.png', dpi=160)


if __name__ == '__main__':
    main()
