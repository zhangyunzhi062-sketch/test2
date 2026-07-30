from __future__ import annotations

import numpy as np
import pytest

from uav_planner.registry import create_solver


CONFIGS = {
    "ACO": {
        "ant_count": 4,
        "iterations": 4,
        "alpha": 1,
        "beta": 3,
        "rho": 0.1,
        "q": 1,
    },
    "GA": {
        "population_size": 8,
        "tsp_generations": 4,
        "cdvrp_generations": 4,
        "generation_gap": 0.75,
        "crossover_rate": 0.9,
        "mutation_rate": 0.2,
    },
    "HPSO": {"population_size": 8, "iterations": 4},
    "SA": {
        "initial_temperature": 10,
        "final_temperature": 1,
        "chain_length": 5,
        "cooling_rate": 0.5,
    },
}


@pytest.mark.parametrize("problem_fixture", ["tsp_problem", "cdvrp_problem"])
@pytest.mark.parametrize("algorithm", ["ACO", "GA", "HPSO", "SA"])
def test_all_eight_solver_entries_return_feasible_routes(
    request,
    problem_fixture,
    algorithm,
):
    problem = request.getfixturevalue(problem_fixture)
    config = {**CONFIGS[algorithm], "seed": 42}
    result = create_solver(algorithm).solve(
        problem,
        config,
        np.random.default_rng(42),
    )

    visited = [waypoint for route in result.routes for waypoint in route[1:-1]]
    assert sorted(visited) == [1, 2, 3, 4, 5]
    assert len(visited) == len(set(visited))
    assert all(route[0] == 0 and route[-1] == 0 for route in result.routes)
    assert result.history
    assert result.total_distance == result.history[-1] or (
        result.total_distance <= min(result.history)
    )

    if problem.problem_type == "CDVRP":
        assert len(result.routes) <= problem.max_vehicles
        assert all(load <= problem.capacity for load in result.route_loads)
        assert all(
            distance <= problem.max_route_distance
            for distance in result.route_distances
        )


def test_fixed_seed_is_reproducible(tsp_problem):
    config = {**CONFIGS["ACO"], "seed": 7}
    first = create_solver("ACO").solve(
        tsp_problem,
        config,
        np.random.default_rng(7),
    )
    second = create_solver("ACO").solve(
        tsp_problem,
        config,
        np.random.default_rng(7),
    )
    assert first.routes == second.routes
    assert first.history == second.history
