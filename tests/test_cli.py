from uav_planner.cli import build_parser


def test_direct_cli_arguments_are_parsed():
    args = build_parser().parse_args(
        [
            "--input",
            "data.xlsx",
            "--problem",
            "tsp",
            "--algorithm",
            "sa",
            "--distance-mode",
            "euclidean",
            "--dimension",
            "3d",
            "--seed",
            "9",
            "--output",
            "out",
        ]
    )
    assert args.problem == "tsp"
    assert args.algorithm == "sa"
    assert args.seed == 9
    assert args.dimension == "3d"
