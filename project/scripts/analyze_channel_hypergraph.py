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

from cell_sphere_core.analysis.channel_hypergraph import summarize_channel_hypergraph_trace
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze a channel_hypergraph_trace.json file.")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--title", type=str, default="Step 25 channel hypergraph analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_channel_hypergraph_trace(trace)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    report = {"title": args.title, "summary": summary, "external_interpretation": {}}
    for track_name in TRACK_NAMES:
        active = summary["tracks"][track_name]
        fam = active["active_family_means"]
        report["external_interpretation"][track_name] = {
            "axial_minus_swirl_active": float(fam["axial_polar_family"] - fam["swirl_circulation_family"]),
            "x_axis_balance": float(active["active_axis_balance"]["x"]),
            "signed_circulation": float(active["active_signed_circulation"]),
            "mean_edge_count": float(active["mean_edge_count"]),
            "mean_hyperedge_count": float(active["mean_hyperedge_count"]),
            "active_transfer_strength_mean": float(active["active_transfer_strength_mean"]),
        }
    report_path = outdir / "channel_hypergraph_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(TRACK_NAMES), dtype=np.float64)
    axial = [summary["tracks"][name]["active_family_means"]["axial_polar_family"] for name in TRACK_NAMES]
    swirl = [summary["tracks"][name]["active_family_means"]["swirl_circulation_family"] for name in TRACK_NAMES]
    ax.plot(x, axial, marker="o", label="axial_polar_family")
    ax.plot(x, swirl, marker="o", label="swirl_circulation_family")
    ax.set_xticks(x, TRACK_NAMES, rotation=15)
    ax.set_ylabel("active family mean")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / "channel_hypergraph_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)
    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
