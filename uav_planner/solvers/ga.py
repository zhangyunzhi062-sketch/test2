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
    probability,
    score,
)


class GASolver(Solver):
    algorithm = "GA"

    def solve(
        self,
        problem: PlanningProblem,
        config: dict[str, Any],
        rng: np.random.Generator,
    ) -> PlanningResult:
        started_at = time.perf_counter()
        population_size = max(2, positive_int(config, "population_size", 60))
        generation_key = (
            "tsp_generations" if problem.problem_type == "TSP" else "cdvrp_generations"
        )
        generations = positive_int(
            config,
            generation_key,
            500 if problem.problem_type == "TSP" else 100,
        )
        generation_gap = probability(config, "generation_gap", 0.9)
        crossover_rate = probability(config, "crossover_rate", 0.9)
        mutation_rate = probability(config, "mutation_rate", 0.05)
        seed = int(config.get("seed", 42))

        population = initial_candidates(problem, rng, population_size)
        best_permutation: np.ndarray | None = None
        best_distance = math.inf
        history: list[float] = []

        def tournament(scores: np.ndarray) -> np.ndarray:
            sample = rng.choice(len(population), size=min(3, len(population)), replace=False)
            winner = int(sample[np.argmin(scores[sample])])
            return population[winner]

        for _ in range(generations):
            scores = np.asarray([score(item, problem) for item in population], dtype=float)
            generation_best = int(np.argmin(scores))
            if scores[generation_best] < best_distance:
                best_distance = float(scores[generation_best])
                best_permutation = population[generation_best].copy()

            survivor_count = max(1, int(round(population_size * (1.0 - generation_gap))))
            survivor_indices = np.argsort(scores)[:survivor_count]
            next_population = [population[int(index)].copy() for index in survivor_indices]
            while len(next_population) < population_size:
                first = tournament(scores)
                second = tournament(scores)
                if rng.random() < crossover_rate:
                    child_a, child_b = order_crossover(first, second, rng)
                else:
                    child_a, child_b = first.copy(), second.copy()
                if rng.random() < mutation_rate:
                    child_a = mutate(child_a, rng)
                if rng.random() < mutation_rate:
                    child_b = mutate(child_b, rng)
                next_population.extend([child_a, child_b])
            population = next_population[:population_size]
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
            metadata={"generations": generations, "population_size": population_size},
        )
