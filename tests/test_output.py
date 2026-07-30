from __future__ import annotations

import json

import numpy as np

from uav_planner.output import save_outputs
from uav_planner.registry import create_solver


def test_all_output_files_are_created(tmp_path, tsp_problem):
    result = create_solver("ACO").solve(
        tsp_problem,
        {
            "seed": 42,
            "ant_count": 3,
            "iterations": 2,
            "alpha": 1,
            "beta": 3,
            "rho": 0.1,
            "q": 1,
        },
        np.random.default_rng(42),
    )
    save_outputs(tmp_path, tsp_problem, result)
    expected = {"solution.json", "routes.csv", "route.png", "convergence.png"}
    assert expected == {path.name for path in tmp_path.iterdir()}

    payload = json.loads((tmp_path / "solution.json").read_text(encoding="utf-8"))
    assert "input_path" not in payload
    assert payload["vehicle_count"] == 1
