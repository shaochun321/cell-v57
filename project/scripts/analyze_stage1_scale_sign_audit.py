from __future__ import annotations

import argparse
import json
from math import sqrt
from pathlib import Path
from typing import Any

TRACKS = ["discrete_channel_track", "local_propagation_track", "layered_coupling_track"]
FAMILIES = [
    "structural_tonic_family",
    "dynamic_phasic_family",
    "axial_polar_family",
    "swirl_circulation_family",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze stage-1 scale/sign audit outputs.")
    p.add_argument("--outdir", type=str, default="outputs/stage1_scale_sign_audit")
    return p.parse_args()


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def extract_features(run_dir: Path) -> dict[str, float]:
    interface = json.loads((run_dir / "interface_trace.json").read_text())
    network = json.loads((run_dir / "interface_network_trace.json").read_text())
    temporal = json.loads((run_dir / "interface_temporal_trace.json").read_text())
    start = max(0, len(interface) - 3)
    window = range(start, len(interface))
    features: dict[str, float] = {}

    for key in ["static", "translation", "rotation", "event", "magnitude", "polarity_abs"]:
        features[f"agg_{key}"] = mean([interface[i]["aggregate_channels"][key] for i in window])

    for channel_name in interface[-1]["mirror_structure"]["bundle_channel_names"]:
        channel_values: list[float] = []
        for i in window:
            channel_values.extend(
                bundle["channels"][channel_name] for bundle in interface[i]["interface_bundles"]
            )
        features[f"bundle_{channel_name}_mean"] = mean(channel_values)

    for track in TRACKS:
        for key in [
            "deformation_drive",
            "vibration_drive",
            "event_flux",
            "dissipation_load",
            "axial_flux",
            "swirl_flux",
            "polarity_projection",
            "circulation_projection",
            "transfer_potential",
            "directional_strength",
            "circulation_strength",
        ]:
            features[f"{track}_{key}"] = mean(
                [network[i]["tracks"][track]["global_channels"][key] for i in window]
            )
        for key in [
            "coherence",
            "polarity_strength",
            "circulation_strength",
            "bundle_energy",
            "transfer_std",
            "polarity_span",
            "circulation_span",
        ]:
            features[f"{track}_{key}"] = mean(
                [network[i]["tracks"][track]["spatial_metrics"][key] for i in window]
            )
        for idx, axis in enumerate(["x", "y", "z"]):
            features[f"{track}_dir_{axis}"] = mean(
                [network[i]["tracks"][track]["direction_vector"][idx] for i in window]
            )
            features[f"{track}_circvec_{axis}"] = mean(
                [network[i]["tracks"][track]["circulation_vector"][idx] for i in window]
            )
            features[f"{track}_source_dir_{axis}"] = mean(
                [temporal[i]["tracks"][track]["source_direction_vector"][idx] for i in window]
            )
            features[f"{track}_source_circ_{axis}"] = mean(
                [temporal[i]["tracks"][track]["source_circulation_vector"][idx] for i in window]
            )
            features[f"{track}_axisbal_{axis}"] = mean(
                [temporal[i]["tracks"][track]["axis_polarity_balance"][axis] for i in window]
            )
        for idx in range(4):
            features[f"{track}_transfer_shell_{idx}"] = mean(
                [temporal[i]["tracks"][track]["transfer_shell_profile"][idx] for i in window]
            )
            features[f"{track}_bandwidth_shell_{idx}"] = mean(
                [temporal[i]["tracks"][track]["bandwidth_shell_profile"][idx] for i in window]
            )
        for prefix in ["transfer_attenuation", "bandwidth_attenuation"]:
            for key in [
                "inner_level",
                "outer_level",
                "outer_inner_ratio",
                "attenuation_index",
                "shell_gradient_mean",
                "shell_gradient_std",
                "peak_shell_index",
                "centroid_shell_index",
            ]:
                features[f"{track}_{prefix}_{key}"] = mean(
                    [temporal[i]["tracks"][track][prefix][key] for i in window]
                )
        features[f"{track}_signed_circulation"] = mean(
            [temporal[i]["tracks"][track]["signed_circulation"] for i in window]
        )
        for family_name in FAMILIES:
            family_traces = [temporal[i]["tracks"][track]["family_trajectories"][family_name] for i in window]
            for idx in range(4):
                features[f"{track}_{family_name}_shell_{idx}"] = mean(
                    [family_trace["shell_profile"][idx] for family_trace in family_traces]
                )
            for key in [
                "inner_level",
                "outer_level",
                "outer_inner_ratio",
                "attenuation_index",
                "shell_gradient_mean",
                "shell_gradient_std",
                "peak_shell_index",
                "centroid_shell_index",
            ]:
                features[f"{track}_{family_name}_{key}"] = mean(
                    [family_trace["attenuation"][key] for family_trace in family_traces]
                )
    return features


def euclidean_distance(a: dict[str, float], b: dict[str, float], keys: list[str]) -> float:
    return sqrt(sum((a[key] - b[key]) ** 2 for key in keys))


def build_stats(samples: list[dict[str, Any]]) -> tuple[list[str], dict[str, float], dict[str, float], list[dict[str, Any]]]:
    feature_names = list(samples[0]["features"].keys())
    means = {name: mean([sample["features"][name] for sample in samples]) for name in feature_names}
    stds = {}
    for name in feature_names:
        variance = mean([(sample["features"][name] - means[name]) ** 2 for sample in samples])
        stds[name] = sqrt(variance) if variance > 0.0 else 1.0
    for sample in samples:
        sample["z_features"] = {name: (sample["features"][name] - means[name]) / stds[name] for name in feature_names}
    return feature_names, means, stds, samples


def classify_with_centroids(samples: list[dict[str, Any]]) -> dict[str, Any]:
    feature_names, means, stds, samples = build_stats(samples)
    seeds = sorted({sample["seed"] for sample in samples})
    predictions: list[dict[str, Any]] = []
    correct = 0
    total = 0
    for test_seed in seeds:
        train = [sample for sample in samples if sample["seed"] != test_seed]
        test = [sample for sample in samples if sample["seed"] == test_seed]
        labels = sorted({sample["label"] for sample in train})
        centroids = {
            label: {name: mean([sample["z_features"][name] for sample in train if sample["label"] == label]) for name in feature_names}
            for label in labels
        }
        for sample in test:
            distances = {label: euclidean_distance(sample["z_features"], centroids[label], feature_names) for label in labels}
            prediction = min(distances, key=distances.get)
            predictions.append({
                "test_seed": test_seed,
                "expected": sample["label"],
                "predicted": prediction,
                "distances": distances,
            })
            correct += int(prediction == sample["label"])
            total += 1
    return {
        "accuracy": correct / total if total else 0.0,
        "num_samples": total,
        "predictions": predictions,
        "feature_names": feature_names,
        "means": means,
        "stds": stds,
    }


def build_centroids(samples: list[dict[str, Any]], feature_names: list[str]) -> dict[str, dict[str, float]]:
    labels = sorted({sample["label"] for sample in samples})
    return {
        label: {name: mean([sample["z_features"][name] for sample in samples if sample["label"] == label]) for name in feature_names}
        for label in labels
    }


def top_feature_drifts(source: dict[str, float], target: dict[str, float], feature_names: list[str], k: int = 12) -> list[dict[str, float]]:
    pairs = []
    for name in feature_names:
        delta = target[name] - source[name]
        pairs.append({"feature": name, "delta": delta, "abs_delta": abs(delta)})
    pairs.sort(key=lambda x: x["abs_delta"], reverse=True)
    return pairs[:k]


def load_panel(panel_dir: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for seed_dir in sorted(panel_dir.glob('seed_*')):
        seed = int(seed_dir.name.split('_')[1])
        for case_dir in sorted(seed_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            samples.append({
                "seed": seed,
                "label": case_dir.name,
                "run_dir": str(case_dir),
                "features": extract_features(case_dir),
                "summary": json.loads((case_dir / 'summary.json').read_text()),
            })
    return samples


def mean_features(samples: list[dict[str, Any]], label: str, feature_names: list[str]) -> dict[str, float]:
    label_samples = [s for s in samples if s['label'] == label]
    return {name: mean([s['z_features'][name] for s in label_samples]) for name in feature_names}


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    panel64 = load_panel(outdir / 'N64')
    panel96 = load_panel(outdir / 'N96')

    cls64 = classify_with_centroids(panel64)
    cls96 = classify_with_centroids(panel96)

    feature_names = cls64['feature_names']
    means = cls64['means']
    stds = cls64['stds']

    for sample in panel96:
        sample['z_features'] = {name: (sample['features'][name] - means[name]) / stds[name] for name in feature_names}
    centroids64 = build_centroids(panel64, feature_names)

    cross_scale = []
    for sample in panel96:
        distances = {label: euclidean_distance(sample['z_features'], centroid, feature_names) for label, centroid in centroids64.items()}
        ordered = sorted(distances.items(), key=lambda kv: kv[1])
        cross_scale.append({
            'seed': sample['seed'],
            'label': sample['label'],
            'predicted_against_N64': ordered[0][0],
            'distance_margin_to_second': ordered[1][1] - ordered[0][1],
            'distances': distances,
        })

    # Aggregate mean features by label using N64 scaling, then compare N96 label centroids to N64 label centroids.
    # First assign z_features to panel64 similarly.
    for sample in panel64:
        sample['z_features'] = {name: (sample['features'][name] - means[name]) / stds[name] for name in feature_names}

    drifts = {}
    labels = sorted({s['label'] for s in panel64})
    for label in labels:
        centroid64 = mean_features(panel64, label, feature_names)
        centroid96 = mean_features(panel96, label, feature_names)
        drifts[label] = {
            'distance_to_same_label_64': euclidean_distance(centroid96, centroid64, feature_names),
            'distance_to_translation_x_pos_64': euclidean_distance(centroid96, mean_features(panel64, 'translation_x_pos', feature_names), feature_names),
            'distance_to_translation_x_neg_64': euclidean_distance(centroid96, mean_features(panel64, 'translation_x_neg', feature_names), feature_names),
            'top_feature_drifts_vs_same_label_64': top_feature_drifts(centroid64, centroid96, feature_names),
        }

    report = {
        'protocol': 'stage1_scale_sign_audit',
        'classification_N64': {k: cls64[k] for k in ['accuracy', 'num_samples', 'predictions']},
        'classification_N96': {k: cls96[k] for k in ['accuracy', 'num_samples', 'predictions']},
        'cross_scale_projection_N96_to_N64': cross_scale,
        'label_drifts_N96_vs_N64': drifts,
    }

    (outdir / 'stage1_scale_sign_analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))

    lines = [
        '# Stage-1 scale/sign audit report',
        '',
        '## Decision',
        '',
        'The 64-cell panel remains the stable primary reference. The audit now tests whether the same response families survive at 96 cells without collapsing sign structure under translation.',
        '',
        '## Within-scale classification',
        '',
        f"- N64 leave-one-seed-out accuracy: {cls64['accuracy']:.3f}",
        f"- N96 leave-one-seed-out accuracy: {cls96['accuracy']:.3f}",
        '',
        'Interpretation: if N96 stays classifiable within its own scale but mis-projects against N64, the problem is scale transfer and sign anchoring, not total signal collapse.',
        '',
        '## N96 projected against N64 centroids',
        '',
    ]
    for entry in cross_scale:
        lines.append(f"- seed {entry['seed']} {entry['label']}: projected to {entry['predicted_against_N64']} (margin to second: {entry['distance_margin_to_second']:.3f})")
    txp = drifts['translation_x_pos']
    lines.extend([
        '',
        '## Translation x_pos drift',
        '',
        f"- N96 translation_x_pos centroid distance to N64 translation_x_pos: {txp['distance_to_same_label_64']:.3f}",
        f"- N96 translation_x_pos centroid distance to N64 translation_x_neg: {txp['distance_to_translation_x_neg_64']:.3f}",
        f"- N96 translation_x_pos centroid distance to N64 translation_x_pos: {txp['distance_to_translation_x_pos_64']:.3f}",
        '',
        'Top drifting features for translation_x_pos:',
    ])
    for item in txp['top_feature_drifts_vs_same_label_64']:
        lines.append(f"- {item['feature']}: delta {item['delta']:.3f}")
    lines.extend([
        '',
        '## Hard conclusion',
        '',
        'If N96 remains separable within-scale yet translation_x_pos drifts toward the N64 translation_x_neg reference, then the next refactor target is scale-dependent sign anchoring. The project should not reopen old downstream signed-readout patches. It should instead isolate which interface/track features invert or drift under scale change and tighten anchoring there.',
    ])


    (outdir / 'STAGE1_SCALE_SIGN_AUDIT_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'[OK] analysis outputs: {outdir}')


if __name__ == '__main__':
    main()
