from __future__ import annotations

from pathlib import Path

import pytest

from uav_planner.io_excel import _load_legacy_template, load_planning_workbook
from uav_planner.models import Waypoint, WorkbookSettings
from uav_planner.validation import DataValidationError, validate_and_build_problem


class FakeSheet:
    def __init__(self, rows):
        self.rows = rows

    def iter_rows(self, values_only=True):
        assert values_only
        yield from self.rows


class FakeWorkbook:
    def __init__(self, sheets):
        self.sheets = sheets
        self.sheetnames = list(sheets)

    def __getitem__(self, key):
        return self.sheets[key]


def test_chinese_template_can_be_read():
    template = Path(__file__).parents[1] / "无人机路径规划数据模板.xlsx"
    problem, settings = load_planning_workbook(template)
    assert problem.problem_type == "CDVRP"
    assert settings.algorithm == "ACO"
    assert len(problem.waypoints) == 21
    assert problem.dimension == "3D"
    assert len(problem.obstacles) == 2
    assert problem.waypoints[0].z == 20
    assert settings.algorithm_parameters["ACO"]["ant_count"] == 8


def test_legacy_matlab_four_sheet_format_is_supported():
    workbook = FakeWorkbook(
        {
            "City": FakeSheet([(0, 0), (1, 0), (2, 0)]),
            "Demand": FakeSheet([(0,), (2,), (3,)]),
            "Capacity": FakeSheet([(5,)]),
            "Travelcon": FakeSheet([(20,)]),
        }
    )
    points, settings, obstacles = _load_legacy_template(workbook)
    problem = validate_and_build_problem(points, settings)
    assert problem.problem_type == "CDVRP"
    assert problem.capacity == 5
    assert len(problem.waypoints) == 3
    assert obstacles == []


def test_duplicate_waypoint_id_has_clear_error():
    points = [
        Waypoint(0, "基地", 0, 0, 0),
        Waypoint(1, "甲", 1, 0, 1),
        Waypoint(1, "乙", 2, 0, 1),
    ]
    with pytest.raises(DataValidationError, match="编号重复"):
        validate_and_build_problem(points, WorkbookSettings(problem_type="TSP"))


def test_vehicle_lower_bound_is_checked():
    points = [
        Waypoint(0, "基地", 0, 0, 0),
        Waypoint(1, "甲", 1, 0, 6),
        Waypoint(2, "乙", 2, 0, 6),
    ]
    settings = WorkbookSettings(
        problem_type="CDVRP",
        capacity=10,
        max_route_distance=100,
        max_vehicles=1,
    )
    with pytest.raises(DataValidationError, match="当前限制下无可行方案"):
        validate_and_build_problem(points, settings)
