import pandas as pd

from scripts.generate_readme_assets import (
    render_historical_chart,
    render_spark_chart,
)


def test_spark_chart_contains_median_and_p95(tmp_path) -> None:
    records = [
        {
            "benchmark_id": "test-run",
            "workload": "simple",
            "run": 1,
            "elapsed_seconds": 0.2,
        },
        {
            "benchmark_id": "test-run",
            "workload": "simple",
            "run": 2,
            "elapsed_seconds": 0.4,
        },
    ]
    output = tmp_path / "spark.svg"

    render_spark_chart(records, output)

    chart = output.read_text(encoding="utf-8")
    assert "Median elapsed time" in chart
    assert "0.300s median" in chart
    assert "p95" in chart


def test_historical_chart_explicitly_uses_log_scale(tmp_path) -> None:
    summary = pd.DataFrame(
        [
            {"workload": workload, "engine": engine, "median_s": seconds}
            for workload, seconds in (("moderate", 10.0), ("complex", 20.0))
            for engine in ("Impala", "Hive", "Pig")
        ]
    )
    output = tmp_path / "historical.svg"

    render_historical_chart(summary, output)

    chart = output.read_text(encoding="utf-8")
    assert "log scale" in chart
    assert "Impala: 10s" in chart
    assert "Pig: 20s" in chart
