from __future__ import annotations

import numpy as np

from uav_planner.distance import (
    euclidean_distance_matrix,
    haversine_distance_matrix,
)


def test_euclidean_distance_matrix():
    matrix = euclidean_distance_matrix(np.asarray([[0, 0], [3, 4]], dtype=float))
    assert matrix[0, 1] == 5
    assert np.allclose(matrix, matrix.T)
    assert np.allclose(np.diag(matrix), 0)


def test_haversine_distance_is_in_kilometres():
    matrix = haversine_distance_matrix(
        np.asarray([[0, 0], [0, 1]], dtype=float)
    )
    assert 111 < matrix[0, 1] < 112
    assert np.allclose(matrix, matrix.T)
