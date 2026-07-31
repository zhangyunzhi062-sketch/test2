from __future__ import annotations

import pytest

from uav_planner.models import ObstacleBox, Waypoint, WorkbookSettings
from uav_planner.validation import validate_and_build_problem


@pytest.fixture
def sample_waypoints() -> list[Waypoint]:
    return [
        Waypoint(0, "基地", 0, 0, 0),
        Waypoint(1, "甲", 1, 1, 2),
        Waypoint(2, "乙", 2, 0, 2),
        Waypoint(3, "丙", 4, 1, 3),
        Waypoint(4, "丁", 5, 0, 1),
        Waypoint(5, "戊", 3, 3, 2),
    ]


@pytest.fixture
def tsp_problem(sample_waypoints):
    return validate_and_build_problem(
        sample_waypoints,
        WorkbookSettings(problem_type="TSP", distance_unit="km"),
    )


@pytest.fixture
def cdvrp_problem(sample_waypoints):
    return validate_and_build_problem(
        sample_waypoints,
        WorkbookSettings(
            problem_type="CDVRP",
            capacity=6,
            max_route_distance=30,
            max_vehicles=3,
            distance_unit="km",
        ),
    )


@pytest.fixture
def obstacle_waypoints() -> list[Waypoint]:
    return [
        Waypoint(0, "基地", 0, 0, demand=0, z=2),
        Waypoint(1, "甲", 10, 0, demand=2, z=2),
        Waypoint(2, "乙", 10, 5, demand=2, z=3),
        Waypoint(3, "丙", 0, 5, demand=3, z=3),
        Waypoint(4, "丁", 5, 8, demand=1, z=4),
        Waypoint(5, "戊", 12, 8, demand=2, z=2),
    ]


@pytest.fixture
def obstacle_box() -> ObstacleBox:
    return ObstacleBox(
        1,
        "山体",
        x_min=4,
        x_max=6,
        y_min=-1,
        y_max=6,
        z_min=0,
        z_max=6,
    )


@pytest.fixture
def obstacle_tsp_problem(obstacle_waypoints, obstacle_box):
    return validate_and_build_problem(
        obstacle_waypoints,
        WorkbookSettings(
            problem_type="TSP",
            dimension="3D",
            min_flight_altitude=0,
            max_flight_altitude=10,
            distance_unit="km",
        ),
        [obstacle_box],
    )


@pytest.fixture
def obstacle_cdvrp_problem(obstacle_waypoints, obstacle_box):
    return validate_and_build_problem(
        obstacle_waypoints,
        WorkbookSettings(
            problem_type="CDVRP",
            dimension="3D",
            capacity=6,
            max_route_distance=100,
            max_vehicles=3,
            min_flight_altitude=0,
            max_flight_altitude=10,
            distance_unit="km",
        ),
        [obstacle_box],
    )
