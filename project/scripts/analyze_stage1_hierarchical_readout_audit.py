from __future__ import annotations

import argparse
import json
import os
import sys
from math import sqrt
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from statistics import mean
from typing import Any, Callable

from scripts.analyze_stage1_scale_sign_audit import load_panel
from scripts.analyze_stage1_sign_anchor_feature_audit import zscore_panel, feature_ranking


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Search a simple hierarchical external readout for stable 64->96 sign anchoring.")
    p.add_argument("--n64-dir", type=str, default="outputs/stage1_interface_protocol_raw/N64")
    p.add_argument("--n96-dir", type=str, default="outputs/stage1_medium_sign_audit_raw/baseline")
    p.add_argument("--outdir", type=str, default="outputs/stage1_hierarchical_readout_audit")
    p.add_argument("--translation-group-k", type=int, nargs="+", default=[2, 4, 6, 8, 12])
    p.add_argument("--nontranslation-k", type=int, nargs="+", default=[2, 4, 6, 8, 12])
    p.add_argument("--sign-k", type=int, nargs="+", default=[1, 2, 3, 4, 6, 8, 12])
    return p.parse_args()


def mean_feature(samples: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool], name: str) -> float:
    subset = [s for s in samples if pred(s)]
    return mean([s["z_features"][name] for s in subset])


def build_rankings(panel64: list[dict[str, Any]], panel96: list[dict[str, Any]], feature_names: list[str]) -> dict[str, list[dict[str, float | str | bool]]]:
    sign_rank = feature_ranking(panel64, panel96, feature_names)

    def binary_rank(pos_pred: Callable[[dict[str, Any]], bool], neg_pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, float | str | bool]]:
        rows = []
        for name in feature_names:
            d64 = mean_feature(panel64, pos_pred, name) - mean_feature(panel64, neg_pred, name)
            d96 = mean_feature(panel96, pos_pred, name) - mean_feature(panel96, neg_pred, name)
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
                "score": score,
            })
        rows.sort(key=lambda x: x["score"], reverse=True)
        return rows

    translation_group_rank = binary_rank(
        lambda s: s["label"].startswith("translation"),
        lambda s: not s["label"].startswith("translation"),
    )
    nontranslation_rank = binary_rank(
        lambda s: s["label"] == "baseline",
        lambda s: s["label"] == "rotation_z_pos",
    )
    return {
        "sign_rank": sign_rank,
        "translation_group_rank": translation_group_rank,
        "nontranslation_rank": nontranslation_rank,
    }


def centroid(samples: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool], keys: list[str]) -> dict[str, float]:
    subset = [s for s in samples if pred(s)]
    return {k: mean([s["z_features"][k] for s in subset]) for k in keys}


def squared_distance(sample: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((sample["z_features"][k] - center[k]) ** 2 for k in keys)


def sign_axis_spec(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    pos_center = centroid(samples, lambda s: s["label"] == "translation_x_pos", keys)
    neg_center = centroid(samples, lambda s: s["label"] == "translation_x_neg", keys)
    mid = {k: 0.5 * (pos_center[k] + neg_center[k]) for k in keys}
    weights = {k: pos_center[k] - neg_center[k] for k in keys}
    return {
        "pos_center": pos_center,
        "neg_center": neg_center,
        "mid": mid,
        "weights": weights,
    }


def sign_predict(sample: dict[str, Any], spec: dict[str, dict[str, float]], keys: list[str]) -> tuple[str, float]:
    score = sum(spec["weights"][k] * (sample["z_features"][k] - spec["mid"][k]) for k in keys)
    return ("translation_x_pos" if score > 0.0 else "translation_x_neg"), score


def fit_hierarchical_decoder(train_samples: list[dict[str, Any]], translation_group_keys: list[str], nontranslation_keys: list[str], sign_keys: list[str]) -> dict[str, Any]:
    return {
        "translation_group_keys": translation_group_keys,
        "nontranslation_keys": nontranslation_keys,
        "sign_keys": sign_keys,
        "translation_center": centroid(train_samples, lambda s: s["label"].startswith("translation"), translation_group_keys),
        "nontranslation_center": centroid(train_samples, lambda s: not s["label"].startswith("translation"), translation_group_keys),
        "baseline_center": centroid(train_samples, lambda s: s["label"] == "baseline", nontranslation_keys),
        "rotation_center": centroid(train_samples, lambda s: s["label"] == "rotation_z_pos", nontranslation_keys),
        "sign_spec": sign_axis_spec([s for s in train_samples if s["label"].startswith("translation")], sign_keys),
    }


def predict_hierarchical(samples: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
    preds = []
    for sample in samples:
        d_translation = squared_distance(sample, model["translation_center"], model["translation_group_keys"])
        d_nontranslation = squared_distance(sample, model["nontranslation_center"], model["translation_group_keys"])
        stage1 = "translation" if d_translation < d_nontranslation else "nontranslation"
        record: dict[str, Any] = {
            "seed": sample["seed"],
            "label": sample["label"],
            "stage1_predicted": stage1,
            "stage1_translation_distance": d_translation,
            "stage1_nontranslation_distance": d_nontranslation,
        }
        if stage1 == "translation":
            pred, score = sign_predict(sample, model["sign_spec"], model["sign_keys"])
            record["predicted"] = pred
            record["sign_score"] = score
        else:
            d_baseline = squared_distance(sample, model["baseline_center"], model["nontranslation_keys"])
            d_rotation = squared_distance(sample, model["rotation_center"], model["nontranslation_keys"])
            record["predicted"] = "baseline" if d_baseline < d_rotation else "rotation_z_pos"
            record["stage2_baseline_distance"] = d_baseline
            record["stage2_rotation_distance"] = d_rotation
        preds.append(record)
    return preds


def accuracy(preds: list[dict[str, Any]]) -> float:
    return sum(int(p["predicted"] == p["label"]) for p in preds) / len(preds) if preds else 0.0


def leave_one_seed_out(samples: list[dict[str, Any]], translation_group_keys: list[str], nontranslation_keys: list[str], sign_keys: list[str]) -> float:
    seeds = sorted({s["seed"] for s in samples})
    preds: list[dict[str, Any]] = []
    for seed in seeds:
        train = [s for s in samples if s["seed"] != seed]
        test = [s for s in samples if s["seed"] == seed]
        model = fit_hierarchical_decoder(train, translation_group_keys, nontranslation_keys, sign_keys)
        preds.extend(predict_hierarchical(test, model))
    return accuracy(preds)


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
        variance = mean([(s["features"][name] - means[name]) ** 2 for s in panel64])
        stds[name] = sqrt(variance) if variance > 0.0 else 1.0

    zscore_panel(panel64, feature_names, means, stds)
    zscore_panel(panel96, feature_names, means, stds)
    ranks = build_rankings(panel64, panel96, feature_names)

    trials = []
    for kg in args.translation_group_k:
        translation_group_keys = [row["feature"] for row in ranks["translation_group_rank"][:kg]]
        for kn in args.nontranslation_k:
            nontranslation_keys = [row["feature"] for row in ranks["nontranslation_rank"][:kn]]
            for ks in args.sign_k:
                sign_keys = [row["feature"] for row in ranks["sign_rank"][:ks]]
                model = fit_hierarchical_decoder(panel64, translation_group_keys, nontranslation_keys, sign_keys)
                cross_preds = predict_hierarchical(panel96, model)
                trial = {
                    "translation_group_k": kg,
                    "nontranslation_k": kn,
                    "sign_k": ks,
                    "translation_group_keys": translation_group_keys,
                    "nontranslation_keys": nontranslation_keys,
                    "sign_keys": sign_keys,
                    "within64_accuracy": leave_one_seed_out(panel64, translation_group_keys, nontranslation_keys, sign_keys),
                    "within96_accuracy": leave_one_seed_out(panel96, translation_group_keys, nontranslation_keys, sign_keys),
                    "cross_scale_accuracy": accuracy(cross_preds),
                    "translation_cross_scale_accuracy": accuracy([p for p in cross_preds if p["label"].startswith("translation")]),
                    "cross_scale_predictions": cross_preds,
                }
                trial["composite_score"] = (
                    0.20 * trial["within64_accuracy"]
                    + 0.20 * trial["within96_accuracy"]
                    + 0.25 * trial["cross_scale_accuracy"]
                    + 0.35 * trial["translation_cross_scale_accuracy"]
                )
                trials.append(trial)
    trials.sort(key=lambda x: (x["composite_score"], x["cross_scale_accuracy"]), reverse=True)
    best = trials[0]

    result = {
        "protocol": "stage1_hierarchical_readout_audit",
        "ranking_heads": {
            "translation_group": ranks["translation_group_rank"][:20],
            "nontranslation": ranks["nontranslation_rank"][:20],
            "sign": ranks["sign_rank"][:20],
        },
        "trials": trials,
        "best_trial": best,
    }
    (outdir / "stage1_hierarchical_readout_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    lines = [
        "# Stage-1 hierarchical readout audit",
        "",
        "Goal: replace the flat centroid readout with a minimal hierarchical external decoder that first separates translation from nontranslation, then resolves sign only inside the translation branch.",
        "",
        "## Best trial",
        "",
        f"- translation-group k: {best['translation_group_k']}",
        f"- nontranslation k: {best['nontranslation_k']}",
        f"- sign k: {best['sign_k']}",
        f"- within N64 accuracy: {best['within64_accuracy']:.3f}",
        f"- within N96 accuracy: {best['within96_accuracy']:.3f}",
        f"- cross-scale accuracy: {best['cross_scale_accuracy']:.3f}",
        f"- translation cross-scale accuracy: {best['translation_cross_scale_accuracy']:.3f}",
        "",
        "### Translation-group keys",
    ]
    for name in best["translation_group_keys"]:
        lines.append(f"- {name}")
    lines.extend(["", "### Nontranslation keys", ""])
    for name in best["nontranslation_keys"]:
        lines.append(f"- {name}")
    lines.extend(["", "### Sign keys", ""])
    for name in best["sign_keys"]:
        lines.append(f"- {name}")
    lines.extend(["", "## Cross-scale predictions", ""])
    for row in best["cross_scale_predictions"]:
        extra = f", sign_score={row['sign_score']:.3f}" if "sign_score" in row else ""
        lines.append(f"- seed {row['seed']} {row['label']} -> {row['predicted']} (stage1={row['stage1_predicted']}{extra})")
    (outdir / "STAGE1_HIERARCHICAL_READOUT_AUDIT_REPORT.md").write_text("\n".join(lines))
    print(f"[OK] hierarchical readout audit written to {outdir}")


if __name__ == "__main__":
    main()
