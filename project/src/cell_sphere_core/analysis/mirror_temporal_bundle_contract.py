from __future__ import annotations

from typing import Any

REQUIRED_CASE_KEYS = (
    "dominant_mode",
    "dominant_axis",
    "phase_coverage",
    "overall_scores",
    "active_dominant_mode",
    "active_dominant_axis",
    "mean_active_pair_strength",
    "strongest_bundle",
)


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_mirror_temporal_bundle_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    cases = analysis.get("cases", {})
    required_cases = (
        "floating_static",
        "translation_x_pos",
        "translation_x_neg",
        "rotation_z_pos",
        "rotation_z_neg",
    )
    for case_name in required_cases:
        _require(case_name in cases, f"missing case {case_name}", failures)
    if failures:
        return {"passed": False, "failures": failures}

    for case_name in required_cases:
        case = cases[case_name]
        missing = [key for key in REQUIRED_CASE_KEYS if key not in case]
        _require(not missing, f"{case_name} missing keys: {missing}", failures)

    if failures:
        return {"passed": False, "failures": failures}

    _require(cases["floating_static"]["dominant_mode"] == "static_like", "floating_static dominant_mode must be static_like", failures)
    _require(cases["translation_x_pos"]["active_dominant_mode"] == "translation_like", "translation_x_pos active_dominant_mode must be translation_like", failures)
    _require(cases["translation_x_neg"]["active_dominant_mode"] == "translation_like", "translation_x_neg active_dominant_mode must be translation_like", failures)
    _require(cases["rotation_z_pos"]["active_dominant_mode"] == "rotation_like", "rotation_z_pos active_dominant_mode must be rotation_like", failures)
    _require(cases["rotation_z_neg"]["active_dominant_mode"] == "rotation_like", "rotation_z_neg active_dominant_mode must be rotation_like", failures)
    _require(cases["rotation_z_pos"]["dominant_mode"] == "rotation_like", "rotation_z_pos dominant_mode must be rotation_like", failures)
    _require(cases["rotation_z_neg"]["dominant_mode"] == "rotation_like", "rotation_z_neg dominant_mode must be rotation_like", failures)

    _require(cases["translation_x_pos"]["active_dominant_axis"] == "x", "translation_x_pos active_dominant_axis must be x", failures)
    _require(cases["translation_x_neg"]["active_dominant_axis"] == "x", "translation_x_neg active_dominant_axis must be x", failures)
    _require(cases["rotation_z_pos"]["active_dominant_axis"] == "z", "rotation_z_pos active_dominant_axis must be z", failures)
    _require(cases["rotation_z_neg"]["active_dominant_axis"] == "z", "rotation_z_neg active_dominant_axis must be z", failures)
    _require(cases["rotation_z_pos"]["dominant_axis"] == "z", "rotation_z_pos dominant_axis must be z", failures)
    _require(cases["rotation_z_neg"]["dominant_axis"] == "z", "rotation_z_neg dominant_axis must be z", failures)

    for case_name in ("translation_x_pos", "rotation_z_pos"):
        coverage = cases[case_name].get("phase_coverage", {})
        for phase in ("baseline", "active", "recovery"):
            _require(phase in coverage, f"{case_name} missing phase coverage for {phase}", failures)

    tx_pos = float(cases["translation_x_pos"]["strongest_bundle"].get("active_polarity_projection", 0.0))
    tx_neg = float(cases["translation_x_neg"]["strongest_bundle"].get("active_polarity_projection", 0.0))
    _require(tx_pos * tx_neg < 0.0, f"translation temporal bundle polarity must flip sign, got {tx_pos} and {tx_neg}", failures)
    _require(abs(tx_pos - tx_neg) > 0.01, f"translation temporal bundle polarity separation too small: {abs(tx_pos - tx_neg)}", failures)

    rz_pos = float(cases["rotation_z_pos"]["strongest_bundle"].get("active_circulation_projection", 0.0))
    rz_neg = float(cases["rotation_z_neg"]["strongest_bundle"].get("active_circulation_projection", 0.0))
    _require(rz_pos * rz_neg < 0.0, f"rotation temporal bundle circulation must flip sign, got {rz_pos} and {rz_neg}", failures)
    _require(abs(rz_pos - rz_neg) > 0.01, f"rotation temporal bundle circulation separation too small: {abs(rz_pos - rz_neg)}", failures)

    return {"passed": not failures, "failures": failures}
