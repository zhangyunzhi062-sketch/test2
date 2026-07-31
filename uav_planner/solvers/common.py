from __future__ import annotations

import itertools
import math
import time
from collections.abc import Sequence
from typing import Any

import numpy as np

from ..models import PlanningProblem, PlanningResult, RouteEvaluation
from ..routing import evaluate_permutation
from .base import PlanningInfeasibleError


def positive_int(config: dict[str, Any], key: str, default: int) -> int:
    value = config.get(key, default)
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"算法参数 {key} 必须是正整数。") from exc
    if not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"算法参数 {key} 必须是正整数。")
    return int(numeric)


def positive_float(config: dict[str, Any], key: str, default: float) -> float:
    value = config.get(key, default)
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"算法参数 {key} 必须大于 0。") from exc
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"算法参数 {key} 必须大于 0。")
    return numeric


def probability(config: dict[str, Any], key: str, default: float) -> float:
    value = float(config.get(key, default))
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"算法参数 {key} 必须在 0 到 1 之间。")
    return value


def score(permutation: Sequence[int], problem: PlanningProblem) -> float:
    evaluation = evaluate_permutation(permutation, problem)
    return evaluation.total_distance if evaluation.feasible else math.inf


def nearest_neighbor(problem: PlanningProblem) -> np.ndarray:
    remaining = set(problem.customer_indices)
    route: list[int] = []
    current = 0
    while remaining:
        next_index = min(
            remaining,
            key=lambda index: problem.distance_matrix[current, index],
        )
        route.append(next_index)
        remaining.remove(next_index)
        current = next_index
    return np.asarray(route, dtype=int)


def initial_candidates(
    problem: PlanningProblem,
    rng: np.random.Generator,
    count: int,
) -> list[np.ndarray]:
    customers = np.asarray(problem.customer_indices, dtype=int)
    points = problem.waypoints
    depot = points[0]
    candidates: list[np.ndarray] = [
        nearest_neighbor(problem),
        nearest_neighbor(problem)[::-1].copy(),
        np.asarray(
            sorted(customers, key=lambda index: points[index].demand, reverse=True),
            dtype=int,
        ),
    ]
    angle_order = np.asarray(
        sorted(
            customers,
            key=lambda index: math.atan2(
                points[index].y - depot.y,
                points[index].x - depot.x,
            ),
        ),
        dtype=int,
    )
    candidates.extend([angle_order, angle_order[::-1].copy()])
    while len(candidates) < count:
        candidates.append(rng.permutation(customers))
    return candidates[:count]


def find_feasible_permutation(
    problem: PlanningProblem,
    rng: np.random.Generator,
    attempts: int = 200,
) -> tuple[np.ndarray, RouteEvaluation]:
    for permutation in initial_candidates(problem, rng, attempts):
        evaluation = evaluate_permutation(permutation, problem)
        if evaluation.feasible:
            return permutation.copy(), evaluation

    # 小问题穷举可以区分“没搜到”和“确实不可行”。
    if len(problem.customer_indices) <= 9:
        for permutation in itertools.permutations(problem.customer_indices):
            evaluation = evaluate_permutation(permutation, problem)
            if evaluation.feasible:
                return np.asarray(permutation, dtype=int), evaluation
    raise PlanningInfeasibleError(
        "当前限制下无可行方案，或可行方案过于狭窄。"
        "请放宽容量、航程、无人机数量限制后重试。"
    )


def order_crossover(
    first: np.ndarray,
    second: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    size = len(first)
    if size < 2:
        return first.copy(), second.copy()
    left, right = sorted(rng.choice(size, size=2, replace=False))
    right += 1

    def make_child(parent_a: np.ndarray, parent_b: np.ndarray) -> np.ndarray:
        child = np.full(size, -1, dtype=int)
        child[left:right] = parent_a[left:right]
        used = set(map(int, child[left:right]))
        remaining = [int(value) for value in parent_b if int(value) not in used]
        positions = list(range(right, size)) + list(range(0, left))
        for position, value in zip(positions, remaining):
            child[position] = value
        return child

    return make_child(first, second), make_child(second, first)


def mutate(permutation: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    result = permutation.copy()
    if len(result) < 2:
        return result
    first, second = sorted(rng.choice(len(result), size=2, replace=False))
    if rng.random() < 0.5:
        result[first], result[second] = result[second], result[first]
    else:
        result[first : second + 1] = result[first : second + 1][::-1]
    return result


def make_result(
    *,
    problem: PlanningProblem,
    algorithm: str,
    seed: int,
    best_permutation: Sequence[int],
    history: Sequence[float],
    started_at: float,
    metadata: dict[str, Any] | None = None,
) -> PlanningResult:
    evaluation = evaluate_permutation(best_permutation, problem)
    if not evaluation.feasible:
        raise PlanningInfeasibleError(evaluation.reason or "当前限制下无可行方案。")
    routes = [
        [problem.waypoint_id_for_index(index) for index in route]
        for route in evaluation.routes
    ]
    route_paths: list[list[list[float]]] = []
    for route in evaluation.routes:
        expanded: list[list[float]] = []
        for start, end in zip(route[:-1], route[1:]):
            leg = problem.leg_paths.get((start, end))
            if leg is None:
                raise PlanningInfeasibleError(
                    f"航点 {problem.waypoint_id_for_index(start)} 到 "
                    f"{problem.waypoint_id_for_index(end)} 没有可行避障路径。"
                )
            points = leg if not expanded else leg[1:]
            expanded.extend([list(map(float, point)) for point in points])
        route_paths.append(expanded)
    clean_history = [
        float(value) if math.isfinite(value) else float(evaluation.total_distance)
        for value in history
    ]
    return PlanningResult(
        problem_type=problem.problem_type,
        algorithm=algorithm,
        seed=seed,
        total_distance=float(evaluation.total_distance),
        routes=routes,
        route_distances=[float(value) for value in evaluation.route_distances],
        route_loads=[float(value) for value in evaluation.route_loads],
        route_paths=route_paths,
        history=clean_history,
        elapsed_seconds=float(time.perf_counter() - started_at),
        distance_mode=problem.distance_mode,
        distance_unit=problem.distance_unit,
        metadata=metadata or {},
    )
