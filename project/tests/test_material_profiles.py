import numpy as np

from cell_sphere_core.tissue.material_profiles import (
    build_radial_band_material_profile,
    expand_material_profile_to_cells,
)



def test_material_profile_outer_band_is_stiffer_and_more_shear_resistant():
    profile = build_radial_band_material_profile(
        num_bands=4,
        inner_stiffness_scale=0.8,
        outer_stiffness_scale=1.4,
        inner_damping_scale=1.6,
        outer_damping_scale=0.9,
        inner_shear_scale=0.7,
        outer_shear_scale=1.5,
    )
    assert np.all(np.diff(profile.stiffness_scale_by_band) > 0.0)
    assert np.all(np.diff(profile.damping_scale_by_band) < 0.0)
    assert np.all(np.diff(profile.shear_scale_by_band) > 0.0)

    band_index = np.array([0, 1, 3, 2, 0], dtype=np.int64)
    cell_stiffness, cell_damping, cell_shear = expand_material_profile_to_cells(band_index, profile)
    assert cell_stiffness[2] == profile.stiffness_scale_by_band[3]
    assert cell_damping[0] == profile.damping_scale_by_band[0]
    assert cell_shear[3] == profile.shear_scale_by_band[2]
