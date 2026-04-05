from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze translation_x_pos seed8 active x-carrier ultraweak-row exclusion tightening repair audit.")
    ap.add_argument("--audit", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    (outdir / "process_summary_translation_x_pos_seed8_active_x_carrier_ultraweak_row_exclusion_tightening_repair_audit_analysis.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    seed7 = audit["seed7"]["translation_x_pos"]
    seed8 = audit["seed8"]["translation_x_pos"]
    labels = [
        "seed7 active mean",
        "round44 seed8 active mean",
        "seed8 raw mean",
        "seed8 carrier-floor weighted",
    ]
    values = [
        float(seed7["active_mean_polarity_projection"]),
        float(seed8["active_mean_polarity_projection"]),
        float(seed8["active_raw_mean_polarity_projection"]),
        float(seed8["active_carrier_floor_weighted_polarity_projection"]),
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, values)
    ax.set_ylabel("polarity projection")
    ax.set_title("Round45 translation_x_pos seed8 active x-carrier ultraweak-row exclusion tightening")
    ax.tick_params(axis="x", rotation=20)
    ax.axhline(0.0, linewidth=1.0)
    fig.tight_layout()
    fig.savefig(outdir / "process_summary_translation_x_pos_seed8_active_x_carrier_ultraweak_row_exclusion_tightening_repair_audit.png", dpi=160)


if __name__ == "__main__":
    main()
