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

from cell_sphere_core.analysis.interface_network import TRACK_NAMES, summarize_interface_network_trace


PLOT_CHANNELS = ["deformation_drive", "vibration_drive", "event_flux", "dissipation_load", "axial_flux", "swirl_flux", "transfer_potential"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze an interface_network_trace.json file.")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--title", type=str, default="Step 19 interface-network analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_interface_network_trace(trace)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    report = {
        "title": args.title,
        "summary": summary,
        "external_interpretation": {},
    }
    for track_name in TRACK_NAMES:
        track_summary = summary["tracks"][track_name]
        channels = track_summary.get("active_summary", {}).get("mean_global_channels", {})
        report["external_interpretation"][track_name] = {
            "translation_like_margin": float(channels.get("axial_flux", 0.0) - channels.get("swirl_flux", 0.0)),
            "rotation_like_margin": float(channels.get("swirl_flux", 0.0) - channels.get("axial_flux", 0.0)),
            "deformation_vs_vibration_gap": float(channels.get("deformation_drive", 0.0) - channels.get("vibration_drive", 0.0)),
        }
    report_path = outdir / "interface_network_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    x = np.arange(len(PLOT_CHANNELS), dtype=np.float64)
    width = 0.22
    fig, ax = plt.subplots(figsize=(11, 5))
    for idx, track_name in enumerate(TRACK_NAMES):
        channels = summary["tracks"][track_name].get("active_summary", {}).get("mean_global_channels", {})
        values = [float(channels.get(name, 0.0)) for name in PLOT_CHANNELS]
        ax.bar(x + (idx - 1) * width, values, width=width, label=track_name)
    ax.set_xticks(x)
    ax.set_xticklabels(PLOT_CHANNELS, rotation=25, ha="right")
    ax.set_ylabel("channel level")
    ax.set_ylim(0.0, 1.05)
    ax.set_title(args.title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig_path = outdir / "interface_network_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)

    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
