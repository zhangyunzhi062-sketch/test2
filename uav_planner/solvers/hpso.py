from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..models import PlanningProblem, PlanningResult
from .base import Solver
from .common import (
    initial_candidates,
    make_result,
    mutate,
    order_crossover,
    positive_int,
    score,
)


class HPSOSolver(Solver):
    """使用排列交叉和交换变异的离散混合粒子群算法。"""

    algorithm = "HPSO"

    def solve(
        self,
        problem: PlanningProblem,
        config: dict[str, Any],
        rng: np.random.Generator,
    ) -> PlanningResult:
        started_at = time.perf_counter()
        population_size = max(2, positive_int(config, "population_size", 60))
        iterations = positive_int(config, "iterations", 100)
        seed = int(config.get("seed", 42))

        particles = initial_candidates(problem, rng, population_size)
        personal_best = [particle.copy() for particle in particles]
        personal_scores = np.asarray(
            [score(particle, problem) for particle in particles],
            dtype=float,
        )
        global_index = int(np.argmin(personal_scores))
        global_best = personal_best[global_index].copy()
        global_score = float(personal_scores[global_index])
        history: list[float] = []

        for _ in range(iterations):
            for index, particle in enumerate(particles):
                candidate, _ = order_crossover(
                    particle,
                    personal_best[index],
                    rng,
                )
                candidate, _ = order_crossover(candidate, global_best, rng)
                candidate = mutate(candidate, rng)
                candidate_score = score(candidate, problem)
                particles[index] = candidate
                if candidate_score < personal_scores[index]:
                    personal_best[index] = candidate.copy()
                    personal_scores[index] = candidate_score
                    if candidate_score < global_score:
                        global_score = float(candidate_score)
                        global_best = candidate.copy()
            history.append(global_score)

        if not math.isfinite(global_score):
            from .common import find_feasible_permutation

            global_best, evaluation = find_feasible_permutation(problem, rng)
            global_score = evaluation.total_distance
            history = [
                global_score if not math.isfinite(value) else value
                for value in history
            ]
        return make_result(
            problem=problem,
            algorithm=self.algorithm,
            seed=seed,
            best_permutation=global_best,
            history=history,
            started_at=started_at,
            metadata={"iterations": iterations, "population_size": population_size},
        )
