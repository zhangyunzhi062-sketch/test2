from __future__ import annotations

import math
from math import ceil
from collections.abc import Iterable

import numpy as np

from .distance import build_distance_matrix
from .models import PlanningProblem, Waypoint, WorkbookSettings


class DataValidationError(ValueError):
    """Excel 数据或任务设置不合法。"""


def _finite_number(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DataValidationError(f"{label} 必须是数字。") from exc
    if not math.isfinite(number):
        raise DataValidationError(f"{label} 必须是有限数字。")
    return number


def validate_and_build_problem(
    raw_waypoints: Iterable[Waypoint],
    settings: WorkbookSettings,
) -> PlanningProblem:
    points = list(raw_waypoints)
    if len(points) < 2:
        raise DataValidationError("至少需要 1 个基地和 1 个启用任务点。")

    ids = [point.waypoint_id for point in points]
    if len(ids) != len(set(ids)):
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        raise DataValidationError(f"航点编号重复：{duplicates}")
    if 0 not in ids:
        raise DataValidationError("必须存在编号为 0 的启用基地。")

    depot = next(point for point in points if point.waypoint_id == 0)
    customers = [point for point in points if point.waypoint_id != 0]
    ordered = [depot, *customers]

    normalized_points: list[Waypoint] = []
    for point in ordered:
        x = _finite_number(point.x, f"航点 {point.waypoint_id} 的第一列坐标")
        y = _finite_number(point.y, f"航点 {point.waypoint_id} 的第二列坐标")
        demand = _finite_number(point.demand, f"航点 {point.waypoint_id} 的需求量")
        if demand < 0:
            raise DataValidationError(f"航点 {point.waypoint_id} 的需求量不能为负数。")
        normalized_points.append(
            Waypoint(
                waypoint_id=int(point.waypoint_id),
                name=point.name or f"航点{point.waypoint_id}",
                x=x,
                y=y,
                demand=demand,
                note=point.note,
            )
        )

    if abs(normalized_points[0].demand) > 1e-9:
        raise DataValidationError("基地（编号 0）的需求量必须为 0。")

    problem_type = settings.problem_type.strip().upper()
    if problem_type not in {"TSP", "CDVRP"}:
        raise DataValidationError("问题类型只能是 TSP 或 CDVRP。")

    distance_mode = settings.distance_mode.strip().lower()
    if distance_mode not in {"euclidean", "haversine"}:
        raise DataValidationError("距离模式只能是 euclidean 或 haversine。")

    coordinates = np.asarray([(point.x, point.y) for point in normalized_points], dtype=float)
    if distance_mode == "haversine":
        invalid_latitudes = [
            point.waypoint_id for point in normalized_points if not -90 <= point.x <= 90
        ]
        invalid_longitudes = [
            point.waypoint_id for point in normalized_points if not -180 <= point.y <= 180
        ]
        if invalid_latitudes:
            raise DataValidationError(
                f"以下航点的纬度不在 -90 到 90 之间：{invalid_latitudes}"
            )
        if invalid_longitudes:
            raise DataValidationError(
                f"以下航点的经度不在 -180 到 180 之间：{invalid_longitudes}"
            )

    distance_matrix = build_distance_matrix(coordinates, distance_mode)

    capacity: float | None = None
    max_route_distance: float | None = None
    max_vehicles: int | None = None
    if problem_type == "CDVRP":
        capacity = _finite_number(settings.capacity, "单机容量")
        max_route_distance = _finite_number(settings.max_route_distance, "单机最大航程")
        if capacity <= 0:
            raise DataValidationError("单机容量必须大于 0。")
        if max_route_distance <= 0:
            raise DataValidationError("单机最大航程必须大于 0。")
        if settings.max_vehicles is not None:
            try:
                max_vehicles = int(settings.max_vehicles)
            except (TypeError, ValueError) as exc:
                raise DataValidationError("最大无人机数量必须是正整数或留空。") from exc
            if max_vehicles <= 0:
                raise DataValidationError("最大无人机数量必须是正整数或留空。")
            minimum_by_capacity = ceil(
                sum(point.demand for point in normalized_points[1:]) / capacity
            )
            if minimum_by_capacity > max_vehicles:
                raise DataValidationError(
                    "当前限制下无可行方案：仅按总需求量计算就至少需要 "
                    f"{minimum_by_capacity} 架无人机，但最大无人机数量为 {max_vehicles}。"
                )

        for index, point in enumerate(normalized_points[1:], start=1):
            if point.demand > capacity + 1e-9:
                raise DataValidationError(
                    f"航点 {point.waypoint_id} 的需求量 {point.demand:g} "
                    f"超过单机容量 {capacity:g}。"
                )
            round_trip = distance_matrix[0, index] + distance_matrix[index, 0]
            if round_trip > max_route_distance + 1e-9:
                raise DataValidationError(
                    f"航点 {point.waypoint_id} 的最短往返距离 {round_trip:.2f} "
                    f"超过单机最大航程 {max_route_distance:g}。"
                )

    unit = "km" if distance_mode == "haversine" else (settings.distance_unit or "单位")
    return PlanningProblem(
        problem_type=problem_type,
        waypoints=tuple(normalized_points),
        distance_matrix=distance_matrix,
        distance_mode=distance_mode,
        distance_unit=str(unit),
        capacity=capacity,
        max_route_distance=max_route_distance,
        max_vehicles=max_vehicles,
    )
