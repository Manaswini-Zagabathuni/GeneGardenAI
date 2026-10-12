import argparse
from pathlib import Path

from genegarden_api.evaluation import evaluate_benchmark, load_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen GeneGarden path benchmark.")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    report = evaluate_benchmark(load_benchmark(arguments.benchmark), k=arguments.k)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
