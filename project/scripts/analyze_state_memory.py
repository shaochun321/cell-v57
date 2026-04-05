from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import os

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import matplotlib.pyplot as plt

from cell_sphere_core.analysis.process_state import summarize_transition_memory_trace


TRANSITION_TO_ID = {
    "baseline": 0,
    "stimulus_onset": 1,
    "stimulus_active": 2,
    "recovery": 3,
    "recovered_static": 4,
    "post_stimulus_drift": 5,
    "unknown": 6,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze Step 16 transition-memory traces.")
    p.add_argument("--input", type=str, required=True, help="motion_state_trace.json")
    p.add_argument("--title", type=str, default="Step 16 Transition Memory")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_transition_memory_trace(trace)

    times = [float(row.get("time", 0.0)) for row in trace]
    memory_strength = [float(row.get("memory_trace_strength", 0.0)) for row in trace]
    recovery_index = [float(row.get("recovery_index", 0.0)) for row in trace]
    motion_index = [float(row.get("motion_index", 0.0)) for row in trace]
    static_index = [float(row.get("static_index", 0.0)) for row in trace]
    transition_names = [str(row.get("transition_state", "unknown")) for row in trace]
    transition_ids = [TRANSITION_TO_ID.get(name, TRANSITION_TO_ID["unknown"]) for name in transition_names]

    plt.figure(figsize=(10, 8))
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(times, motion_index, label="motion", linewidth=2.0)
    ax1.plot(times, static_index, label="static", linewidth=2.0)
    ax1.set_ylabel("Index")
    ax1.set_title(args.title)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(times, memory_strength, label="memory trace", linewidth=2.0)
    ax2.plot(times, recovery_index, label="recovery", linewidth=2.0)
    ax2.set_ylabel("Memory")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    ax3 = plt.subplot(3, 1, 3)
    ax3.step(times, transition_ids, where="post", linewidth=2.0)
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Transition")
    ax3.set_yticks(list(TRANSITION_TO_ID.values()), list(TRANSITION_TO_ID.keys()))
    ax3.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    out_img = input_path.parent / f"{input_path.stem}_transition_memory.png"
    out_json = input_path.parent / f"{input_path.stem}_transition_summary.json"
    plt.savefig(out_img, dpi=180)
    plt.close()
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"图像已保存: {out_img}")
    print(f"摘要已保存: {out_json}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
