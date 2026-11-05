import pandas as pd
import pytest

from lakehousebench.analysis import DatasetError, load_observations, summarize


def sample_observations() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "engine": "A",
                "workload": "simple",
                "run": 1,
                "elapsed_value": 1.0,
                "source_unit": "s",
                "elapsed_seconds": 1.0,
                "unit_basis": "test data",
                "source_workbook": "test.xlsx",
            },
            {
                "engine": "A",
                "workload": "simple",
                "run": 2,
                "elapsed_value": 3.0,
                "source_unit": "s",
                "elapsed_seconds": 3.0,
                "unit_basis": "test data",
                "source_workbook": "test.xlsx",
            },
            {
                "engine": "B",
                "workload": "simple",
                "run": 1,
                "elapsed_value": 4.0,
                "source_unit": "s",
                "elapsed_seconds": 4.0,
                "unit_basis": "test data",
                "source_workbook": "test.xlsx",
            },
            {
                "engine": "B",
                "workload": "simple",
                "run": 2,
                "elapsed_value": 6.0,
                "source_unit": "s",
                "elapsed_seconds": 6.0,
                "unit_basis": "test data",
                "source_workbook": "test.xlsx",
            },
        ]
    )


def test_summary_uses_median_and_ranks_within_workload() -> None:
    summary = summarize(sample_observations()).set_index("engine")

    assert summary.loc["A", "median_s"] == 2.0
    assert summary.loc["A", "rank"] == 1
    assert summary.loc["B", "rank"] == 2
    assert summary.loc["A", "first_run_vs_steady"] == pytest.approx(1 / 3)


def test_load_rejects_duplicate_run_keys(tmp_path) -> None:
    data = sample_observations()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    path = tmp_path / "duplicate.csv"
    data.to_csv(path, index=False)

    with pytest.raises(DatasetError, match="must be unique"):
        load_observations(path)


def test_load_rejects_non_positive_timings(tmp_path) -> None:
    data = sample_observations()
    data.loc[0, "elapsed_seconds"] = 0
    path = tmp_path / "invalid.csv"
    data.to_csv(path, index=False)

    with pytest.raises(DatasetError, match="must be positive"):
        load_observations(path)
