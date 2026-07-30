from __future__ import annotations

from uav_planner.routing import evaluate_cdvrp, evaluate_tsp


def test_tsp_visits_every_customer_once(tsp_problem):
    evaluation = evaluate_tsp([1, 2, 3, 4, 5], tsp_problem)
    assert evaluation.feasible
    assert evaluation.routes == ((0, 1, 2, 3, 4, 5, 0),)


def test_cdvrp_split_respects_all_constraints(cdvrp_problem):
    evaluation = evaluate_cdvrp([1, 2, 3, 4, 5], cdvrp_problem)
    assert evaluation.feasible
    assert len(evaluation.routes) <= cdvrp_problem.max_vehicles
    assert all(load <= cdvrp_problem.capacity for load in evaluation.route_loads)
    assert all(
        distance <= cdvrp_problem.max_route_distance
        for distance in evaluation.route_distances
    )
    visited = [customer for route in evaluation.routes for customer in route[1:-1]]
    assert sorted(visited) == [1, 2, 3, 4, 5]


def test_invalid_permutation_is_rejected(cdvrp_problem):
    evaluation = evaluate_cdvrp([1, 1, 2, 3, 4], cdvrp_problem)
    assert not evaluation.feasible
