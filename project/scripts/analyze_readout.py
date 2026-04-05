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

from cell_sphere_core.analysis.readout import summarize_external_readout_trace


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze Step 17 external readout traces.")
    p.add_argument("--input", type=str, required=True, help="readout_trace.json")
    p.add_argument("--title", type=str, default="Step 17 External Readout")
    return p.parse_args()


def _class_to_id(name: str) -> int:
    mapping = {"static": 0, "translation": 1, "rotation": 2, "mixed": 3, "unknown": 4, "none": 5}
    return mapping.get(name, 4)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    trace = json.loads(input_path.read_text(encoding="utf-8"))
    summary = summarize_external_readout_trace(trace)

    times = [float(row.get("time", 0.0)) for row in trace]
    static = [float(row.get("static_channel", 0.0)) for row in trace]
    translation = [float(row.get("translation_channel", 0.0)) for row in trace]
    rotation = [float(row.get("rotation_channel", 0.0)) for row in trace]
    onset = [float(row.get("onset_channel", 0.0)) for row in trace]
    recovery = [float(row.get("recovery_channel", 0.0)) for row in trace]
    class_ids = [_class_to_id(str(row.get("readout_class", "unknown"))) for row in trace]

    plt.figure(figsize=(10, 8))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(times, static, label="static", linewidth=2.0)
    ax1.plot(times, translation, label="translation", linewidth=2.0)
    ax1.plot(times, rotation, label="rotation", linewidth=2.0)
    ax1.plot(times, onset, label="onset", linewidth=1.7)
    ax1.plot(times, recovery, label="recovery", linewidth=1.7)
    ax1.set_ylabel("Channel")
    ax1.set_title(args.title)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    ax2 = plt.subplot(2, 1, 2)
    ax2.step(times, class_ids, where="post", linewidth=2.0)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Readout class")
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
