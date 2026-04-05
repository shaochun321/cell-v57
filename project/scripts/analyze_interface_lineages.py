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

from cell_sphere_core.analysis.interface_lineages import FAMILY_NAMES, TRACK_NAMES, summarize_interface_lineage_trace

PLOT_FAMILIES = FAMILY_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze an interface_lineage_trace.json file.")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--title", type=str, default="Step 21 interface-lineage analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_interface_lineage_trace(trace)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    report = {
        "title": args.title,
        "summary": summary,
        "external_interpretation": {},
    }
    for track_name in TRACK_NAMES:
        track_summary = summary["tracks"][track_name]
        families = track_summary.get("active_family_means", {})
        report["external_interpretation"][track_name] = {
            "axial_minus_swirl_family": float(families.get("axial_polar_family", 0.0) - families.get("swirl_circulation_family", 0.0)),
            "dynamic_minus_structural_family": float(families.get("dynamic_phasic_family", 0.0) - families.get("structural_tonic_family", 0.0)),
            "signed_polarity": float(track_summary.get("active_mean_signed_polarity", 0.0)),
            "signed_circulation": float(track_summary.get("active_mean_signed_circulation", 0.0)),
            "x_axis_family_balance": float(track_summary.get("active_family_axis_balance", {}).get("axial_polar_family", {}).get("x", 0.0)),
            "bandwidth_proxy": float(track_summary.get("active_mean_bandwidth_proxy", 0.0)),
        }
    report_path = outdir / "interface_lineage_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    x = np.arange(len(PLOT_FAMILIES), dtype=np.float64)
    width = 0.22
    fig, ax = plt.subplots(figsize=(10.5, 5))
    for idx, track_name in enumerate(TRACK_NAMES):
        families = summary["tracks"][track_name].get("active_family_means", {})
        values = [float(families.get(name, 0.0)) for name in PLOT_FAMILIES]
        ax.bar(x + (idx - 1) * width, values, width=width, label=track_name)
    ax.set_xticks(x)
    ax.set_xticklabels(PLOT_FAMILIES, rotation=20, ha="right")
    ax.set_ylabel("family level")
    ax.set_ylim(0.0, 1.05)
    ax.set_title(args.title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig_path = outdir / "interface_lineage_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)

    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
