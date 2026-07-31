from __future__ import annotations

import numpy as np


EARTH_RADIUS_KM = 6371.0088


def euclidean_distance_matrix(coordinates: np.ndarray) -> np.ndarray:
    """计算任意二维或三维坐标的欧氏距离矩阵。"""

    coordinates = np.asarray(coordinates, dtype=float)
    differences = coordinates[:, None, :] - coordinates[None, :, :]
    matrix = np.sqrt(np.sum(differences * differences, axis=2))
    np.fill_diagonal(matrix, 0.0)
    return matrix


def haversine_distance_matrix(coordinates: np.ndarray) -> np.ndarray:
    """计算纬度、经度坐标之间的球面距离，单位为公里。"""

    coordinates = np.asarray(coordinates, dtype=float)
    latitudes = np.radians(coordinates[:, 0])
    longitudes = np.radians(coordinates[:, 1])

    delta_latitude = latitudes[:, None] - latitudes[None, :]
    delta_longitude = longitudes[:, None] - longitudes[None, :]
    haversine = (
        np.sin(delta_latitude / 2.0) ** 2
        + np.cos(latitudes[:, None])
        * np.cos(latitudes[None, :])
        * np.sin(delta_longitude / 2.0) ** 2
    )
    haversine = np.clip(haversine, 0.0, 1.0)
    matrix = 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(haversine))
    np.fill_diagonal(matrix, 0.0)
    return matrix


def build_distance_matrix(coordinates: np.ndarray, mode: str) -> np.ndarray:
    normalized = mode.strip().lower()
    if normalized == "euclidean":
        return euclidean_distance_matrix(coordinates)
    if normalized == "haversine":
        return haversine_distance_matrix(coordinates)
    raise ValueError(f"不支持的距离模式：{mode}")


def geodetic_3d_distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    """经纬度使用球面距离、高度使用米，返回三维斜距（公里）。"""

    horizontal = haversine_distance_matrix(
        np.asarray([[first[0], first[1]], [second[0], second[1]]], dtype=float)
    )[0, 1]
    vertical = (second[2] - first[2]) / 1000.0
    return float(np.hypot(horizontal, vertical))
