from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class RadialBandMaterialProfile:
    stiffness_scale_by_band: np.ndarray
    damping_scale_by_band: np.ndarray
    shear_scale_by_band: np.ndarray



def _linear_profile(num_bands: int, inner_value: float, outer_value: float) -> np.ndarray:
    if num_bands <= 1:
        return np.array([outer_value], dtype=np.float64)
    return np.linspace(inner_value, outer_value, num_bands, dtype=np.float64)



def build_radial_band_material_profile(
    num_bands: int,
    inner_stiffness_scale: float = 0.85,
    outer_stiffness_scale: float = 1.35,
    inner_damping_scale: float = 1.55,
    outer_damping_scale: float = 0.90,
    inner_shear_scale: float = 0.80,
    outer_shear_scale: float = 1.45,
) -> RadialBandMaterialProfile:
    """
    Build a simple radial material gradient.

    Default interpretation:
    - inner bands: softer, more dissipative
    - outer bands: stiffer, more shear-resistant
    """
    return RadialBandMaterialProfile(
        stiffness_scale_by_band=_linear_profile(num_bands, inner_stiffness_scale, outer_stiffness_scale),
        damping_scale_by_band=_linear_profile(num_bands, inner_damping_scale, outer_damping_scale),
        shear_scale_by_band=_linear_profile(num_bands, inner_shear_scale, outer_shear_scale),
    )



def expand_material_profile_to_cells(
    band_index: np.ndarray,
    material_profile: RadialBandMaterialProfile,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    band_index = np.asarray(band_index, dtype=np.int64)
    return (
        material_profile.stiffness_scale_by_band[band_index],
        material_profile.damping_scale_by_band[band_index],
        material_profile.shear_scale_by_band[band_index],
    )
