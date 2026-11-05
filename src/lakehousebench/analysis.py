from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "engine",
    "workload",
    "run",
    "elapsed_value",
    "source_unit",
    "elapsed_seconds",
    "unit_basis",
    "source_workbook",
}


class DatasetError(ValueError):
    """Raised when observations cannot be safely analyzed."""


def load_observations(path: str | Path) -> pd.DataFrame:
    observations = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(observations.columns)
    if missing:
        raise DatasetError(f"Missing required columns: {', '.join(sorted(missing))}")
    if observations.empty:
        raise DatasetError("The observations dataset is empty.")
    if observations[list(REQUIRED_COLUMNS)].isna().any().any():
        raise DatasetError("Required observation fields must not be blank.")
    if observations.duplicated(["engine", "workload", "run"]).any():
        raise DatasetError("Each engine/workload/run combination must be unique.")

    for column in ("run", "elapsed_value", "elapsed_seconds"):
        observations[column] = pd.to_numeric(observations[column], errors="coerce")
        if observations[column].isna().any():
            raise DatasetError(f"{column} must contain numeric values.")
    if (observations["run"] < 1).any():
        raise DatasetError("Run numbers must be positive.")
    if (observations["elapsed_value"] <= 0).any() or (
        observations["elapsed_seconds"] <= 0
    ).any():
        raise DatasetError("Elapsed times must be positive.")

    return observations


def summarize(observations: pd.DataFrame) -> pd.DataFrame:
    ordered = observations.sort_values(["engine", "workload", "run"])
    summary = (
        ordered.groupby(["workload", "engine"], as_index=False)
        .agg(
            runs=("elapsed_seconds", "size"),
            median_s=("elapsed_seconds", "median"),
            mean_s=("elapsed_seconds", "mean"),
            stddev_s=("elapsed_seconds", "std"),
            p95_s=("elapsed_seconds", lambda values: values.quantile(0.95)),
            min_s=("elapsed_seconds", "min"),
            max_s=("elapsed_seconds", "max"),
            first_run_s=("elapsed_seconds", "first"),
            steady_median_s=("elapsed_seconds", lambda values: values.iloc[1:].median()),
        )
    )
    summary["rank"] = (
        summary.groupby("workload")["median_s"]
        .rank(method="min")
        .astype(int)
    )
    summary["slowest_to_engine_speedup"] = (
        summary.groupby("workload")["median_s"].transform("max")
        / summary["median_s"]
    )
    summary["first_run_vs_steady"] = summary["first_run_s"] / summary[
        "steady_median_s"
    ]
    return summary.sort_values(["workload", "rank", "engine"]).reset_index(drop=True)


def render_report(observations: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = [
        "# Query benchmark summary",
        "",
        f"- Observations: {len(observations)}",
        f"- Engines: {', '.join(sorted(observations['engine'].unique()))}",
        f"- Workloads: {', '.join(sorted(observations['workload'].unique()))}",
        "- Primary metric: median elapsed time in seconds, ranked within workload.",
        "",
        "## Results",
        "",
        "| Workload | Engine | Runs | Median (s) | Mean (s) | P95 (s) | "
        "Min (s) | Max (s) | Rank | First / steady median |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.workload} | {row.engine} | {row.runs} | "
            f"{row.median_s:.6g} | {row.mean_s:.6g} | {row.p95_s:.6g} | "
            f"{row.min_s:.6g} | {row.max_s:.6g} | {row.rank} | "
            f"{row.first_run_vs_steady:.3f}x |"
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Times are converted to seconds using the per-row `unit_basis`; "
            "unlabelled units are assumptions, not confirmed source facts.",
            "- Hive's simple-query source header says milliseconds. Its literal "
            "conversion dominates that workload's ranking and needs verification.",
            "- Ten repeats are descriptive evidence only. The source does not "
            "establish equivalent queries, hardware, cache state, or warm-up.",
            "- The first-run ratio is shown to expose possible warm-up effects; "
            "runs are not silently discarded.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze(data_path: str | Path, output_dir: str | Path) -> tuple[Path, Path]:
    observations = load_observations(data_path)
    summary = summarize(observations)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    csv_path = destination / "summary.csv"
    report_path = destination / "summary.md"
    summary.to_csv(csv_path, index=False)
    report_path.write_text(render_report(observations, summary), encoding="utf-8")
    return csv_path, report_path
