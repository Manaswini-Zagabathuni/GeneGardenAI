from pathlib import Path

from genegarden_api.evaluation import evaluate_benchmark, load_benchmark
from genegarden_api.graph.discovery import BiomedicalDiscoveryEngine

BENCHMARK = (
    Path(__file__).parents[1] / "resources" / "benchmarks" / "oncology_open_targets_26_09.json"
)


def test_frozen_benchmark_is_reproducible() -> None:
    report = evaluate_benchmark(load_benchmark(BENCHMARK), k=5)
    metrics = {item.method: item for item in report.methods}

    assert report.case_count == 3
    assert metrics["transparent_baseline_v1"].precision_at_k == 0.133333
    assert metrics["transparent_baseline_v1"].recall_at_k == 0.666667
    assert metrics["transparent_baseline_v1"].mean_reciprocal_rank == 0.233333
    assert metrics["shortest_path"].mean_reciprocal_rank == 0.233333
    assert metrics["unweighted_path_count"].mean_reciprocal_rank == 0.205556
    assert any("leakage" in limitation for limitation in report.limitations)


def test_benchmark_compares_methods_over_the_full_bounded_candidate_set(monkeypatch) -> None:
    observed_result_counts: list[int] = []
    original_search = BiomedicalDiscoveryEngine.search

    def recording_search(self, snapshot, options):
        observed_result_counts.append(options.result_count)
        return original_search(self, snapshot, options)

    monkeypatch.setattr(BiomedicalDiscoveryEngine, "search", recording_search)

    evaluate_benchmark(load_benchmark(BENCHMARK), k=5)

    assert observed_result_counts == [5000, 5000, 5000]
