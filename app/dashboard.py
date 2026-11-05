from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lakehousebench.analysis import load_observations, summarize


st.set_page_config(page_title="LakehouseBench", layout="wide")
st.title("LakehouseBench")
st.caption(
    "Modern Spark SQL benchmark runner, with the original course results kept "
    "separate as historical context."
)

view = st.radio(
    "View",
    ["Modern Spark runs", "Historical course results"],
    horizontal=True,
)

if view == "Modern Spark runs":
    result_path = PROJECT_ROOT / "results" / "spark-results.jsonl"
    if not result_path.is_file():
        st.info(
            "No Spark runs recorded yet. Start Docker, then run "
            "`docker compose --profile spark run --build --rm spark-benchmark`."
        )
        st.code(
            "docker compose --profile spark run --build --rm spark-benchmark",
            language="powershell",
        )
        st.stop()

    runs = pd.read_json(result_path, lines=True)
    benchmark_ids = sorted(runs["benchmark_id"].dropna().unique())
    if not benchmark_ids:
        st.error("Spark results are missing benchmark IDs. Rerun the benchmark.")
        st.stop()
    selected_benchmark = st.selectbox("Benchmark run", benchmark_ids)
    runs = runs[runs["benchmark_id"] == selected_benchmark]
    st.caption(
        "Each run includes Spark/runtime metadata, the SQL fingerprint, the "
        "cache policy, and a result checksum."
    )
    st.dataframe(
        runs.sort_values(["workload", "run"], ascending=[True, False]),
        hide_index=True,
        width="stretch",
    )
    run_summary = (
        runs.groupby("workload")["elapsed_seconds"]
        .agg(median_seconds="median", p95_seconds=lambda values: values.quantile(0.95))
        .reset_index()
    )
    st.bar_chart(run_summary, x="workload", y="median_seconds")
    st.dataframe(run_summary, hide_index=True, width="stretch")
    st.warning(
        "These local Spark results are not directly comparable with the "
        "historical Hive/Pig/Impala timings: query equivalence, hardware, "
        "versions, and measurement conditions differ. `uncached` disables "
        "Spark's in-memory cache; it does not flush operating-system or "
        "filesystem caches."
    )
else:
    data_path = PROJECT_ROOT / "data" / "observations.csv"
    observations = load_observations(data_path)
    workloads = ["All workloads", *sorted(observations["workload"].unique())]
    selected_workload = st.selectbox("Workload", workloads)

    filtered = observations
    if selected_workload != "All workloads":
        filtered = observations[observations["workload"] == selected_workload]

    summary = summarize(filtered)
    cards = st.columns(3)
    cards[0].metric("Observations", f"{len(filtered)}")
    cards[1].metric("Engines", f"{filtered['engine'].nunique()}")
    cards[2].metric("Workloads", f"{filtered['workload'].nunique()}")

    st.subheader("Recorded median elapsed time (seconds)")
    chart_data = summary.pivot(index="engine", columns="workload", values="median_s")
    st.bar_chart(chart_data)
    st.dataframe(
        summary[
            [
                "workload",
                "engine",
                "runs",
                "median_s",
                "mean_s",
                "p95_s",
                "min_s",
                "max_s",
                "rank",
                "first_run_vs_steady",
            ]
        ],
        hide_index=True,
        width="stretch",
    )

    st.warning(
        "Unit caveat: Hive's simple-query workbook labels its measurements as "
        "milliseconds; the other engines' simple-query measurements use seconds "
        "or omit units. Verify that label before interpreting this workload's "
        "ranking."
    )
    with st.expander("Historical measurement limitations"):
        st.markdown(
            "- Pig and Impala units are partly assumed, not consistently stated.\n"
            "- Ten repeats support descriptive summaries, not significance claims.\n"
            "- The source does not establish matched hardware, equivalent queries, "
            "cache state, or warm-up conditions.\n"
            "- These runs are preserved as archival evidence, not used as a "
            "modern engine bake-off."
        )
