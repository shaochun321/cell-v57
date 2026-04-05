from __future__ import annotations

from typing import Any

REQUIRED_CASE_KEYS = (
    "dominant_mode",
    "dominant_phase",
    "phase_counts",
    "phase_dominant_modes",
    "active_dominant_mode",
    "mean_shell_strength",
    "outermost_shell",
)


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_mirror_shell_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    cases = payload.get("cases", {})
    for case_name in ("floating_static", "translation_x_pos", "translation_x_neg", "rotation_z_pos", "rotation_z_neg"):
        case = cases.get(case_name)
        _require(isinstance(case, dict), f"missing case payload: {case_name}", failures)
        if not isinstance(case, dict):
            continue
        missing = [key for key in REQUIRED_CASE_KEYS if key not in case]
        _require(not missing, f"{case_name} missing keys: {missing}", failures)

    if failures:
        return {"passed": False, "failures": failures}

    _require(cases["floating_static"]["dominant_mode"] == "static_like", "floating_static dominant_mode must be static_like", failures)
    _require(cases["translation_x_pos"]["active_dominant_mode"] == "translation_like", "translation_x_pos active_dominant_mode must be translation_like", failures)
    _require(cases["translation_x_neg"]["active_dominant_mode"] == "translation_like", "translation_x_neg active_dominant_mode must be translation_like", failures)
    _require(cases["rotation_z_pos"]["active_dominant_mode"] == "rotation_like", "rotation_z_pos active_dominant_mode must be rotation_like", failures)
    _require(cases["rotation_z_neg"]["active_dominant_mode"] == "rotation_like", "rotation_z_neg active_dominant_mode must be rotation_like", failures)

    for case_name in ("translation_x_pos", "rotation_z_pos"):
        phase_counts = cases[case_name].get("phase_counts", {})
        for phase in ("baseline", "active", "recovery"):
            _require(phase in phase_counts, f"{case_name} missing phase coverage for {phase}", failures)

    tx_pos = float(cases["translation_x_pos"]["outermost_shell"].get("axis_polarity_balance", {}).get("x", 0.0))
    tx_neg = float(cases["translation_x_neg"]["outermost_shell"].get("axis_polarity_balance", {}).get("x", 0.0))
    _require(tx_pos * tx_neg < 0.0, f"translation outermost-shell x balance must flip sign, got {tx_pos} and {tx_neg}", failures)
    _require(abs(tx_pos - tx_neg) > 0.01, f"translation outermost-shell x balance separation too small: {abs(tx_pos - tx_neg)}", failures)

    rz_pos = float(cases["rotation_z_pos"]["outermost_shell"].get("circulation_axis_balance", {}).get("z", 0.0))
    rz_neg = float(cases["rotation_z_neg"]["outermost_shell"].get("circulation_axis_balance", {}).get("z", 0.0))
    _require(rz_pos * rz_neg < 0.0, f"rotation outermost-shell z circulation must flip sign, got {rz_pos} and {rz_neg}", failures)
    _require(abs(rz_pos - rz_neg) > 0.01, f"rotation outermost-shell z circulation separation too small: {abs(rz_pos - rz_neg)}", failures)

    return {"passed": not failures, "failures": failures}
