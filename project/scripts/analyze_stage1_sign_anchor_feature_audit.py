from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from math import sqrt

from scripts.analyze_stage1_scale_sign_audit import load_panel

TRANSLATION_LABELS = ["translation_x_pos", "translation_x_neg"]
ALL_LABELS = ["baseline", "translation_x_pos", "translation_x_neg", "rotation_z_pos"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find cross-scale sign-stable feature subsets for the external readout.")
    p.add_argument("--n64-dir", type=str, default="outputs/stage1_interface_protocol/N64")
    p.add_argument("--n96-dir", type=str, default="outputs/stage1_medium_sign_audit/baseline")
    p.add_argument("--outdir", type=str, default="outputs/stage1_sign_anchor_feature_audit")
    p.add_argument("--k-grid", type=int, nargs="+", default=[8, 12, 16, 24, 32, 48])
    return p.parse_args()


def zscore_panel(samples: list[dict], feature_names: list[str], means: dict[str, float], stds: dict[str, float]) -> None:
    for sample in samples:
        sample["z_features"] = {name: (sample["features"][name] - means[name]) / stds[name] for name in feature_names}


def feature_stats(samples: list[dict], label: str, feature_names: list[str]) -> dict[str, float]:
    subset = [s for s in samples if s["label"] == label]
    return {name: mean([s["z_features"][name] for s in subset]) for name in feature_names}


def feature_ranking(panel64: list[dict], panel96: list[dict], feature_names: list[str]) -> list[dict]:
    pos64 = feature_stats(panel64, "translation_x_pos", feature_names)
    neg64 = feature_stats(panel64, "translation_x_neg", feature_names)
    pos96 = feature_stats(panel96, "translation_x_pos", feature_names)
    neg96 = feature_stats(panel96, "translation_x_neg", feature_names)
    rows = []
    for name in feature_names:
        d64 = pos64[name] - neg64[name]
        d96 = pos96[name] - neg96[name]
        same_sign = d64 == 0.0 or d96 == 0.0 or (d64 > 0) == (d96 > 0)
        magnitude = min(abs(d64), abs(d96))
        drift_penalty = abs(d64 - d96)
        score = magnitude - 0.35 * drift_penalty
        if not same_sign:
            score -= 10.0
        rows.append({
            "feature": name,
            "delta64": d64,
            "delta96": d96,
            "same_sign": same_sign,
            "magnitude_floor": magnitude,
            "drift_penalty": drift_penalty,
            "score": score,
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows


def euclidean(a: dict[str, float], b: dict[str, float], keys: list[str]) -> float:
    return sqrt(sum((a[k] - b[k]) ** 2 for k in keys))


def leave_one_seed_out(samples: list[dict], keys: list[str]) -> float:
    seeds = sorted({s["seed"] for s in samples})
    total = 0
    correct = 0
    for test_seed in seeds:
        train = [s for s in samples if s["seed"] != test_seed]
        test = [s for s in samples if s["seed"] == test_seed]
        labels = sorted({s["label"] for s in train})
        centroids = {
            label: {k: mean([s["z_features"][k] for s in train if s["label"] == label]) for k in keys}
            for label in labels
        }
        for sample in test:
            pred = min(labels, key=lambda label: euclidean(sample["z_features"], centroids[label], keys))
            total += 1
            correct += int(pred == sample["label"])
    return correct / total if total else 0.0


def project_against_n64(panel64: list[dict], panel96: list[dict], keys: list[str]) -> dict:
    labels = sorted({s["label"] for s in panel64})
    centroids64 = {
        label: {k: mean([s["z_features"][k] for s in panel64 if s["label"] == label]) for k in keys}
        for label in labels
    }
    preds = []
    for sample in panel96:
        dists = {label: euclidean(sample["z_features"], centroids64[label], keys) for label in labels}
        ordered = sorted(dists.items(), key=lambda kv: kv[1])
        preds.append({
            "seed": sample["seed"],
            "label": sample["label"],
            "predicted": ordered[0][0],
            "margin": ordered[1][1] - ordered[0][1],
            "distances": dists,
        })
    overall = sum(int(p["predicted"] == p["label"]) for p in preds) / len(preds)
    translation = [p for p in preds if p["label"] in TRANSLATION_LABELS]
    translation_acc = sum(int(p["predicted"] == p["label"]) for p in translation) / len(translation)
    translation_margin = mean([p["margin"] for p in translation])
    return {
        "predictions": preds,
        "overall_accuracy": overall,
        "translation_accuracy": translation_acc,
        "translation_margin": translation_margin,
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    panel64 = load_panel(Path(args.n64_dir))
    panel96 = load_panel(Path(args.n96_dir))
    feature_names = list(panel64[0]["features"].keys())

    means = {name: mean([s["features"][name] for s in panel64]) for name in feature_names}
    stds = {}
    for name in feature_names:
        var = mean([(s["features"][name] - means[name]) ** 2 for s in panel64])
        stds[name] = sqrt(var) if var > 0.0 else 1.0
    zscore_panel(panel64, feature_names, means, stds)
    zscore_panel(panel96, feature_names, means, stds)

    ranking = feature_ranking(panel64, panel96, feature_names)

    trials = []
    for k in args.k_grid:
        keys = [row["feature"] for row in ranking[:k]]
        within64 = leave_one_seed_out(panel64, keys)
        within96 = leave_one_seed_out(panel96, keys)
        proj = project_against_n64(panel64, panel96, keys)
        trials.append({
            "k": k,
            "features": keys,
            "within64_accuracy": within64,
            "within96_accuracy": within96,
            "cross_scale_accuracy": proj["overall_accuracy"],
            "translation_projection_accuracy": proj["translation_accuracy"],
            "translation_margin": proj["translation_margin"],
            "predictions": proj["predictions"],
            "composite_score": 0.20 * within64 + 0.20 * within96 + 0.25 * proj["overall_accuracy"] + 0.35 * proj["translation_accuracy"],
        })
    trials.sort(key=lambda x: (x["composite_score"], x["translation_margin"]), reverse=True)

    result = {
        "protocol": "stage1_sign_anchor_feature_audit",
        "feature_ranking": ranking[:80],
        "trials": trials,
        "best_trial": trials[0],
    }
    (outdir / "stage1_sign_anchor_feature_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        "# Stage-1 sign-anchor feature audit",
        "",
        "Goal: rebuild the external readout on a feature subset that preserves translation sign across 64/96 cells.",
        "",
        "## Best subset",
        "",
        f"- k: {trials[0]['k']}",
        f"- within N64 accuracy: {trials[0]['within64_accuracy']:.3f}",
        f"- within N96 accuracy: {trials[0]['within96_accuracy']:.3f}",
        f"- cross-scale accuracy: {trials[0]['cross_scale_accuracy']:.3f}",
        f"- translation projection accuracy: {trials[0]['translation_projection_accuracy']:.3f}",
        f"- translation mean margin: {trials[0]['translation_margin']:.3f}",
        "",
        "Selected features:",
    ]
    for name in trials[0]["features"]:
        lines.append(f"- {name}")
    lines.extend(["", "## Top sign-stable features", ""])
    for row in ranking[:20]:
        lines.append(
            f"- {row['feature']}: delta64={row['delta64']:.3f}, delta96={row['delta96']:.3f}, same_sign={row['same_sign']}, score={row['score']:.3f}"
        )
    (outdir / "STAGE1_SIGN_ANCHOR_FEATURE_AUDIT_REPORT.md").write_text("\n".join(lines))
    print(f"[OK] sign-anchor feature audit written to {outdir}")


if __name__ == "__main__":
    main()
