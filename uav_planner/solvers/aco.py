from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..models import PlanningProblem, PlanningResult
from ..routing import evaluate_permutation
from .base import Solver
from .common import make_result, positive_float, positive_int, probability


class ACOSolver(Solver):
    algorithm = "ACO"

    def solve(
        self,
        problem: PlanningProblem,
        config: dict[str, Any],
        rng: np.random.Generator,
    ) -> PlanningResult:
        started_at = time.perf_counter()
        ant_count = positive_int(config, "ant_count", 8)
        iterations = positive_int(config, "iterations", 100)
        alpha = positive_float(config, "alpha", 1.0)
        beta = positive_float(config, "beta", 5.0)
        rho = probability(config, "rho", 0.1)
        if rho <= 0:
            raise ValueError("算法参数 rho 必须大于 0 且不超过 1。")
        q = positive_float(config, "q", 1.0)
        seed = int(config.get("seed", 42))

        node_count = len(problem.waypoints)
        pheromone = np.ones((node_count, node_count), dtype=float)
        heuristic = np.zeros_like(problem.distance_matrix, dtype=float)
        positive = problem.distance_matrix > 0
        heuristic[positive] = 1.0 / problem.distance_matrix[positive]

        best_permutation: np.ndarray | None = None
        best_distance = math.inf
        history: list[float] = []

        for _ in range(iterations):
            ant_solutions: list[tuple[np.ndarray, float, tuple[tuple[int, ...], ...]]] = []
            for _ant in range(ant_count):
                unvisited = set(problem.customer_indices)
                permutation: list[int] = []
                current = 0
                while unvisited:
                    choices = np.asarray(sorted(unvisited), dtype=int)
                    weights = (
                        pheromone[current, choices] ** alpha
                        * heuristic[current, choices] ** beta
                    )
                    weight_sum = float(weights.sum())
                    probabilities = (
                        weights / weight_sum
                        if math.isfinite(weight_sum) and weight_sum > 0
                        else np.full(len(choices), 1.0 / len(choices))
                    )
                    selected = int(rng.choice(choices, p=probabilities))
                    permutation.append(selected)
                    unvisited.remove(selected)
                    current = selected

                candidate = np.asarray(permutation, dtype=int)
                evaluation = evaluate_permutation(candidate, problem)
                if evaluation.feasible:
                    ant_solutions.append(
                        (candidate, evaluation.total_distance, evaluation.routes)
                    )
                    if evaluation.total_distance < best_distance:
                        best_distance = evaluation.total_distance
                        best_permutation = candidate.copy()

            pheromone *= 1.0 - rho
            pheromone = np.maximum(pheromone, 1e-12)
            for _candidate, distance, routes in ant_solutions:
                deposit = q / max(distance, 1e-12)
                for route in routes:
                    for start, end in zip(route[:-1], route[1:]):
                        pheromone[start, end] += deposit
                        pheromone[end, start] += deposit
            history.append(best_distance)

        if best_permutation is None:
            from .common import find_feasible_permutation

            best_permutation, evaluation = find_feasible_permutation(problem, rng)
            best_distance = evaluation.total_distance
            history = [
                best_distance if not math.isfinite(value) else value
                for value in history
            ]
        return make_result(
            problem=problem,
            algorithm=self.algorithm,
            seed=seed,
            best_permutation=best_permutation,
            history=history,
            started_at=started_at,
            metadata={"iterations": iterations, "ant_count": ant_count},
        )
