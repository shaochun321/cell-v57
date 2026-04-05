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

from cell_sphere_core.analysis.channel_motifs import summarize_channel_motif_trace
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze a channel_motif_trace.json file.")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--title", type=str, default="Step 26 channel motif analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_channel_motif_trace(trace)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    report = {"title": args.title, "summary": summary, "external_interpretation": {}}
    for track_name in TRACK_NAMES:
        active = summary["tracks"][track_name]
        motifs = active.get("active_motif_counts", {})
        report["external_interpretation"][track_name] = {
            "axial_minus_swirl_active": float(active["active_family_means"].get("axial_polar_family", 0.0) - active["active_family_means"].get("swirl_circulation_family", 0.0)),
            "x_axis_balance": float(active["active_axis_balance"].get("x", 0.0)),
            "signed_circulation": float(active.get("active_signed_circulation", 0.0)),
            "axial_path_motif_count": int(motifs.get("axial_path_motif", 0)),
            "swirl_loop_motif_count": int(motifs.get("swirl_loop_motif", 0)),
            "stable_substructure_count": int(len(active.get("stable_substructures", []))),
        }
    report_path = outdir / "channel_motif_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(TRACK_NAMES), dtype=np.float64)
    axial_counts = [summary["tracks"][name]["active_motif_counts"].get("axial_path_motif", 0) for name in TRACK_NAMES]
    swirl_counts = [summary["tracks"][name]["active_motif_counts"].get("swirl_loop_motif", 0) for name in TRACK_NAMES]
    ax.plot(x, axial_counts, marker="o", label="axial_path_motif count")
    ax.plot(x, swirl_counts, marker="o", label="swirl_loop_motif count")
    ax.set_xticks(x, TRACK_NAMES, rotation=15)
    ax.set_ylabel("active motif count")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / "channel_motif_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
