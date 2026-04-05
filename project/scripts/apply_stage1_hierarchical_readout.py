from __future__ import annotations

import argparse
import json
import os
import sys
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_stage1_scale_sign_audit import load_panel
from scripts.analyze_stage1_sign_anchor_feature_audit import zscore_panel

TRANSLATION_GROUP_KEYS = [
    "discrete_channel_track_swirl_circulation_family_shell_0",
    "discrete_channel_track_swirl_circulation_family_inner_level",
    "layered_coupling_track_bandwidth_shell_2",
    "discrete_channel_track_bandwidth_shell_2",
]
NONTRANSLATION_KEYS = [
    "discrete_channel_track_transfer_std",
    "agg_magnitude",
]
SIGN_KEYS = ["layered_coupling_track_circvec_z"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply the stage-1 hierarchical external readout.")
    p.add_argument("--train-dir", type=str, default="outputs/stage1_interface_protocol_raw/N64")
    p.add_argument("--target-dir", type=str, default="outputs/stage1_medium_sign_audit_raw/baseline")
    p.add_argument("--out", type=str, default="outputs/stage1_hierarchical_readout_predictions.json")
    return p.parse_args()


def centroid(samples: list[dict[str, Any]], pred, keys: list[str]) -> dict[str, float]:
    subset = [s for s in samples if pred(s)]
    return {k: mean([s["z_features"][k] for s in subset]) for k in keys}


def squared_distance(sample: dict[str, Any], center: dict[str, float], keys: list[str]) -> float:
    return sum((sample["z_features"][k] - center[k]) ** 2 for k in keys)


def sign_spec(samples: list[dict[str, Any]], keys: list[str]) -> dict[str, dict[str, float]]:
    pos = centroid(samples, lambda s: s["label"] == "translation_x_pos", keys)
    neg = centroid(samples, lambda s: s["label"] == "translation_x_neg", keys)
    return {
        "mid": {k: 0.5 * (pos[k] + neg[k]) for k in keys},
        "weights": {k: pos[k] - neg[k] for k in keys},
    }


def sign_predict(sample: dict[str, Any], spec: dict[str, dict[str, float]], keys: list[str]) -> tuple[str, float]:
    score = sum(spec["weights"][k] * (sample["z_features"][k] - spec["mid"][k]) for k in keys)
    return ("translation_x_pos" if score > 0.0 else "translation_x_neg"), score


def main() -> None:
    args = parse_args()
    train = load_panel(Path(args.train_dir))
    target = load_panel(Path(args.target_dir))
    feature_names = list(train[0]["features"].keys())

    means = {name: mean([s["features"][name] for s in train]) for name in feature_names}
    stds = {}
    for name in feature_names:
        variance = mean([(s["features"][name] - means[name]) ** 2 for s in train])
        stds[name] = sqrt(variance) if variance > 0.0 else 1.0
    zscore_panel(train, feature_names, means, stds)
    zscore_panel(target, feature_names, means, stds)

    translation_center = centroid(train, lambda s: s["label"].startswith("translation"), TRANSLATION_GROUP_KEYS)
    nontranslation_center = centroid(train, lambda s: not s["label"].startswith("translation"), TRANSLATION_GROUP_KEYS)
    baseline_center = centroid(train, lambda s: s["label"] == "baseline", NONTRANSLATION_KEYS)
    rotation_center = centroid(train, lambda s: s["label"] == "rotation_z_pos", NONTRANSLATION_KEYS)
    spec = sign_spec([s for s in train if s["label"].startswith("translation")], SIGN_KEYS)

    preds = []
    for sample in target:
        d_translation = squared_distance(sample, translation_center, TRANSLATION_GROUP_KEYS)
        d_nontranslation = squared_distance(sample, nontranslation_center, TRANSLATION_GROUP_KEYS)
        if d_translation < d_nontranslation:
            pred, score = sign_predict(sample, spec, SIGN_KEYS)
            preds.append({
                "seed": sample["seed"],
                "label": sample["label"],
                "predicted": pred,
                "stage1_predicted": "translation",
                "sign_score": score,
            })
        else:
            d_baseline = squared_distance(sample, baseline_center, NONTRANSLATION_KEYS)
            d_rotation = squared_distance(sample, rotation_center, NONTRANSLATION_KEYS)
            pred = "baseline" if d_baseline < d_rotation else "rotation_z_pos"
            preds.append({
                "seed": sample["seed"],
                "label": sample["label"],
                "predicted": pred,
                "stage1_predicted": "nontranslation",
                "stage2_baseline_distance": d_baseline,
                "stage2_rotation_distance": d_rotation,
            })

    accuracy = sum(int(p["predicted"] == p["label"]) for p in preds) / len(preds)
    out = {
        "protocol": "stage1_hierarchical_readout_apply",
        "translation_group_keys": TRANSLATION_GROUP_KEYS,
        "nontranslation_keys": NONTRANSLATION_KEYS,
        "sign_keys": SIGN_KEYS,
        "accuracy": accuracy,
        "predictions": preds,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[OK] wrote hierarchical readout predictions to {out_path} (accuracy={accuracy:.3f})")


if __name__ == "__main__":
    main()
