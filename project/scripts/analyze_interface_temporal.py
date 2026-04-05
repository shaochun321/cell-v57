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

from cell_sphere_core.analysis.interface_temporal import summarize_interface_temporal_trace
from cell_sphere_core.analysis.interface_lineages import TRACK_NAMES


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Externally analyze an interface_temporal_trace.json file.")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--title", type=str, default="Step 24 interface-temporal analysis")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_interface_temporal_trace(trace)
    outdir = input_path.parent if args.output is None else Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    report = {
        "title": args.title,
        "summary": summary,
        "external_interpretation": {},
    }
    for track_name in TRACK_NAMES:
        active = summary["tracks"][track_name]["active_families"]
        report["external_interpretation"][track_name] = {
            "axial_minus_swirl_active": float(active["axial_polar_family"]["mean_outer_level"] - active["swirl_circulation_family"]["mean_outer_level"]),
            "axial_attenuation": float(active["axial_polar_family"]["mean_attenuation_index"]),
            "swirl_attenuation": float(active["swirl_circulation_family"]["mean_attenuation_index"]),
            "x_axis_polarity_balance": float(summary["tracks"][track_name]["active_mean_axis_polarity_balance"]["x"]),
            "signed_circulation": float(summary["tracks"][track_name]["active_mean_signed_circulation"]),
        }
    report_path = outdir / "interface_temporal_analysis.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    x = None
    for track_name in TRACK_NAMES:
        shell_profile = summary["tracks"][track_name]["active_families"]["axial_polar_family"]["shell_profile_mean"]
        if x is None:
            x = np.arange(len(shell_profile), dtype=np.float64)
        ax.plot(x, shell_profile, marker="o", label=f"{track_name}: axial")
    ax.set_xlabel("shell index")
    ax.set_ylabel("active shell response")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig_path = outdir / "interface_temporal_overview.png"
    fig.savefig(fig_path, dpi=180)
    plt.close(fig)

    print(f"分析报告: {report_path}")
    print(f"概览图: {fig_path}")


if __name__ == "__main__":
    main()
