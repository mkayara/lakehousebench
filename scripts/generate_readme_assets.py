import argparse
import html
import json
import math
from pathlib import Path

import pandas as pd

from lakehousebench.analysis import load_observations, summarize


ENGINE_COLORS = {"Impala": "#1f77b4", "Hive": "#e67e22", "Pig": "#7f8c8d"}
SPARK_COLOR = "#e25a1c"


def _text(x: float, y: float, value: str, *, size: int = 13, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'text-anchor="{anchor}">{html.escape(value)}</text>'
    )


def render_spark_chart(records: list[dict], output: Path) -> None:
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("No Spark benchmark records were provided.")
    if "benchmark_id" not in frame or frame["benchmark_id"].nunique() != 1:
        raise ValueError("Spark chart input must contain exactly one benchmark run.")

    required = {"workload", "run", "elapsed_seconds"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Spark records are missing fields: {', '.join(sorted(missing))}")

    summaries = (
        frame.groupby("workload")["elapsed_seconds"]
        .agg(median="median", p95=lambda values: values.quantile(0.95), runs="size")
        .sort_values("median")
    )
    width, height = 900, 275
    left, right = 190, 650
    top, row_gap = 80, 52
    maximum = max(float(summaries["p95"].max()), 0.001)
    tick_step = 10 ** math.floor(math.log10(maximum / 4))
    tick_step *= max(1, math.ceil(maximum / 4 / tick_step))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        "<title>Spark SQL benchmark median and p95 latency</title>",
        "<desc>Median latency bars with p95 markers for each workload.</desc>",
        '<style>text{font-family:Arial,sans-serif;fill:#253247} .grid{stroke:#dbe2ea}'
        ".p95{stroke:#18212f;stroke-width:3}</style>",
        _text(20, 29, "Spark SQL on a local Docker runtime", size=19),
        _text(20, 52, "Median elapsed time; dark marker = p95. Lower is faster.", size=13),
    ]

    chart_width = right - left
    tick = 0.0
    while tick <= maximum + tick_step * 0.01:
        x = left + min(tick / maximum, 1) * chart_width
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="66" x2="{x:.1f}" y2="224"/>')
        parts.append(_text(x, 245, f"{tick:g}", size=12, anchor="middle"))
        tick += tick_step

    for index, (workload, row) in enumerate(summaries.iterrows()):
        y = top + index * row_gap
        median_x = left + float(row["median"]) / maximum * chart_width
        p95_x = left + float(row["p95"]) / maximum * chart_width
        parts.extend(
            [
                _text(left - 14, y + 5, str(workload), anchor="end"),
                f'<rect x="{left}" y="{y - 10}" width="{median_x - left:.2f}" '
                f'height="21" rx="3" fill="{SPARK_COLOR}"/>',
                f'<line class="p95" x1="{p95_x:.1f}" y1="{y - 14}" '
                f'x2="{p95_x:.1f}" y2="{y + 15}"/>',
                _text(right + 10, y + 5, f'{row["median"]:.3f}s median  |  '
                      f'{row["p95"]:.3f}s p95  |  n={int(row["runs"])}', size=12),
            ]
        )
    parts.extend([_text((left + right) / 2, 268, "Elapsed seconds", size=12, anchor="middle"),
                  "</svg>"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")


def render_historical_chart(summary: pd.DataFrame, output: Path) -> None:
    selected = summary[summary["workload"].isin(["moderate", "complex"])].copy()
    if selected.empty:
        raise ValueError("Historical chart requires moderate and complex workloads.")

    width, height = 1000, 370
    left, right = 190, 760
    minimum, maximum = 0.1, 100.0

    def x_position(value: float) -> float:
        ratio = (math.log10(value) - math.log10(minimum)) / (
            math.log10(maximum) - math.log10(minimum)
        )
        return left + ratio * (right - left)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        "<title>Historical Hive, Impala and Pig query timings</title>",
        "<desc>Moderate and complex workload median timings on a logarithmic seconds axis.</desc>",
        '<style>text{font-family:Arial,sans-serif;fill:#253247} .grid{stroke:#dbe2ea}</style>',
        _text(20, 29, "Historical course results: moderate and complex", size=19),
        _text(20, 52, "Median elapsed time in seconds (log scale); unlabelled units assumed to be seconds.", size=12),
    ]
    for engine, color in ENGINE_COLORS.items():
        parts.append(f'<rect x="{left}" y="67" width="12" height="12" fill="{color}"/>')
        parts.append(_text(left + 18, 78, engine, size=12))
        left += 95
    left = 190
    ticks = [0.1, 1, 10, 100]
    chart_top, chart_bottom = 104, 310
    for tick in ticks:
        x = x_position(tick)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{chart_top}" '
                     f'x2="{x:.1f}" y2="{chart_bottom}"/>')
        parts.append(_text(x, 333, f"{tick:g}", size=12, anchor="middle"))

    engines = ["Impala", "Hive", "Pig"]
    workloads = ["moderate", "complex"]
    y = chart_top + 9
    for workload in workloads:
        parts.append(_text(left - 12, y + 15, workload.title(), size=14, anchor="end"))
        y += 14
        for engine in engines:
            row = selected[
                (selected["workload"] == workload) & (selected["engine"] == engine)
            ]
            if row.empty:
                continue
            value = float(row.iloc[0]["median_s"])
            color = ENGINE_COLORS[engine]
            x = x_position(value)
            parts.append(
                f'<rect x="{x_position(minimum):.1f}" y="{y}" '
                f'width="{x - x_position(minimum):.2f}" height="12" '
                f'rx="2" fill="{color}"/>'
            )
            parts.append(_text(x + 6, y + 11, f"{engine}: {value:g}s", size=11))
            y += 24
        y += 10
    parts.extend([_text((left + right) / 2, 360, "Elapsed seconds (logarithmic scale)",
                        size=12, anchor="middle"), "</svg>"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate README benchmark charts.")
    parser.add_argument("--spark-results", type=Path, default=Path("results/spark-results.jsonl"))
    parser.add_argument("--historical-data", type=Path, default=Path("data/observations.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/results"))
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in args.spark_results.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    observations = load_observations(args.historical_data)
    summary = summarize(observations)
    render_spark_chart(records, args.output_dir / "spark-latency.svg")
    render_historical_chart(summary, args.output_dir / "historical-latency.svg")
    print(f"Wrote README charts to {args.output_dir}")


if __name__ == "__main__":
    main()
