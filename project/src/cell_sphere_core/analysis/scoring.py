from __future__ import annotations


def near_sphere_score(metrics: dict) -> float:
    sag = float(metrics.get("sag_ratio", 0.0))
    vol = abs(1.0 - float(metrics.get("volume_ratio", 1.0)))
    shape = float(metrics.get("shape_deviation", 0.0))
    radius_cv = float(metrics.get("radius_cv", 0.0))
    asph = float(metrics.get("asphericity", 0.0))
    floor_contact = float(metrics.get("floor_contact_ratio", 0.0))
    kinetic = float(metrics.get("kinetic_energy", 0.0))
    return (
        2.0 * sag
        + 2.5 * vol
        + 4.0 * shape
        + 3.0 * radius_cv
        + 2.0 * asph
        + 1.5 * floor_contact
        + 0.05 * kinetic
    )
