
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "outputs" / "m2_4_material_baseline_recheck_audit"
    audit_path = out_dir / "process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.json"
    audit = json.loads(audit_path.read_text())

    analysis = {
        "round52_frozen_seed8_final_mean": audit["round52_frozen_reference"]["final_active_mean"],
        "round59_m2_3_seed8_final_mean": audit["round59_m2_3_reference"]["final_active_mean"],
        "round60_m2_4_seed8_final_mean": audit["round60_m2_4_candidate"]["final_active_mean"],
        "round60_minus_round59_final_mean": audit["evidence"]["final_gain_vs_round59"],
        "round52_minus_round60_gap": audit["evidence"]["gap_to_frozen_round52"],
        "round52_translation_support": audit["round52_frozen_reference"]["translation_support"],
        "round60_translation_support": audit["round60_m2_4_candidate"]["translation_support"],
        "round52_translation_carriers": audit["round52_frozen_reference"]["translation_carrier_pair_count"],
        "round60_translation_carriers": audit["round60_m2_4_candidate"]["translation_carrier_pair_count"],
        "decision": audit["decision"],
    }
    analysis_path = out_dir / "process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit_analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2))

    fig_path = out_dir / "process_summary_translation_x_pos_m2_4_material_baseline_recheck_audit.png"
    labels = ["round52 frozen", "round59 m2.3", "round60 m2.4"]
    values = [
        analysis["round52_frozen_seed8_final_mean"],
        analysis["round59_m2_3_seed8_final_mean"],
        analysis["round60_m2_4_seed8_final_mean"],
    ]
    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.ylabel("seed8 translation_x_pos final active mean")
    plt.title("M2.4 baseline recheck")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=160)
    plt.close()

    print(analysis_path)
    print(fig_path)

if __name__ == "__main__":
    main()
