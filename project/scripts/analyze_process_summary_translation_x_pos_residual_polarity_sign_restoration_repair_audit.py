from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze translation_x_pos residual polarity sign restoration repair audit.")
    ap.add_argument("--audit", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    analysis = {
        "suite": audit["suite"],
        "contracts": audit["contracts"],
        "inferred_outcome": audit["inferred_outcome"],
        "residual_issue": audit["residual_issue"],
        "seed7": audit["seed7"],
        "seed8": audit["seed8"],
    }
    (outdir / "process_summary_translation_x_pos_residual_polarity_sign_restoration_repair_audit_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    labels = ["seed7 x_pos", "seed8 x_pos", "seed7 x_neg", "seed8 x_neg"]
    values = [
        float(audit["seed7"]["translation_x_pos"]["active_mean_polarity_projection"]),
        float(audit["seed8"]["translation_x_pos"]["active_mean_polarity_projection"]),
        float(audit["seed7"]["translation_x_neg"]["active_mean_polarity_projection"]),
        float(audit["seed8"]["translation_x_neg"]["active_mean_polarity_projection"]),
    ]

    fig = plt.figure(figsize=(8, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.bar(labels, values)
    ax.axhline(0.0, linewidth=1.0)
    ax.set_ylabel("active mean polarity projection")
    ax.set_title("Round35 translation x-family polarity sign restoration")
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(outdir / "process_summary_translation_x_pos_residual_polarity_sign_restoration_repair_audit.png", dpi=160)


if __name__ == "__main__":
    main()
