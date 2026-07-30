from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..models import PlanningProblem, PlanningResult
from .base import Solver
from .common import (
    find_feasible_permutation,
    make_result,
    mutate,
    positive_float,
    positive_int,
)
from ..routing import evaluate_permutation


class SASolver(Solver):
    algorithm = "SA"

    def solve(
        self,
        problem: PlanningProblem,
        config: dict[str, Any],
        rng: np.random.Generator,
    ) -> PlanningResult:
        started_at = time.perf_counter()
        initial_temperature = positive_float(config, "initial_temperature", 1000.0)
        final_temperature = positive_float(config, "final_temperature", 0.001)
        chain_length = positive_int(config, "chain_length", 200)
        cooling_rate = float(config.get("cooling_rate", 0.9))
        if not 0.0 < cooling_rate < 1.0:
            raise ValueError("算法参数 cooling_rate 必须大于 0 且小于 1。")
        if final_temperature >= initial_temperature:
            raise ValueError("终止温度必须小于初始温度。")
        seed = int(config.get("seed", 42))

        current, current_evaluation = find_feasible_permutation(problem, rng)
        current_distance = current_evaluation.total_distance
        best = current.copy()
        best_distance = current_distance
        history: list[float] = []
        temperature = initial_temperature

        while temperature > final_temperature:
            for _ in range(chain_length):
                candidate = mutate(current, rng)
                evaluation = evaluate_permutation(candidate, problem)
                if not evaluation.feasible:
                    continue
                difference = evaluation.total_distance - current_distance
                if difference <= 0 or rng.random() < math.exp(-difference / temperature):
                    current = candidate
                    current_distance = evaluation.total_distance
                    if current_distance < best_distance:
                        best = current.copy()
                        best_distance = current_distance
            history.append(best_distance)
            temperature *= cooling_rate

        return make_result(
            problem=problem,
            algorithm=self.algorithm,
            seed=seed,
            best_permutation=best,
            history=history,
            started_at=started_at,
            metadata={
                "temperature_steps": len(history),
                "chain_length": chain_length,
            },
        )
