from __future__ import annotations

from cell_sphere_core.analysis.phase_r3 import summarize_phase_r3_audit


def _case(swirl: float, axial: float, circ: float) -> dict:
    return {
        "motif_report": {
            "tracks": {
                "layered_coupling_track": {
                    "active_family_means": {
                        "swirl_circulation_family": swirl,
                        "axial_polar_family": axial,
                    },
                    "active_signed_circulation": circ,
                    "active_axis_balance": {"x": 0.35},
                }
            }
        }
    }


def test_phase_r3_detects_enclosed_stable_component():
    alphas = [340.0, 380.0, 420.0, 460.0, 500.0]
    gains = [0.9, 1.0, 1.1, 1.2, 1.3]
    peak = (420.0, 1.1)
    rows = []
    for a in alphas:
        for g in gains:
            da = int(abs(a - peak[0]) / 40.0)
            dg = int(round(abs(g - peak[1]) / 0.1))
            md = da + dg
            if md == 0:
                swirl, axial, circ = 0.46, 0.20, 0.22
            elif md == 1:
                swirl, axial, circ = 0.40, 0.21, 0.18
            elif md == 2:
                swirl, axial, circ = 0.23, 0.25, 0.08
            else:
                swirl, axial, circ = 0.20, 0.26, 0.03
            rows.append({
                "case_id": f"a{a:.0f}_g{g:.1f}",
                "rotation_alpha": a,
                "swirl_gain": g,
                "circulation_gain": 1.1,
                "axial_base": 0.9,
                "transfer_base": 0.96,
                "circulation_feed": 0.18,
                "rotation_pos": _case(swirl, axial, circ),
                "rotation_neg": _case(swirl - 0.01, axial, -circ),
            })
    report = {
        "metadata": {"rotation_alphas": alphas, "swirl_gains": gains},
        "translation_guard": _case(swirl=0.18, axial=0.40, circ=0.01),
        "rotation_scan": rows,
    }
    audit = summarize_phase_r3_audit(report)
    assert audit["closure"]["component_size"] >= 5
    assert audit["closure"]["boundary_touch"] is False
    assert audit["closure"]["closure_score"] > 0.60
    assert audit["ratings"]["closure"] in {"moderate", "strong"}
