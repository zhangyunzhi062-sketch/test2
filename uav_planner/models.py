from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Waypoint:
    """用户输入的一个航点。"""

    waypoint_id: int
    name: str
    x: float
    y: float
    demand: float = 0.0
    note: str = ""


@dataclass(frozen=True)
class PlanningProblem:
    """完成校验并计算好距离矩阵的规划问题。"""

    problem_type: str
    waypoints: tuple[Waypoint, ...]
    distance_matrix: np.ndarray
    distance_mode: str = "euclidean"
    distance_unit: str = "km"
    capacity: float | None = None
    max_route_distance: float | None = None
    max_vehicles: int | None = None

    @property
    def customer_indices(self) -> tuple[int, ...]:
        return tuple(range(1, len(self.waypoints)))

    @property
    def waypoint_ids(self) -> tuple[int, ...]:
        return tuple(point.waypoint_id for point in self.waypoints)

    def waypoint_id_for_index(self, index: int) -> int:
        return self.waypoints[index].waypoint_id


@dataclass(frozen=True)
class RouteEvaluation:
    """一个任务点排列被解码后的约束与距离结果。"""

    feasible: bool
    total_distance: float
    routes: tuple[tuple[int, ...], ...]
    route_distances: tuple[float, ...]
    route_loads: tuple[float, ...]
    reason: str = ""


@dataclass
class PlanningResult:
    """求解器对外返回的统一结果。"""

    problem_type: str
    algorithm: str
    seed: int
    total_distance: float
    routes: list[list[int]]
    route_distances: list[float]
    route_loads: list[float]
    history: list[float]
    elapsed_seconds: float
    distance_mode: str
    distance_unit: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "seed": self.seed,
            "distance_mode": self.distance_mode,
            "distance_unit": self.distance_unit,
            "total_distance": self.total_distance,
            "routes": self.routes,
            "route_distances": self.route_distances,
            "route_loads": self.route_loads,
            "history": self.history,
            "elapsed_seconds": self.elapsed_seconds,
            "metadata": self.metadata,
        }


@dataclass
class WorkbookSettings:
    """从 Excel 中读取的任务设置和算法参数。"""

    problem_type: str = "CDVRP"
    algorithm: str = "ACO"
    distance_mode: str = "euclidean"
    distance_unit: str = "km"
    capacity: float | None = 20.0
    max_route_distance: float | None = 500.0
    max_vehicles: int | None = None
    seed: int = 42
    algorithm_parameters: dict[str, dict[str, float]] = field(default_factory=dict)

    def selected_algorithm_config(self) -> dict[str, float | int]:
        config: dict[str, float | int] = {
            "seed": self.seed,
        }
        config.update(self.algorithm_parameters.get(self.algorithm.upper(), {}))
        return config

