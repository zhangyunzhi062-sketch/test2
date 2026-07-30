from __future__ import annotations

import math
from collections.abc import Sequence

from .models import PlanningProblem, RouteEvaluation


def route_distance(route: Sequence[int], problem: PlanningProblem) -> float:
    return float(
        sum(
            problem.distance_matrix[start, end]
            for start, end in zip(route[:-1], route[1:])
        )
    )


def _valid_permutation(
    permutation: Sequence[int],
    problem: PlanningProblem,
) -> bool:
    return (
        len(permutation) == len(problem.customer_indices)
        and set(permutation) == set(problem.customer_indices)
    )


def evaluate_tsp(
    permutation: Sequence[int],
    problem: PlanningProblem,
) -> RouteEvaluation:
    if not _valid_permutation(permutation, problem):
        return RouteEvaluation(
            feasible=False,
            total_distance=math.inf,
            routes=(),
            route_distances=(),
            route_loads=(),
            reason="任务点排列缺失、重复或包含非法编号。",
        )

    route = (0, *map(int, permutation), 0)
    distance = route_distance(route, problem)
    load = float(sum(problem.waypoints[index].demand for index in permutation))
    return RouteEvaluation(
        feasible=True,
        total_distance=distance,
        routes=(route,),
        route_distances=(distance,),
        route_loads=(load,),
    )


def evaluate_cdvrp(
    permutation: Sequence[int],
    problem: PlanningProblem,
) -> RouteEvaluation:
    if not _valid_permutation(permutation, problem):
        return RouteEvaluation(
            feasible=False,
            total_distance=math.inf,
            routes=(),
            route_distances=(),
            route_loads=(),
            reason="任务点排列缺失、重复或包含非法编号。",
        )
    if problem.capacity is None or problem.max_route_distance is None:
        return RouteEvaluation(
            feasible=False,
            total_distance=math.inf,
            routes=(),
            route_distances=(),
            route_loads=(),
            reason="CDVRP 缺少单机容量或最大航程。",
        )

    customers = tuple(map(int, permutation))
    customer_count = len(customers)
    # split_cost[start][end] 表示排列中 [start, end) 由一架无人机完成的距离。
    split_cost = [[math.inf] * (customer_count + 1) for _ in range(customer_count)]
    split_load = [[0.0] * (customer_count + 1) for _ in range(customer_count)]
    for start in range(customer_count):
        load = 0.0
        open_distance = 0.0
        previous = 0
        for end in range(start, customer_count):
            customer = customers[end]
            load += problem.waypoints[customer].demand
            open_distance += problem.distance_matrix[previous, customer]
            closed_distance = open_distance + problem.distance_matrix[customer, 0]
            if (
                load > problem.capacity + 1e-9
                or closed_distance > problem.max_route_distance + 1e-9
            ):
                break
            split_cost[start][end + 1] = float(closed_distance)
            split_load[start][end + 1] = float(load)
            previous = customer

    # 未限制车辆数时使用一维动态规划，避免不必要的三次方计算。
    if problem.max_vehicles is None:
        dp = [math.inf] * (customer_count + 1)
        predecessor: list[int | None] = [None] * (customer_count + 1)
        dp[0] = 0.0
        for end in range(1, customer_count + 1):
            for start in range(end):
                candidate = dp[start] + split_cost[start][end]
                if candidate < dp[end]:
                    dp[end] = candidate
                    predecessor[end] = start
        if not math.isfinite(dp[customer_count]):
            return RouteEvaluation(
                feasible=False,
                total_distance=math.inf,
                routes=(),
                route_distances=(),
                route_loads=(),
                reason="当前限制下无可行方案。",
            )
        segments: list[tuple[int, int]] = []
        end = customer_count
        while end > 0:
            start = predecessor[end]
            if start is None:
                return RouteEvaluation(
                    feasible=False,
                    total_distance=math.inf,
                    routes=(),
                    route_distances=(),
                    route_loads=(),
                    reason="路线解码失败。",
                )
            segments.append((start, end))
            end = start
        segments.reverse()
        routes = [(0, *customers[start:end], 0) for start, end in segments]
        distances = [split_cost[start][end] for start, end in segments]
        loads = [split_load[start][end] for start, end in segments]
        return RouteEvaluation(
            feasible=True,
            total_distance=float(sum(distances)),
            routes=tuple(routes),
            route_distances=tuple(distances),
            route_loads=tuple(loads),
        )

    # 有车辆上限时按“车辆数 × 已服务点数”动态规划。
    vehicle_limit = problem.max_vehicles
    dp = [[math.inf] * (customer_count + 1) for _ in range(vehicle_limit + 1)]
    predecessor: list[list[int | None]] = [
        [None] * (customer_count + 1) for _ in range(vehicle_limit + 1)
    ]
    dp[0][0] = 0.0
    for vehicles in range(1, vehicle_limit + 1):
        for end in range(1, customer_count + 1):
            for start in range(end):
                segment = split_cost[start][end]
                candidate = dp[vehicles - 1][start] + segment
                if candidate < dp[vehicles][end]:
                    dp[vehicles][end] = candidate
                    predecessor[vehicles][end] = start

    best_vehicle_count = min(
        range(1, vehicle_limit + 1),
        key=lambda count: dp[count][customer_count],
    )
    if not math.isfinite(dp[best_vehicle_count][customer_count]):
        reason = "当前限制下无可行方案。"
        reason = (
            f"当前排列无法在 {problem.max_vehicles} 架无人机限制内完成；"
            "当前限制下无可行方案。"
        )
        return RouteEvaluation(
            feasible=False,
            total_distance=math.inf,
            routes=(),
            route_distances=(),
            route_loads=(),
            reason=reason,
        )

    segments: list[tuple[int, int]] = []
    end = customer_count
    vehicles = best_vehicle_count
    while end > 0:
        start = predecessor[vehicles][end]
        if start is None:
            return RouteEvaluation(
                feasible=False,
                total_distance=math.inf,
                routes=(),
                route_distances=(),
                route_loads=(),
                reason="路线解码失败。",
            )
        segments.append((start, end))
        end = start
        vehicles -= 1
    segments.reverse()

    routes = [
        (0, *customers[start:end], 0)
        for start, end in segments
    ]
    distances = [split_cost[start][end] for start, end in segments]
    loads = [split_load[start][end] for start, end in segments]
    return RouteEvaluation(
        feasible=True,
        total_distance=float(sum(distances)),
        routes=tuple(routes),
        route_distances=tuple(distances),
        route_loads=tuple(loads),
    )


def evaluate_permutation(
    permutation: Sequence[int],
    problem: PlanningProblem,
) -> RouteEvaluation:
    if problem.problem_type == "TSP":
        return evaluate_tsp(permutation, problem)
    if problem.problem_type == "CDVRP":
        return evaluate_cdvrp(permutation, problem)
    raise ValueError(f"不支持的问题类型：{problem.problem_type}")
