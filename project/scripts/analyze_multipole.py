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

from cell_sphere_core.analysis.multipole import analyze_sensor_frames, load_sensor_nodes_jsonl, summarize_energy_series


def _load_frames(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        return load_sensor_nodes_jsonl(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    raise ValueError(f"Unsupported input payload in {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze node-level multipole energy over time.")
    p.add_argument("--input", type=str, required=True, help="sensor_nodes.jsonl or sensor_trace.json")
    p.add_argument("--field", type=str, default="u_r", help="Node field to analyze, e.g. u_r, accel_r, force_density, gate")
    p.add_argument("--band", type=str, default="outer", help="Band index, or inner / outer")
    p.add_argument("--title", type=str, default="Step 14 Multipole Analysis")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    frames = _load_frames(input_path)
    band: int | str = args.band
    if band not in {"inner", "outer"}:
        band = int(band)
    series = analyze_sensor_frames(frames, band=band, field_name=args.field)
    summary = summarize_energy_series(series)
    active_series = [row for row in series if row.get("stimulus_active")]
    active_summary = summarize_energy_series(active_series)
    times = [row["time"] for row in series]
    e0 = [row["l=0"] for row in series]
    e1 = [row["l=1"] for row in series]
    e2 = [row["l=2"] for row in series]

    plt.figure(figsize=(10, 6))
    plt.plot(times, e0, label="l=0", linestyle=":")
    plt.plot(times, e1, label="l=1 dipole", linewidth=2.2)
    plt.plot(times, e2, label="l=2 quadrupole", linewidth=2.2)
    plt.xlabel("Time (s)")
    plt.ylabel(f"Energy ({args.field})")
    plt.title(args.title)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()

    out_img = input_path.parent / f"{input_path.stem}_{args.field}_band-{args.band}_multipole.png"
    out_json = input_path.parent / f"{input_path.stem}_{args.field}_band-{args.band}_multipole.json"
    plt.savefig(out_img, dpi=180)
    plt.close()
    out_json.write_text(json.dumps({"series": series, "summary": summary, "active_summary": active_summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"图像已保存: {out_img}")
    print(f"摘要已保存: {out_json}")
    print(json.dumps({"summary": summary, "active_summary": active_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
