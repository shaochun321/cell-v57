from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from scripts.analyze_stage1_scale_sign_audit import (
    load_panel,
    classify_with_centroids,
    build_centroids,
    euclidean_distance,
    top_feature_drifts,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze stage-1 medium/sign audit outputs.")
    p.add_argument("--reference-dir", type=str, default="outputs/stage1_scale_sign_audit/N64")
    p.add_argument("--audit-dir", type=str, default="outputs/stage1_medium_sign_audit")
    p.add_argument("--outdir", type=str, default="outputs/stage1_medium_sign_audit_analysis")
    return p.parse_args()


def score_translation_projection(cross_scale: list[dict]) -> float:
    items = [x for x in cross_scale if x["label"] in {"translation_x_pos", "translation_x_neg"}]
    if not items:
        return 0.0
    return sum(int(x["predicted_against_N64"] == x["label"]) for x in items) / len(items)


def score_all_projection(cross_scale: list[dict]) -> float:
    if not cross_scale:
        return 0.0
    return sum(int(x["predicted_against_N64"] == x["label"]) for x in cross_scale) / len(cross_scale)


def mean_margin(items: list[dict], labels: set[str] | None = None) -> float:
    filt = items if labels is None else [x for x in items if x["label"] in labels]
    if not filt:
        return 0.0
    return mean([x["distance_margin_to_second"] for x in filt])


def main() -> None:
    args = parse_args()
    reference_dir = Path(args.reference_dir)
    audit_dir = Path(args.audit_dir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    panel64 = load_panel(reference_dir)
    cls64 = classify_with_centroids(panel64)
    feature_names = cls64["feature_names"]
    means = cls64["means"]
    stds = cls64["stds"]

    for sample in panel64:
        sample["z_features"] = {name: (sample["features"][name] - means[name]) / stds[name] for name in feature_names}
    centroids64 = build_centroids(panel64, feature_names)

    manifest = json.loads((audit_dir / "stage1_medium_sign_manifest.json").read_text())
    profiles = manifest["profiles"]

    analysis: dict[str, object] = {
        "protocol": "stage1_medium_sign_audit",
        "reference_n64_accuracy": cls64["accuracy"],
        "profiles": {},
        "ranking": [],
    }

    ranking_rows = []
    for profile_name in profiles.keys():
        panel = load_panel(audit_dir / profile_name)
        cls = classify_with_centroids(panel)
        for sample in panel:
            sample["z_features"] = {name: (sample["features"][name] - means[name]) / stds[name] for name in feature_names}

        cross_scale = []
        for sample in panel:
            distances = {label: euclidean_distance(sample["z_features"], centroid, feature_names) for label, centroid in centroids64.items()}
            ordered = sorted(distances.items(), key=lambda kv: kv[1])
            cross_scale.append({
                "seed": sample["seed"],
                "label": sample["label"],
                "predicted_against_N64": ordered[0][0],
                "distance_margin_to_second": ordered[1][1] - ordered[0][1],
                "distances": distances,
            })

        label_means = {}
        for label in sorted({sample["label"] for sample in panel}):
            label_samples = [s for s in panel if s["label"] == label]
            centroid = {name: mean([s["z_features"][name] for s in label_samples]) for name in feature_names}
            label_means[label] = {
                "distance_to_same_label_64": euclidean_distance(centroid, centroids64[label], feature_names),
                "distance_to_translation_x_pos_64": euclidean_distance(centroid, centroids64["translation_x_pos"], feature_names),
                "distance_to_translation_x_neg_64": euclidean_distance(centroid, centroids64["translation_x_neg"], feature_names),
                "top_feature_drifts_vs_same_label_64": top_feature_drifts(centroids64[label], centroid, feature_names, k=10),
            }

        translation_projection_accuracy = score_translation_projection(cross_scale)
        overall_projection_accuracy = score_all_projection(cross_scale)
        translation_margin = mean_margin(cross_scale, {"translation_x_pos", "translation_x_neg"})
        overall_margin = mean_margin(cross_scale)
        translation_sign_gap = (
            label_means["translation_x_pos"]["distance_to_translation_x_neg_64"] - label_means["translation_x_pos"]["distance_to_translation_x_pos_64"]
            + label_means["translation_x_neg"]["distance_to_translation_x_pos_64"] - label_means["translation_x_neg"]["distance_to_translation_x_neg_64"]
        ) / 2.0

        analysis["profiles"][profile_name] = {
            "within_scale_accuracy": cls["accuracy"],
            "cross_scale_projection_accuracy": overall_projection_accuracy,
            "translation_projection_accuracy": translation_projection_accuracy,
            "mean_projection_margin": overall_margin,
            "translation_mean_margin": translation_margin,
            "translation_sign_gap": translation_sign_gap,
            "cross_scale_predictions": cross_scale,
            "label_means": label_means,
        }
        ranking_rows.append({
            "profile": profile_name,
            "within_scale_accuracy": cls["accuracy"],
            "cross_scale_projection_accuracy": overall_projection_accuracy,
            "translation_projection_accuracy": translation_projection_accuracy,
            "translation_mean_margin": translation_margin,
            "translation_sign_gap": translation_sign_gap,
            "composite_score": 0.25 * cls["accuracy"] + 0.25 * overall_projection_accuracy + 0.30 * translation_projection_accuracy + 0.20 * max(translation_sign_gap, 0.0) / 5.0,
        })

    ranking_rows.sort(key=lambda row: row["composite_score"], reverse=True)
    analysis["ranking"] = ranking_rows

    (outdir / "stage1_medium_sign_analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2))

    lines = [
        "# Stage-1 medium/sign audit report",
        "",
        "## Decision question",
        "",
        "Does introducing stronger effective-medium damping improve 96-cell translation sign anchoring without collapsing within-scale separability?",
        "",
    ]
    for row in ranking_rows:
        prof = analysis["profiles"][row["profile"]]
        lines.extend([
            f"## Profile: {row['profile']}",
            "",
            f"- within-scale accuracy: {prof['within_scale_accuracy']:.3f}",
            f"- cross-scale projection accuracy: {prof['cross_scale_projection_accuracy']:.3f}",
            f"- translation projection accuracy: {prof['translation_projection_accuracy']:.3f}",
            f"- translation mean margin: {prof['translation_mean_margin']:.3f}",
            f"- translation sign gap: {prof['translation_sign_gap']:.3f}",
            "",
        ])
        txp = prof["label_means"]["translation_x_pos"]
        txn = prof["label_means"]["translation_x_neg"]
        lines.extend([
            f"translation_x_pos distances -> pos64 {txp['distance_to_translation_x_pos_64']:.3f}, neg64 {txp['distance_to_translation_x_neg_64']:.3f}",
            f"translation_x_neg distances -> neg64 {txn['distance_to_translation_x_neg_64']:.3f}, pos64 {txn['distance_to_translation_x_pos_64']:.3f}",
            "",
        ])
    best = ranking_rows[0]
    lines.extend([
        "## Hard conclusion",
        "",
        f"Best profile by composite score: {best['profile']}",
        "",
        "Treat the medium hypothesis as useful only if translation projection accuracy and sign gap improve without crushing within-scale classifiability.",
    ])
    (outdir / "STAGE1_MEDIUM_SIGN_AUDIT_REPORT.md").write_text("\n".join(lines))
    print(f"[OK] medium/sign analysis written to {outdir}")


if __name__ == "__main__":
    main()
