import numpy as np

from cell_sphere_core.tissue.local_volume import compute_local_volume_density_proxies


def test_local_volume_density_proxy_responds_to_compression():
    neighbor_list = [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]

    x_rest = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    x_compressed = x_rest.copy()
    x_compressed[0] = np.array([0.15, 0.15, 0.15], dtype=np.float64)

    rest_volume, rest_density = compute_local_volume_density_proxies(x_rest, neighbor_list)
    compressed_volume, compressed_density = compute_local_volume_density_proxies(x_compressed, neighbor_list)

    assert compressed_volume[0] < rest_volume[0]
    assert compressed_density[0] > rest_density[0]
