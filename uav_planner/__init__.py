"""无人机单机 TSP 与集群 CDVRP 路径规划工具。"""

from .models import ObstacleBox, PlanningProblem, PlanningResult, Waypoint
from .registry import create_solver

__all__ = [
    "ObstacleBox",
    "PlanningProblem",
    "PlanningResult",
    "Waypoint",
    "create_solver",
]

__version__ = "0.2.0"
