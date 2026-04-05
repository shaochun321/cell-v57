from cell_sphere_core.reference.sizing import estimate_reference_sphere


def test_reference_radius_scales_with_count():
    ref_small = estimate_reference_sphere(num_cells=100, cell_radius=0.004)
    ref_large = estimate_reference_sphere(num_cells=800, cell_radius=0.004)
    assert ref_large.target_radius > ref_small.target_radius
    ratio = ref_large.target_radius / ref_small.target_radius
    assert 1.9 < ratio < 2.2
