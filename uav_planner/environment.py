from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np

from .distance import EARTH_RADIUS_KM, geodetic_3d_distance
from .models import ObstacleBox, Waypoint


EPSILON = 1e-9


@dataclass(frozen=True)
class InternalBox:
    obstacle_id: int
    minimum: np.ndarray
    maximum: np.ndarray

    def contains_closed(self, point: np.ndarray) -> bool:
        return bool(
            np.all(point >= self.minimum - EPSILON)
            and np.all(point <= self.maximum + EPSILON)
        )


@dataclass(frozen=True)
class CoordinateTransformer:
    distance_mode: str
    reference_latitude: float
    reference_longitude: float

    def to_internal(self, point: tuple[float, float, float]) -> np.ndarray:
        if self.distance_mode == "euclidean":
            return np.asarray(point, dtype=float)
        latitude, longitude, altitude_metres = point
        latitude_radians = math.radians(latitude)
        reference_latitude_radians = math.radians(self.reference_latitude)
        east = (
            EARTH_RADIUS_KM
            * math.cos(reference_latitude_radians)
            * math.radians(longitude - self.reference_longitude)
        )
        north = EARTH_RADIUS_KM * (
            latitude_radians - reference_latitude_radians
        )
        return np.asarray([east, north, altitude_metres / 1000.0], dtype=float)

    def to_display(self, point: np.ndarray) -> tuple[float, float, float]:
        if self.distance_mode == "euclidean":
            return tuple(float(value) for value in point)
        east, north, altitude_km = map(float, point)
        reference_latitude_radians = math.radians(self.reference_latitude)
        latitude = self.reference_latitude + math.degrees(north / EARTH_RADIUS_KM)
        longitude = self.reference_longitude + math.degrees(
            east / (EARTH_RADIUS_KM * math.cos(reference_latitude_radians))
        )
        return latitude, longitude, altitude_km * 1000.0

    def clearance_to_internal(self, clearance: float) -> float:
        return clearance if self.distance_mode == "euclidean" else clearance / 1000.0

    def altitude_to_internal(self, altitude: float) -> float:
        return altitude if self.distance_mode == "euclidean" else altitude / 1000.0


def display_distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    distance_mode: str,
    dimension: str,
) -> float:
    if distance_mode == "haversine":
        if dimension == "3D":
            return geodetic_3d_distance(first, second)
        return geodetic_3d_distance(
            (first[0], first[1], 0.0),
            (second[0], second[1], 0.0),
        )
    axes = 3 if dimension == "3D" else 2
    return float(
        np.linalg.norm(np.asarray(first[:axes]) - np.asarray(second[:axes]))
    )


def _transform_obstacle(
    obstacle: ObstacleBox,
    transformer: CoordinateTransformer,
    clearance: float,
) -> InternalBox:
    corners = [
        transformer.to_internal((x, y, z))
        for x in (obstacle.x_min, obstacle.x_max)
        for y in (obstacle.y_min, obstacle.y_max)
        for z in (obstacle.z_min, obstacle.z_max)
    ]
    stacked = np.vstack(corners)
    internal_clearance = transformer.clearance_to_internal(clearance)
    return InternalBox(
        obstacle_id=obstacle.obstacle_id,
        minimum=stacked.min(axis=0) - internal_clearance,
        maximum=stacked.max(axis=0) + internal_clearance,
    )


def segment_crosses_box_interior(
    start: np.ndarray,
    end: np.ndarray,
    box: InternalBox,
) -> bool:
    """Slab 法检测线段是否进入长方体内部；沿边界绕行不算穿越。"""

    direction = end - start
    lower = box.minimum + EPSILON
    upper = box.maximum - EPSILON
    if np.any(lower >= upper):
        return False
    entry = 0.0
    leave = 1.0
    for axis in range(3):
        if abs(direction[axis]) <= EPSILON:
            if start[axis] <= lower[axis] or start[axis] >= upper[axis]:
                return False
            continue
        first = (lower[axis] - start[axis]) / direction[axis]
        second = (upper[axis] - start[axis]) / direction[axis]
        axis_entry, axis_leave = sorted((first, second))
        entry = max(entry, axis_entry)
        leave = min(leave, axis_leave)
        if leave - entry <= EPSILON:
            return False
    return leave - entry > EPSILON and leave >= 0.0 and entry <= 1.0


def segment_is_clear(
    start: np.ndarray,
    end: np.ndarray,
    boxes: tuple[InternalBox, ...],
) -> bool:
    return not any(segment_crosses_box_interior(start, end, box) for box in boxes)


def _deduplicate_points(points: list[np.ndarray]) -> list[np.ndarray]:
    unique: dict[tuple[float, float, float], np.ndarray] = {}
    for point in points:
        key = tuple(float(value) for value in np.round(point, decimals=10))
        unique.setdefault(key, point)
    return list(unique.values())


def _dijkstra(
    graph: list[list[tuple[int, float]]],
    source: int,
) -> tuple[list[float], list[int | None]]:
    distances = [math.inf] * len(graph)
    predecessors: list[int | None] = [None] * len(graph)
    distances[source] = 0.0
    queue: list[tuple[float, int]] = [(0.0, source)]
    while queue:
        current_distance, node = heapq.heappop(queue)
        if current_distance > distances[node] + EPSILON:
            continue
        for neighbour, weight in graph[node]:
            candidate = current_distance + weight
            if candidate + EPSILON < distances[neighbour]:
                distances[neighbour] = candidate
                predecessors[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
    return distances, predecessors


def _reconstruct_path(
    predecessors: list[int | None],
    source: int,
    target: int,
) -> list[int]:
    path = [target]
    current = target
    while current != source:
        previous = predecessors[current]
        if previous is None:
            return []
        path.append(previous)
        current = previous
    path.reverse()
    return path


def build_obstacle_aware_paths(
    waypoints: tuple[Waypoint, ...],
    obstacles: tuple[ObstacleBox, ...],
    *,
    distance_mode: str,
    dimension: str,
    min_flight_altitude: float | None,
    max_flight_altitude: float | None,
    clearance: float,
) -> tuple[
    np.ndarray,
    dict[tuple[int, int], tuple[tuple[float, float, float], ...]],
]:
    display_points = [
        (point.x, point.y, point.z if dimension == "3D" else 0.0)
        for point in waypoints
    ]
    transformer = CoordinateTransformer(
        distance_mode=distance_mode,
        reference_latitude=waypoints[0].x,
        reference_longitude=waypoints[0].y,
    )

    if not obstacles:
        matrix = np.zeros((len(waypoints), len(waypoints)), dtype=float)
        paths: dict[
            tuple[int, int],
            tuple[tuple[float, float, float], ...],
        ] = {}
        for first in range(len(waypoints)):
            for second in range(len(waypoints)):
                matrix[first, second] = display_distance(
                    display_points[first],
                    display_points[second],
                    distance_mode,
                    dimension,
                )
                paths[first, second] = (
                    display_points[first],
                    display_points[second],
                )
        return matrix, paths

    internal_waypoints = [
        transformer.to_internal(point) for point in display_points
    ]
    internal_boxes = tuple(
        _transform_obstacle(obstacle, transformer, clearance)
        for obstacle in obstacles
    )
    for waypoint, internal_point in zip(waypoints, internal_waypoints):
        for box in internal_boxes:
            if box.contains_closed(internal_point):
                raise ValueError(
                    f"航点 {waypoint.waypoint_id} 位于障碍物 {box.obstacle_id} "
                    "内部或安全边界上。"
                )

    candidates = list(internal_waypoints)
    waypoint_altitudes = [point[2] for point in internal_waypoints]
    median_altitude = float(np.median(waypoint_altitudes))
    internal_min_altitude = (
        transformer.altitude_to_internal(min_flight_altitude)
        if min_flight_altitude is not None
        else min(waypoint_altitudes)
    )
    internal_max_altitude = (
        transformer.altitude_to_internal(max_flight_altitude)
        if max_flight_altitude is not None
        else max(waypoint_altitudes)
    )

    for box in internal_boxes:
        if (
            box.maximum[2] < internal_min_altitude - EPSILON
            or box.minimum[2] > internal_max_altitude + EPSILON
        ):
            continue
        altitude_levels = {
            min(max(box.minimum[2], internal_min_altitude), internal_max_altitude),
            min(max(box.maximum[2], internal_min_altitude), internal_max_altitude),
            internal_min_altitude,
            internal_max_altitude,
            min(max(median_altitude, internal_min_altitude), internal_max_altitude),
        }
        for x in (box.minimum[0], box.maximum[0]):
            for y in (box.minimum[1], box.maximum[1]):
                for z in altitude_levels:
                    candidates.append(np.asarray([x, y, z], dtype=float))

    candidates = _deduplicate_points(candidates)
    mission_node_indices: list[int] = []
    for waypoint_point in internal_waypoints:
        mission_node_indices.append(
            next(
                index
                for index, candidate in enumerate(candidates)
                if np.allclose(candidate, waypoint_point, atol=EPSILON, rtol=0.0)
            )
        )

    valid_candidates = []
    old_to_new: dict[int, int] = {}
    for old_index, point in enumerate(candidates):
        if not internal_min_altitude - EPSILON <= point[2] <= internal_max_altitude + EPSILON:
            continue
        containing_boxes = [
            box for box in internal_boxes if box.contains_closed(point)
        ]
        if containing_boxes and old_index not in mission_node_indices:
            # 候选点必须同时位于它所接触的每一个长方体边界上；
            # 若它落入另一个重叠长方体内部，则不能作为绕行节点。
            on_every_boundary = all(
                np.any(np.isclose(point, box.minimum, atol=EPSILON))
                or np.any(np.isclose(point, box.maximum, atol=EPSILON))
                for box in containing_boxes
            )
            if not on_every_boundary:
                continue
        old_to_new[old_index] = len(valid_candidates)
        valid_candidates.append(point)
    mission_node_indices = [old_to_new[index] for index in mission_node_indices]
    candidates = valid_candidates

    graph: list[list[tuple[int, float]]] = [[] for _ in candidates]
    for first in range(len(candidates)):
        for second in range(first + 1, len(candidates)):
            if not segment_is_clear(
                candidates[first],
                candidates[second],
                internal_boxes,
            ):
                continue
            weight = float(np.linalg.norm(candidates[first] - candidates[second]))
            graph[first].append((second, weight))
            graph[second].append((first, weight))

    matrix = np.full((len(waypoints), len(waypoints)), math.inf, dtype=float)
    paths: dict[
        tuple[int, int],
        tuple[tuple[float, float, float], ...],
    ] = {}
    for source_waypoint, source_node in enumerate(mission_node_indices):
        distances, predecessors = _dijkstra(graph, source_node)
        for target_waypoint, target_node in enumerate(mission_node_indices):
            node_path = _reconstruct_path(predecessors, source_node, target_node)
            if not node_path:
                continue
            display_path = tuple(
                transformer.to_display(candidates[index])
                for index in node_path
            )
            path_distance = sum(
                display_distance(
                    start,
                    end,
                    distance_mode,
                    dimension,
                )
                for start, end in zip(display_path[:-1], display_path[1:])
            )
            matrix[source_waypoint, target_waypoint] = path_distance
            paths[source_waypoint, target_waypoint] = display_path
    np.fill_diagonal(matrix, 0.0)
    return matrix, paths
