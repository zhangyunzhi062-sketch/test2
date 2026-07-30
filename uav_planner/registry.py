from __future__ import annotations

from .solvers import ACOSolver, GASolver, HPSOSolver, SASolver, Solver


def create_solver(algorithm: str) -> Solver:
    solvers: dict[str, type[Solver]] = {
        "ACO": ACOSolver,
        "GA": GASolver,
        "HPSO": HPSOSolver,
        "SA": SASolver,
    }
    normalized = algorithm.strip().upper()
    if normalized not in solvers:
        raise ValueError("算法只能是 ACO、GA、HPSO 或 SA。")
    return solvers[normalized]()
