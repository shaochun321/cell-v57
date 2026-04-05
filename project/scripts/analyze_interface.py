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

from cell_sphere_core.analysis.interface_bundles import summarize_mirror_interface_trace


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze Step 18 mirror-interface traces.")
    p.add_argument("--input", type=str, required=True, help="interface_trace.json")
    p.add_argument("--title", type=str, default="Step 18 Mirror Interface")
    return p.parse_args()


def _class_to_id(name: str) -> int:
    mapping = {"static": 0, "translation": 1, "rotation": 2, "mixed": 3, "unknown": 4, "none": 5}
    return mapping.get(name, 4)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_mirror_interface_trace(trace)

    times = [float(row.get("time", 0.0)) for row in trace]
    static = [float(row.get("aggregate_channels", {}).get("static", 0.0)) for row in trace]
    translation = [float(row.get("aggregate_channels", {}).get("translation", 0.0)) for row in trace]
    rotation = [float(row.get("aggregate_channels", {}).get("rotation", 0.0)) for row in trace]
    event = [float(row.get("aggregate_channels", {}).get("event", 0.0)) for row in trace]
    magnitude = [float(row.get("aggregate_channels", {}).get("magnitude", 0.0)) for row in trace]
    dx = [float(row.get("direction_vector", [0.0, 0.0, 0.0])[0]) for row in trace]
    dy = [float(row.get("direction_vector", [0.0, 0.0, 0.0])[1]) for row in trace]
    dz = [float(row.get("direction_vector", [0.0, 0.0, 0.0])[2]) for row in trace]
    class_ids = [_class_to_id(str(row.get("interface_class", "unknown"))) for row in trace]

    plt.figure(figsize=(10, 10))
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(times, static, label="static", linewidth=2.0)
    ax1.plot(times, translation, label="translation", linewidth=2.0)
    ax1.plot(times, rotation, label="rotation", linewidth=2.0)
    ax1.plot(times, event, label="event", linewidth=1.7)
    ax1.plot(times, magnitude, label="magnitude", linewidth=1.7)
    ax1.set_ylabel("Aggregate channels")
    ax1.set_title(args.title)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(times, dx, label="dir_x", linewidth=1.8)
    ax2.plot(times, dy, label="dir_y", linewidth=1.8)
    ax2.plot(times, dz, label="dir_z", linewidth=1.8)
    ax2.set_ylabel("Direction vector")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    ax3 = plt.subplot(3, 1, 3)
    ax3.step(times, class_ids, where="post", linewidth=2.0)
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Interface class")
    ax3.set_yticks([0, 1, 2, 3, 4, 5], ["static", "translation", "rotation", "mixed", "unknown", "none"])
    ax3.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    out_img = input_path.parent / f"{input_path.stem}_overview.png"
    out_json = input_path.parent / f"{input_path.stem}_summary.json"
    plt.savefig(out_img, dpi=180)
    plt.close()
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"图像已保存: {out_img}")
    print(f"摘要已保存: {out_json}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
