from __future__ import annotations

import math
from math import ceil
from collections.abc import Iterable

from .environment import build_obstacle_aware_paths
from .models import ObstacleBox, PlanningProblem, Waypoint, WorkbookSettings


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
    raw_obstacles: Iterable[ObstacleBox] = (),
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
        z = _finite_number(point.z, f"航点 {point.waypoint_id} 的高度")
        demand = _finite_number(point.demand, f"航点 {point.waypoint_id} 的需求量")
        if demand < 0:
            raise DataValidationError(f"航点 {point.waypoint_id} 的需求量不能为负数。")
        normalized_points.append(
            Waypoint(
                waypoint_id=int(point.waypoint_id),
                name=point.name or f"航点{point.waypoint_id}",
                x=x,
                y=y,
                z=z,
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

    dimension = settings.dimension.strip().upper()
    if dimension not in {"2D", "3D"}:
        raise DataValidationError("空间维度只能是 2D 或 3D。")
    if dimension == "2D":
        normalized_points = [
            Waypoint(
                waypoint_id=point.waypoint_id,
                name=point.name,
                x=point.x,
                y=point.y,
                z=0.0,
                demand=point.demand,
                note=point.note,
            )
            for point in normalized_points
        ]
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

    min_flight_altitude: float | None = None
    max_flight_altitude: float | None = None
    if dimension == "3D":
        min_flight_altitude = _finite_number(
            settings.min_flight_altitude,
            "最小飞行高度",
        )
        max_flight_altitude = _finite_number(
            settings.max_flight_altitude,
            "最大飞行高度",
        )
        if min_flight_altitude >= max_flight_altitude:
            raise DataValidationError("最大飞行高度必须大于最小飞行高度。")
        for point in normalized_points:
            if not min_flight_altitude <= point.z <= max_flight_altitude:
                raise DataValidationError(
                    f"航点 {point.waypoint_id} 的高度 {point.z:g} "
                    f"不在 {min_flight_altitude:g} 到 {max_flight_altitude:g} 之间。"
                )

    obstacle_clearance = _finite_number(
        settings.obstacle_clearance,
        "障碍物安全距离",
    )
    if obstacle_clearance < 0:
        raise DataValidationError("障碍物安全距离不能为负数。")

    obstacles: list[ObstacleBox] = []
    obstacle_ids: set[int] = set()
    for obstacle in raw_obstacles:
        if obstacle.obstacle_id in obstacle_ids:
            raise DataValidationError(f"障碍物编号重复：{obstacle.obstacle_id}")
        obstacle_ids.add(obstacle.obstacle_id)
        values = {
            "X最小值": _finite_number(obstacle.x_min, "障碍物 X 最小值"),
            "X最大值": _finite_number(obstacle.x_max, "障碍物 X 最大值"),
            "Y最小值": _finite_number(obstacle.y_min, "障碍物 Y 最小值"),
            "Y最大值": _finite_number(obstacle.y_max, "障碍物 Y 最大值"),
            "Z最小值": _finite_number(obstacle.z_min, "障碍物 Z 最小值"),
            "Z最大值": _finite_number(obstacle.z_max, "障碍物 Z 最大值"),
        }
        if not values["X最小值"] < values["X最大值"]:
            raise DataValidationError(
                f"障碍物 {obstacle.obstacle_id} 的 X 最小值必须小于最大值。"
            )
        if not values["Y最小值"] < values["Y最大值"]:
            raise DataValidationError(
                f"障碍物 {obstacle.obstacle_id} 的 Y 最小值必须小于最大值。"
            )
        if not values["Z最小值"] < values["Z最大值"]:
            raise DataValidationError(
                f"障碍物 {obstacle.obstacle_id} 的 Z 最小值必须小于最大值。"
            )
        if distance_mode == "haversine" and (
            not -90 <= values["X最小值"] <= 90
            or not -90 <= values["X最大值"] <= 90
            or not -180 <= values["Y最小值"] <= 180
            or not -180 <= values["Y最大值"] <= 180
        ):
            raise DataValidationError(
                f"障碍物 {obstacle.obstacle_id} 的经纬度范围不合法。"
            )
        obstacles.append(
            ObstacleBox(
                obstacle_id=obstacle.obstacle_id,
                name=obstacle.name,
                x_min=values["X最小值"],
                x_max=values["X最大值"],
                y_min=values["Y最小值"],
                y_max=values["Y最大值"],
                z_min=values["Z最小值"],
                z_max=values["Z最大值"],
                note=obstacle.note,
            )
        )

    try:
        distance_matrix, leg_paths = build_obstacle_aware_paths(
            tuple(normalized_points),
            tuple(obstacles),
            distance_mode=distance_mode,
            dimension=dimension,
            min_flight_altitude=min_flight_altitude,
            max_flight_altitude=max_flight_altitude,
            clearance=obstacle_clearance,
        )
    except ValueError as exc:
        raise DataValidationError(str(exc)) from exc
    unreachable = [
        normalized_points[index].waypoint_id
        for index in range(1, len(normalized_points))
        if not math.isfinite(distance_matrix[0, index])
    ]
    if unreachable:
        raise DataValidationError(
            f"以下航点被障碍物完全阻断，无法从基地到达：{unreachable}"
        )

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
        dimension=dimension,
        capacity=capacity,
        max_route_distance=max_route_distance,
        max_vehicles=max_vehicles,
        min_flight_altitude=min_flight_altitude,
        max_flight_altitude=max_flight_altitude,
        obstacle_clearance=obstacle_clearance,
        obstacles=tuple(obstacles),
        leg_paths=leg_paths,
    )
