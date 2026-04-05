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

from cell_sphere_core.analysis.process_state import summarize_process_state_trace


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze Step 15 process-state traces.")
    p.add_argument("--input", type=str, required=True, help="motion_state_trace.json")
    p.add_argument("--title", type=str, default="Step 15 Process State")
    return p.parse_args()


def _class_to_id(name: str) -> int:
    mapping = {"static": 0, "translation": 1, "rotation": 2, "mixed": 3, "unknown": 4, "none": 5}
    return mapping.get(name, 4)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_process_state_trace(trace)

    times = [float(row.get("time", 0.0)) for row in trace]
    force_mag = [float(row.get("force_magnitude_index", 0.0)) for row in trace]
    static_idx = [float(row.get("static_index", 0.0)) for row in trace]
    motion_idx = [float(row.get("motion_index", 0.0)) for row in trace]
    classes = [str(row.get("motion_class", "unknown")) for row in trace]
    class_ids = [_class_to_id(name) for name in classes]

    plt.figure(figsize=(10, 7))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(times, force_mag, label="force magnitude", linewidth=2.0)
    ax1.plot(times, static_idx, label="static", linewidth=2.0)
    ax1.plot(times, motion_idx, label="motion", linewidth=2.0)
    ax1.set_ylabel("Index")
    ax1.set_title(args.title)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    ax2 = plt.subplot(2, 1, 2)
    ax2.step(times, class_ids, where="post", linewidth=2.0)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Class")
    ax2.set_yticks([0, 1, 2, 3, 4, 5], ["static", "translation", "rotation", "mixed", "unknown", "none"])
    ax2.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    out_img = input_path.parent / f"{input_path.stem}_channels.png"
    out_json = input_path.parent / f"{input_path.stem}_summary.json"
    plt.savefig(out_img, dpi=180)
    plt.close()
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"图像已保存: {out_img}")
    print(f"摘要已保存: {out_json}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
