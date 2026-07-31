from __future__ import annotations

import numpy as np
import pytest

from uav_planner.environment import InternalBox, segment_crosses_box_interior
from uav_planner.models import ObstacleBox, Waypoint, WorkbookSettings
from uav_planner.validation import DataValidationError, validate_and_build_problem


def test_segment_box_collision_allows_boundary_but_not_interior():
    box = InternalBox(1, np.asarray([4, -1, 0]), np.asarray([6, 1, 5]))
    assert segment_crosses_box_interior(
        np.asarray([0, 0, 2]),
        np.asarray([10, 0, 2]),
        box,
    )
    assert not segment_crosses_box_interior(
        np.asarray([0, -1, 2]),
        np.asarray([10, -1, 2]),
        box,
    )


def test_visibility_graph_detours_around_3d_obstacle():
    points = [
        Waypoint(0, "基地", 0, 0, demand=0, z=2),
        Waypoint(1, "目标", 10, 0, demand=1, z=2),
    ]
    obstacle = ObstacleBox(1, "山体", 4, 6, -1, 1, 0, 5)
    problem = validate_and_build_problem(
        points,
        WorkbookSettings(
            problem_type="TSP",
            dimension="3D",
            min_flight_altitude=0,
            max_flight_altitude=10,
        ),
        [obstacle],
    )
    assert problem.distance_matrix[0, 1] > 10
    assert len(problem.leg_paths[0, 1]) > 2
    internal_box = InternalBox(
        obstacle.obstacle_id,
        np.asarray([obstacle.x_min, obstacle.y_min, obstacle.z_min]),
        np.asarray([obstacle.x_max, obstacle.y_max, obstacle.z_max]),
    )
    path = problem.leg_paths[0, 1]
    assert all(
        not segment_crosses_box_interior(
            np.asarray(start),
            np.asarray(end),
            internal_box,
        )
        for start, end in zip(path[:-1], path[1:])
    )


def test_waypoint_inside_obstacle_is_rejected():
    points = [
        Waypoint(0, "基地", 0, 0, demand=0, z=2),
        Waypoint(1, "目标", 5, 0, demand=1, z=2),
    ]
    obstacle = ObstacleBox(1, "山体", 4, 6, -1, 1, 0, 5)
    with pytest.raises(DataValidationError, match="位于障碍物"):
        validate_and_build_problem(
            points,
            WorkbookSettings(
                problem_type="TSP",
                dimension="3D",
                min_flight_altitude=0,
                max_flight_altitude=10,
            ),
            [obstacle],
        )


def test_geodetic_3d_combines_surface_distance_and_altitude():
    points = [
        Waypoint(0, "基地", 0, 0, demand=0, z=0),
        Waypoint(1, "目标", 0, 1, demand=1, z=1000),
    ]
    problem = validate_and_build_problem(
        points,
        WorkbookSettings(
            problem_type="TSP",
            dimension="3D",
            distance_mode="haversine",
            min_flight_altitude=0,
            max_flight_altitude=2000,
        ),
    )
    assert 111 < problem.distance_matrix[0, 1] < 112


def test_invalid_obstacle_bounds_have_clear_error():
    points = [
        Waypoint(0, "基地", 0, 0, demand=0, z=2),
        Waypoint(1, "目标", 10, 0, demand=1, z=2),
    ]
    obstacle = ObstacleBox(1, "错误区域", 6, 4, -1, 1, 0, 5)
    with pytest.raises(DataValidationError, match="X 最小值必须小于最大值"):
        validate_and_build_problem(
            points,
            WorkbookSettings(
                problem_type="TSP",
                dimension="3D",
                min_flight_altitude=0,
                max_flight_altitude=10,
            ),
            [obstacle],
        )
