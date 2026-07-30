from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .models import PlanningProblem, PlanningResult


def _configure_chinese_font() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def _plot_routes(
    problem: PlanningProblem,
    result: PlanningResult,
    output_path: Path,
) -> None:
    _configure_chinese_font()
    point_by_id = {point.waypoint_id: point for point in problem.waypoints}
    figure, axis = plt.subplots(figsize=(10, 7), dpi=140)
    colors = plt.get_cmap("tab20")

    for route_number, route in enumerate(result.routes, start=1):
        route_points = [point_by_id[waypoint_id] for waypoint_id in route]
        if problem.distance_mode == "haversine":
            horizontal = [point.y for point in route_points]
            vertical = [point.x for point in route_points]
        else:
            horizontal = [point.x for point in route_points]
            vertical = [point.y for point in route_points]
        axis.plot(
            horizontal,
            vertical,
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=colors((route_number - 1) % 20),
            label=f"无人机 {route_number}",
        )

    for point in problem.waypoints:
        horizontal = point.y if problem.distance_mode == "haversine" else point.x
        vertical = point.x if problem.distance_mode == "haversine" else point.y
        marker_size = 90 if point.waypoint_id == 0 else 35
        marker_color = "#D62728" if point.waypoint_id == 0 else "#16324F"
        axis.scatter(horizontal, vertical, s=marker_size, c=marker_color, zorder=5)
        axis.annotate(
            f"{point.waypoint_id}:{point.name}",
            (horizontal, vertical),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    axis.set_title(
        f"{result.problem_type} / {result.algorithm} 路线图\n"
        f"总距离：{result.total_distance:.3f} {result.distance_unit}"
    )
    axis.set_xlabel("经度" if problem.distance_mode == "haversine" else "X")
    axis.set_ylabel("纬度" if problem.distance_mode == "haversine" else "Y")
    axis.grid(True, linestyle="--", alpha=0.35)
    axis.set_aspect("equal", adjustable="datalim")
    if result.routes:
        axis.legend(loc="best", fontsize=8)
    figure.tight_layout()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def _plot_convergence(result: PlanningResult, output_path: Path) -> None:
    _configure_chinese_font()
    figure, axis = plt.subplots(figsize=(9, 5), dpi=140)
    steps = range(1, len(result.history) + 1)
    axis.plot(steps, result.history, color="#1F6E78", linewidth=1.8)
    axis.set_title(f"{result.algorithm} 收敛曲线")
    axis.set_xlabel("迭代/温度步")
    axis.set_ylabel(f"全局最优总距离（{result.distance_unit}）")
    axis.grid(True, linestyle="--", alpha=0.35)
    figure.tight_layout()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def save_outputs(
    output_directory: str | Path,
    problem: PlanningProblem,
    result: PlanningResult,
) -> Path:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    summary = result.as_dict()
    summary["waypoint_count"] = len(problem.waypoints)
    summary["vehicle_count"] = len(result.routes)
    with (directory / "solution.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)

    with (directory / "routes.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["无人机编号", "访问顺序", "路线距离", "载荷", "距离单位"]
        )
        for route_number, (route, distance, load) in enumerate(
            zip(result.routes, result.route_distances, result.route_loads),
            start=1,
        ):
            writer.writerow(
                [
                    route_number,
                    " -> ".join(map(str, route)),
                    f"{distance:.6f}",
                    f"{load:.6f}",
                    result.distance_unit,
                ]
            )

    _plot_routes(problem, result, directory / "route.png")
    _plot_convergence(result, directory / "convergence.png")
    return directory
