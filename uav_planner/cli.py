from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .io_excel import load_planning_workbook
from .output import save_outputs
from .registry import create_solver
from .solvers import PlanningInfeasibleError
from .validation import DataValidationError


DEFAULT_TEMPLATE = "无人机路径规划数据模板.xlsx"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uav-planner",
        description="从 Excel/WPS 表格读取航点和限制，规划单机 TSP 或无人机群 CDVRP 路线。",
    )
    parser.add_argument("--input", type=Path, help="输入 .xlsx 文件")
    parser.add_argument(
        "--problem",
        choices=["tsp", "cdvrp"],
        help="问题类型；不填写时使用 Excel 设置",
    )
    parser.add_argument(
        "--algorithm",
        choices=["aco", "ga", "hpso", "sa"],
        help="算法；不填写时使用 Excel 设置",
    )
    parser.add_argument(
        "--distance-mode",
        choices=["euclidean", "haversine"],
        help="距离模式；不填写时使用 Excel 设置",
    )
    parser.add_argument("--seed", type=int, help="随机种子；不填写时使用 Excel 设置")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="结果目录，默认 results",
    )
    return parser


def _choose_excel_file() -> Path:
    default_path = Path.cwd() / DEFAULT_TEMPLATE
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(
            title="请选择无人机路径规划 Excel 文件",
            initialdir=str(Path.cwd()),
            initialfile=DEFAULT_TEMPLATE if default_path.exists() else "",
            filetypes=[("Excel 工作簿", "*.xlsx")],
        )
        root.destroy()
        if selected:
            return Path(selected)
    except Exception:
        pass

    print("\n请输入 Excel 文件路径。")
    if default_path.exists():
        print(f"直接按回车将使用当前文件夹中的“{DEFAULT_TEMPLATE}”。")
    entered = input("Excel 文件：").strip().strip('"')
    return Path(entered) if entered else default_path


def _overrides_from_args(args: argparse.Namespace) -> dict[str, object]:
    return {
        "problem_type": args.problem.upper() if args.problem else None,
        "algorithm": args.algorithm.upper() if args.algorithm else None,
        "distance_mode": args.distance_mode,
        "seed": args.seed,
    }


def _show_summary(problem, settings) -> None:
    print("\n========== 已读取的任务 ==========")
    print(f"问题类型：{problem.problem_type}")
    print(f"算法：{settings.algorithm}")
    print(f"启用航点：{len(problem.waypoints)} 个（含基地）")
    print(
        "距离模式："
        + ("经纬度球面距离" if problem.distance_mode == "haversine" else "欧氏距离")
    )
    print(f"距离单位：{problem.distance_unit}")
    if problem.problem_type == "CDVRP":
        vehicle_limit = (
            "不限"
            if problem.max_vehicles is None
            else f"{problem.max_vehicles} 架"
        )
        print(f"单机容量：{problem.capacity:g}")
        print(f"单机最大航程：{problem.max_route_distance:g} {problem.distance_unit}")
        print(f"最大无人机数量：{vehicle_limit}")
    print(f"随机种子：{settings.seed}")
    print("==================================")


def _load_interactively(args: argparse.Namespace):
    path = _choose_excel_file()
    while True:
        problem, settings = load_planning_workbook(
            path,
            _overrides_from_args(args),
        )
        _show_summary(problem, settings)
        answer = input(
            "\n输入 Y 开始规划；输入 M 返回 Excel 修改并重新读取；输入 Q 退出："
        ).strip().lower()
        if answer in {"y", "yes", "是", ""}:
            return problem, settings
        if answer in {"q", "quit", "退出"}:
            raise KeyboardInterrupt
        print(
            "\n请修改并保存 Excel，然后关闭 Excel/WPS。"
            "完成后按回车，程序会重新读取同一个文件。"
        )
        input()


def run(args: argparse.Namespace) -> int:
    interactive = args.input is None
    if interactive:
        problem, settings = _load_interactively(args)
    else:
        problem, settings = load_planning_workbook(
            args.input,
            _overrides_from_args(args),
        )
        _show_summary(problem, settings)

    config = settings.selected_algorithm_config()
    rng = np.random.default_rng(settings.seed)
    solver = create_solver(settings.algorithm)
    print(f"\n正在使用 {settings.algorithm} 规划，请稍候……")
    result = solver.solve(problem, config, rng)
    output_directory = save_outputs(args.output, problem, result).resolve()

    print("\n========== 规划完成 ==========")
    print(f"总距离：{result.total_distance:.3f} {result.distance_unit}")
    print(f"使用无人机：{len(result.routes)} 架")
    for index, (route, distance, load) in enumerate(
        zip(result.routes, result.route_distances, result.route_loads),
        start=1,
    ):
        print(
            f"无人机 {index}：{' -> '.join(map(str, route))}"
            f"；距离 {distance:.3f} {result.distance_unit}；载荷 {load:.3f}"
        )
    print(f"结果已保存到：{output_directory}")
    print("其中 route.png 是路线图，routes.csv 可用 Excel/WPS 打开。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\n已取消，本次没有执行规划。")
        return 130
    except (DataValidationError, PlanningInfeasibleError, ValueError) as exc:
        print(f"\n无法规划：{exc}", file=sys.stderr)
        return 2
    except PermissionError:
        print(
            "\n无法写入结果。请关闭正在占用结果文件的 Excel/WPS 后重试。",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
