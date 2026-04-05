from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import os

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cell_sphere_core.analysis.channel_invariants import summarize_channel_invariants
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze cross-protocol motif invariants.")
    p.add_argument("--input", type=str, required=True, help="Path to step27_protocol_report.json or step27_invariants.json")
    p.add_argument("--title", type=str, default="Step 27 channel invariant analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if "tracks" in payload and "principle" in payload:
        invariants = payload
    else:
        invariants = summarize_channel_invariants(payload)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    report = {"title": args.title, "invariants": invariants, "external_readout": {}}
    for track_name in TRACK_NAMES:
        track = invariants["tracks"][track_name]
        report["external_readout"][track_name] = {
            "translation_axial_consistency": float(track["translation"].get("axial_dominance_consistency", 0.0)),
            "translation_sign_consistency": float(track["translation"].get("polarity_separation_consistency", 0.0)),
            "rotation_swirl_consistency": float(track["rotation"].get("swirl_dominance_consistency", 0.0)),
            "rotation_sign_consistency": float(track["rotation"].get("circulation_separation_consistency", 0.0)),
            "translation_axial_margin_cv": float(track["translation"].get("axial_margin_cv", 0.0)),
            "rotation_signed_circulation_cv": float(track["rotation"].get("signed_circulation_cv", 0.0)),
            "translation_robust_substructures": len(track["translation"].get("robust_substructures", [])),
            "rotation_robust_substructures": len(track["rotation"].get("robust_substructures", [])),
        }
    report_path = outdir / "channel_invariant_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(TRACK_NAMES), dtype=np.float64)
    t_cons = [invariants["tracks"][name]["translation"].get("axial_dominance_consistency", 0.0) for name in TRACK_NAMES]
    r_cons = [invariants["tracks"][name]["rotation"].get("swirl_dominance_consistency", 0.0) for name in TRACK_NAMES]
    ax.plot(x, t_cons, marker="o", label="translation axial consistency")
    ax.plot(x, r_cons, marker="o", label="rotation swirl consistency")
    ax.set_xticks(x, TRACK_NAMES, rotation=15)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("consistency")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / "channel_invariant_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
