from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from ..models import PlanningProblem, PlanningResult


class PlanningInfeasibleError(RuntimeError):
    """在给定限制和搜索预算内没有找到可行路线。"""


class Solver(ABC):
    """所有算法都遵循的公共求解接口。"""

    algorithm: str

    @abstractmethod
    def solve(
        self,
        problem: PlanningProblem,
        config: dict[str, Any],
        rng: np.random.Generator,
    ) -> PlanningResult:
        raise NotImplementedError
