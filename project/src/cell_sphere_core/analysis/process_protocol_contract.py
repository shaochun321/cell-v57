from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_PHASES = ("baseline", "active", "recovery")
MODE_EXPECTATION_BY_CASE = {
    "floating_static": {"overall": "static_like"},
    "translation_x_pos": {"active": "translation_like"},
    "translation_x_neg": {"active": "translation_like"},
    "rotation_z_pos": {"active": "rotation_like"},
    "rotation_z_neg": {"active": "rotation_like"},
}


@dataclass(frozen=True)
class CaseContractResult:
    case_name: str
    passed: bool
    failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "passed": bool(self.passed),
            "failures": list(self.failures),
        }


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...], *, context: str) -> list[str]:
    failures: list[str] = []
    for key in keys:
        if key not in payload:
            failures.append(f"{context}: missing key {key!r}")
    return failures


def validate_case_analysis(case_name: str, case_payload: dict[str, Any]) -> CaseContractResult:
    failures: list[str] = []
    failures.extend(_require_keys(
        case_payload,
        (
            "dominant_mode",
            "dominant_phase",
            "mean_stability_score",
            "mean_recovery_score",
            "mean_mode_margin",
            "phase_counts",
            "phase_dominant_modes",
            "active_dominant_mode",
            "active_mean_mode_margin",
        ),
        context=f"case {case_name}",
    ))

    phase_counts = case_payload.get("phase_counts", {})
    if not isinstance(phase_counts, dict):
        failures.append(f"case {case_name}: phase_counts must be a dict")
        phase_counts = {}

    phase_modes = case_payload.get("phase_dominant_modes", {})
    if not isinstance(phase_modes, dict):
        failures.append(f"case {case_name}: phase_dominant_modes must be a dict")
        phase_modes = {}

    if case_name != "floating_static":
        missing = [phase for phase in REQUIRED_PHASES if phase not in phase_counts]
        if missing:
            failures.append(f"case {case_name}: missing required phases {missing!r}")
    else:
        if "baseline" not in phase_counts:
            failures.append("case floating_static: missing baseline phase")

    expectation = MODE_EXPECTATION_BY_CASE.get(case_name, {})
    expected_overall = expectation.get("overall")
    if expected_overall and str(case_payload.get("dominant_mode", "none")) != expected_overall:
        failures.append(
            f"case {case_name}: dominant_mode expected {expected_overall!r}, got {case_payload.get('dominant_mode')!r}"
        )
    expected_active = expectation.get("active")
    if expected_active and str(case_payload.get("active_dominant_mode", "none")) != expected_active:
        failures.append(
            f"case {case_name}: active_dominant_mode expected {expected_active!r}, got {case_payload.get('active_dominant_mode')!r}"
        )
    if expected_active and str(phase_modes.get("active", "none")) != expected_active:
        failures.append(
            f"case {case_name}: phase_dominant_modes['active'] expected {expected_active!r}, got {phase_modes.get('active')!r}"
        )

    for key in ("mean_stability_score", "mean_recovery_score", "mean_mode_margin", "active_mean_mode_margin"):
        value = float(case_payload.get(key, 0.0))
        if value < 0.0:
            failures.append(f"case {case_name}: {key} must be >= 0, got {value!r}")

    return CaseContractResult(case_name=case_name, passed=not failures, failures=tuple(failures))


def validate_protocol_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    failures.extend(_require_keys(analysis, ("suite", "cases", "gates", "contracts"), context="analysis"))
    cases = analysis.get("cases", {})
    if not isinstance(cases, dict):
        return {
            "passed": False,
            "failures": ["analysis: cases must be a dict"],
            "case_results": [],
        }

    case_results = []
    for case_name in MODE_EXPECTATION_BY_CASE:
        payload = cases.get(case_name)
        if not isinstance(payload, dict):
            failures.append(f"analysis: missing case payload for {case_name!r}")
            continue
        result = validate_case_analysis(case_name, payload)
        case_results.append(result.to_dict())
        failures.extend(result.failures)

    gates = analysis.get("gates", {})
    if not isinstance(gates, dict):
        failures.append("analysis: gates must be a dict")
        gates = {}
    for gate_key in (
        "translation_has_recovery",
        "rotation_has_recovery",
        "translation_has_baseline",
        "rotation_has_baseline",
        "translation_has_active",
        "rotation_has_active",
    ):
        if gates.get(gate_key) is not True:
            failures.append(f"analysis: expected gate {gate_key!r} to be True")

    return {
        "passed": not failures,
        "failures": failures,
        "case_results": case_results,
    }
