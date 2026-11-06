import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_published_benchmark_has_ten_consistent_samples_per_workload() -> None:
    results_path = PROJECT_ROOT / "results" / "spark-results.jsonl"
    records = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    benchmark_ids = {record["benchmark_id"] for record in records}
    assert benchmark_ids

    for benchmark_id in benchmark_ids:
        benchmark = [
            record for record in records if record["benchmark_id"] == benchmark_id
        ]
        assert len(benchmark) == 30
        assert {record["dataset_rows"] for record in benchmark} == {100_000}
        assert {record["warmups"] for record in benchmark} == {2}
        assert {record["cache_policy"] for record in benchmark} == {"uncached"}
        assert {record["spark_version"] for record in benchmark} == {"4.2.1"}

        for workload in ("simple", "moderate", "complex"):
            samples = [
                record for record in benchmark if record["workload"] == workload
            ]
            assert len(samples) == 10
            assert all(record["elapsed_seconds"] > 0 for record in samples)
            assert len({record["result_sha256"] for record in samples}) == 1
