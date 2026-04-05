import numpy as np

from cell_sphere_core.tissue.reference_state import build_tissue_reference


def test_tissue_reference_builds_multiple_radial_bands():
    x = np.array(
        [
            [0.00, 0.00, 0.00],
            [0.02, 0.00, 0.00],
            [0.04, 0.00, 0.00],
            [0.06, 0.00, 0.00],
            [0.08, 0.00, 0.00],
            [0.10, 0.00, 0.00],
        ],
        dtype=np.float64,
    )
    edges = np.array(
        [
            [0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
            [0, 2], [1, 3], [2, 4], [3, 5],
        ],
        dtype=np.int64,
    )
    is_surface = np.array([False, False, False, True, True, True], dtype=bool)
    center = np.zeros(3, dtype=np.float64)

    ref = build_tissue_reference(x, edges, is_surface, center, num_radial_bands=4)
    assert ref.num_radial_bands >= 3
    assert int(np.sum(ref.radial_band_counts)) == len(x)
    assert np.all(np.diff(ref.radial_band_mean_rest_radius) >= 0.0)
    assert len(ref.radial_band_bounds) == ref.num_radial_bands + 1
    assert np.all(ref.rest_local_volume_proxy > 0.0)
    assert np.all(ref.rest_local_density_proxy > 0.0)
