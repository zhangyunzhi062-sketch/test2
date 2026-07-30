from __future__ import annotations

import pytest

from uav_planner.models import Waypoint, WorkbookSettings
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
