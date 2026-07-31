from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

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

    for obstacle in problem.obstacles:
        horizontal = (
            obstacle.y_min if problem.distance_mode == "haversine" else obstacle.x_min
        )
        vertical = (
            obstacle.x_min if problem.distance_mode == "haversine" else obstacle.y_min
        )
        width = (
            obstacle.y_max - obstacle.y_min
            if problem.distance_mode == "haversine"
            else obstacle.x_max - obstacle.x_min
        )
        height = (
            obstacle.x_max - obstacle.x_min
            if problem.distance_mode == "haversine"
            else obstacle.y_max - obstacle.y_min
        )
        axis.add_patch(
            Rectangle(
                (horizontal, vertical),
                width,
                height,
                facecolor="#7F5539",
                edgecolor="#5C3D2E",
                alpha=0.35,
                hatch="//",
            )
        )

    for route_number, route_path in enumerate(result.route_paths, start=1):
        if problem.distance_mode == "haversine":
            horizontal = [point[1] for point in route_path]
            vertical = [point[0] for point in route_path]
        else:
            horizontal = [point[0] for point in route_path]
            vertical = [point[1] for point in route_path]
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


def _box_faces(obstacle) -> list[list[tuple[float, float, float]]]:
    x0, x1 = obstacle.x_min, obstacle.x_max
    y0, y1 = obstacle.y_min, obstacle.y_max
    z0, z1 = obstacle.z_min, obstacle.z_max
    vertices = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    return [
        [vertices[index] for index in face]
        for face in (
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        )
    ]


def _plot_routes_3d(
    problem: PlanningProblem,
    result: PlanningResult,
    output_path: Path,
) -> None:
    _configure_chinese_font()
    figure = plt.figure(figsize=(11, 8), dpi=140)
    axis = figure.add_subplot(111, projection="3d")
    colors = plt.get_cmap("tab20")

    for obstacle in problem.obstacles:
        faces = _box_faces(obstacle)
        if problem.distance_mode == "haversine":
            faces = [
                [(y, x, z) for x, y, z in face]
                for face in faces
            ]
        collection = Poly3DCollection(
            faces,
            facecolors="#8B5E3C",
            edgecolors="#5C3D2E",
            alpha=0.3,
            linewidths=0.8,
        )
        axis.add_collection3d(collection)

    for route_number, route_path in enumerate(result.route_paths, start=1):
        if problem.distance_mode == "haversine":
            horizontal = [point[1] for point in route_path]
            vertical = [point[0] for point in route_path]
        else:
            horizontal = [point[0] for point in route_path]
            vertical = [point[1] for point in route_path]
        altitude = [point[2] for point in route_path]
        axis.plot(
            horizontal,
            vertical,
            altitude,
            marker="o",
            markersize=3,
            linewidth=1.8,
            color=colors((route_number - 1) % 20),
            label=f"无人机 {route_number}",
        )

    for point in problem.waypoints:
        horizontal = point.y if problem.distance_mode == "haversine" else point.x
        vertical = point.x if problem.distance_mode == "haversine" else point.y
        marker_color = "#D62728" if point.waypoint_id == 0 else "#16324F"
        axis.scatter(horizontal, vertical, point.z, s=45, c=marker_color)
        axis.text(horizontal, vertical, point.z, str(point.waypoint_id), fontsize=8)

    axis.set_title(
        f"{result.problem_type} / {result.algorithm} 三维避障路线\n"
        f"总距离：{result.total_distance:.3f} {result.distance_unit}"
    )
    axis.set_xlabel("经度" if problem.distance_mode == "haversine" else "X")
    axis.set_ylabel("纬度" if problem.distance_mode == "haversine" else "Y")
    axis.set_zlabel("高度（米）" if problem.distance_mode == "haversine" else "Z/高度")
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
    summary["dimension"] = problem.dimension
    summary["obstacle_count"] = len(problem.obstacles)
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

    with (directory / "flight_path.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        writer = csv.writer(stream)
        first_label = "纬度" if problem.distance_mode == "haversine" else "X"
        second_label = "经度" if problem.distance_mode == "haversine" else "Y"
        third_label = "海拔（米）" if problem.distance_mode == "haversine" else "Z/高度"
        writer.writerow(
            ["无人机编号", "路径点序号", first_label, second_label, third_label]
        )
        for route_number, route_path in enumerate(result.route_paths, start=1):
            for point_number, point in enumerate(route_path, start=1):
                writer.writerow(
                    [
                        route_number,
                        point_number,
                        f"{point[0]:.9f}",
                        f"{point[1]:.9f}",
                        f"{point[2]:.6f}",
                    ]
                )

    _plot_routes(problem, result, directory / "route.png")
    if problem.dimension == "3D":
        _plot_routes_3d(problem, result, directory / "route_3d.png")
    _plot_convergence(result, directory / "convergence.png")
    return directory
