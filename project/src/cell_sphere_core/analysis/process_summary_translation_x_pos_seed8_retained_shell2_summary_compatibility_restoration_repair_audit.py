from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _active_x_pair_rows(atlas_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window_index, atlas_row in enumerate(atlas_trace):
        if str(atlas_row.get("phase", "baseline")) != "active":
            continue
        pair_rows = [
            {
                "shell_index": int(pair.get("shell_index", -1)),
                "pair_key": str(pair.get("pair_key", "none")),
                "dominant_mode": str(pair.get("dominant_mode", "none")),
                "direction_sign": float(pair.get("direction_sign", 0.0)),
                "pair_strength": float(pair.get("pair_strength", 0.0)),
                "handoff_gate_score": float(pair.get("handoff_gate_score", 0.0)),
                "translation_like": float(pair.get("mode_scores", {}).get("translation_like", 0.0)),
                "static_like": float(pair.get("mode_scores", {}).get("static_like", 0.0)),
                "polarity_projection": float(pair.get("pair_differential_mode", {}).get("polarity_projection", 0.0)),
            }
            for pair in sorted(
                [item for item in atlas_row.get("pair_summaries", []) if str(item.get("axis", "none")) == "x"],
                key=lambda item: int(item.get("shell_index", -1)),
            )
        ]
        rows.append(
            {
                "window_index": int(window_index),
                "window_start": float(atlas_row.get("window_start", 0.0)),
                "window_end": float(atlas_row.get("window_end", 0.0)),
                "atlas_dominant_mode": str(atlas_row.get("atlas_dominant_mode", "none")),
                "atlas_dominant_axis": str(atlas_row.get("atlas_dominant_axis", "none")),
                "pair_rows": pair_rows,
            }
        )
    return rows


def _active_translation_carrier_counts(active_rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_shell: dict[int, int] = {}
    total = 0
    for window in active_rows:
        for row in window["pair_rows"]:
            if row["dominant_mode"] == "translation_like" and row["direction_sign"] > 0.0:
                shell_index = int(row["shell_index"])
                per_shell[shell_index] = per_shell.get(shell_index, 0) + 1
                total += 1
    return {
        "total": int(total),
        "per_shell": {str(shell): int(count) for shell, count in sorted(per_shell.items())},
    }


def _phase_x_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json["phase_summaries"]["active"]["axis_summaries"]["x"])


def _phase_summary(summary_json: dict[str, Any]) -> dict[str, Any]:
    return dict(summary_json["phase_summaries"]["active"])


def _second_active_shell2_row(active_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(active_rows) < 2:
        return {}
    return next((row for row in active_rows[1]["pair_rows"] if int(row["shell_index"]) == 2), {})


def build_translation_x_pos_seed8_retained_shell2_summary_compatibility_restoration_repair_audit(
    *,
    repeatability_audit_path: str | Path,
    seed8_baseline_summary_path: str | Path,
    seed8_baseline_atlas_trace_path: str | Path,
    seed8_repaired_summary_path: str | Path,
    seed8_repaired_atlas_trace_path: str | Path,
    seed8_xneg_summary_path: str | Path,
    seed8_rotation_summary_path: str | Path,
    seed8_round48_summary_path: str | Path,
) -> dict[str, Any]:
    repeatability = _load_json(repeatability_audit_path)
    seed8_base_summary = _load_json(seed8_baseline_summary_path)
    seed8_base_rows = _active_x_pair_rows(_load_json(seed8_baseline_atlas_trace_path))
    seed8_repaired_summary = _load_json(seed8_repaired_summary_path)
    seed8_repaired_rows = _active_x_pair_rows(_load_json(seed8_repaired_atlas_trace_path))
    seed8_xneg_summary = _load_json(seed8_xneg_summary_path)
    seed8_rotation_summary = _load_json(seed8_rotation_summary_path)
    seed8_round48_summary = _load_json(seed8_round48_summary_path)

    seed8_base_counts = _active_translation_carrier_counts(seed8_base_rows)
    seed8_repaired_counts = _active_translation_carrier_counts(seed8_repaired_rows)

    seed8_base_active_x = _phase_x_summary(seed8_base_summary)
    seed8_repaired_active_x = _phase_x_summary(seed8_repaired_summary)
    seed8_round48_active_x = _phase_x_summary(seed8_round48_summary)
    seed8_xneg_active = _phase_x_summary(seed8_xneg_summary)
    seed8_rotation_active = _phase_summary(seed8_rotation_summary)

    baseline_shell2_second = _second_active_shell2_row(seed8_base_rows)
    repaired_shell2_second = _second_active_shell2_row(seed8_repaired_rows)

    evidence = {
        "baseline_round49_seed8_second_active_shell2_translation_like": bool(baseline_shell2_second) and baseline_shell2_second.get("dominant_mode") == "translation_like",
        "repaired_round50_seed8_second_active_shell2_translation_like": bool(repaired_shell2_second) and repaired_shell2_second.get("dominant_mode") == "translation_like",
        "repaired_round50_seed8_second_active_shell2_positive_sign": bool(repaired_shell2_second) and float(repaired_shell2_second.get("direction_sign", 0.0)) > 0.0,
        "repaired_seed8_translation_x_pos_active_mean_exceeds_round49": abs(float(seed8_repaired_active_x.get("mean_polarity_projection", 0.0))) > abs(float(seed8_base_active_x.get("mean_polarity_projection", 0.0))),
        "repaired_seed8_translation_x_pos_active_mean_recovers_round48": abs(float(seed8_repaired_active_x.get("mean_polarity_projection", 0.0))) > abs(float(seed8_round48_active_x.get("mean_polarity_projection", 0.0))),
        "repaired_seed8_active_translation_carrier_total_preserved": int(seed8_repaired_counts["total"]) == int(seed8_base_counts["total"]),
        "repaired_seed8_shell2_translation_carrier_count_preserved": int(seed8_repaired_counts["per_shell"].get("2", 0)) == int(seed8_base_counts["per_shell"].get("2", 0)),
        "repaired_seed8_translation_x_pos_active_mode_axis_preserved": str(seed8_repaired_summary["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(seed8_repaired_summary["phase_summaries"]["active"]["dominant_axis"]) == "x",
        "repaired_seed8_translation_x_neg_sign_preserved": str(seed8_xneg_summary["phase_summaries"]["active"]["dominant_mode"]) == "translation_like" and str(seed8_xneg_summary["phase_summaries"]["active"]["dominant_axis"]) == "x" and float(seed8_xneg_active.get("direction_sign", 0.0)) < 0.0,
        "repaired_seed8_rotation_z_guardrail_preserved": str(seed8_rotation_active.get("dominant_mode", "none")) == "rotation_like" and str(seed8_rotation_active.get("dominant_axis", "none")) == "z",
    }
    contracts_passed = all(evidence.values())

    return {
        "suite": "translation_x_pos_seed8_retained_shell2_summary_compatibility_restoration_repair_audit_r1",
        "contracts": {"passed": contracts_passed},
        "repeatability_failures": list(repeatability.get("contracts", {}).get("failures", []) or repeatability.get("failures", []) or []),
        "seed8_round49_baseline": {
            "active_translation_carrier_counts": seed8_base_counts,
            "phase_active_x_summary": seed8_base_active_x,
            "second_active_shell2_row": baseline_shell2_second,
            "active_x_pair_rows": seed8_base_rows,
        },
        "seed8_round50_repaired": {
            "active_translation_carrier_counts": seed8_repaired_counts,
            "phase_active_x_summary": seed8_repaired_active_x,
            "second_active_shell2_row": repaired_shell2_second,
            "active_x_pair_rows": seed8_repaired_rows,
        },
        "seed8_round48_reference": {
            "phase_active_x_summary": seed8_round48_active_x,
        },
        "guardrails": {
            "seed8_translation_x_neg_active_x_summary": seed8_xneg_active,
            "seed8_rotation_z_pos_active_summary": seed8_rotation_active,
        },
        "evidence": evidence,
        "inferred_outcome": "translation_x_pos_seed8_retained_shell2_summary_compatibility_restoration_repair_success" if contracts_passed else "undetermined",
        "residual_issue": "active_x_amplitude_gap_to_seed7_still_large",
    }
