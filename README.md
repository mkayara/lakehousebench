# LakehouseBench

[![CI](https://github.com/<your-username>/lakehousebench/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/lakehousebench/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-4.2.1-E25A1C?logo=apachespark&logoColor=white)
![PySpark](https://img.shields.io/badge/benchmark-Spark%20SQL-E25A1C?logo=apachespark&logoColor=white)
![Docker](https://img.shields.io/badge/deployment-Docker-2496ED?logo=docker&logoColor=white)

A portfolio-focused big-data benchmark lab. Its runnable Apache Spark SQL
profile generates a deterministic dataset, executes three analytical query
shapes, and records timing, runtime metadata, SQL fingerprints, and result
checksums. A Streamlit dashboard presents those measurements alongside a
strictly separate archival analysis of the supplied Hive, Pig, and Impala runs.

Spark SQL is the first runnable modern engine. Historical Hive/Impala
observations provide context, not a purported head-to-head result. Pig is
retained only because it is in the source workbook. HBase is intentionally not
ranked against SQL engines: a future HBase profile should measure point reads,
batch gets, and writes as a separate key-value workload.

## Run a Spark benchmark

Docker Compose builds a pinned Spark 4.2.1 image and submits a local Spark SQL
benchmark. The initial run uses 100,000 generated rows, two warm-ups, and ten
timed repetitions per workload.

```powershell
docker compose --profile spark run --build --rm spark-benchmark
docker compose up --build dashboard
```

Results are appended to `results/spark-results.jsonl`. Open the dashboard at
`http://localhost:8501`, choose **Modern Spark runs**, and inspect the
per-repetition timings and recorded metadata.

Set the workload size, warm-ups, repetitions, and cache policy using environment
variables:

```powershell
$env:BENCHMARK_ROWS = "1000000"
$env:BENCHMARK_WARMUPS = "3"
$env:BENCHMARK_REPETITIONS = "15"
$env:BENCHMARK_CACHE_POLICY = "uncached"
docker compose --profile spark run --build --rm spark-benchmark
```

Use `cached` to persist the generated event table in Spark memory. Cache policy
is explicit in every output record; it is not silently mixed in comparisons.

## Historical course results

The original spreadsheets contain 10 observations per engine/workload for
Hive, Pig, and Impala. Their analysis is available in the dashboard's
**Historical course results** view, and is reproducible with:

```text
python -m pip install -e ".[dev]"
python -m lakehousebench analyze --data data/observations.csv --output reports
```

The importer reads the original workbooks using explicit cell mappings:

```powershell
python scripts/import_workbooks.py --input-dir "C:\path\to\workbooks" --output data/observations.csv
```

Hive's simple-query header says milliseconds, while other engine timings use
seconds or omit the unit. This is flagged and converted literally rather than
quietly "corrected"; the source unit should be verified before trusting that
historical ranking. Modern Spark timings are not directly comparable to the old
results because hardware, engine versions, queries, and measurement conditions
differ.

## Engineering choices

- **A benchmark is a contract, not just a stopwatch.** The Spark profile fixes
  workload SQL, generated input, warm-up count, repetition count, and cache
  policy in code and records them with each run.
- **Check output as well as time.** Every run stores a stable result checksum
  and query fingerprint so changed outputs or changed SQL are observable.
- **Retain raw samples.** Repeated runs are kept rather than reduced to a
  single flattering average; warm-ups are excluded explicitly.
- **Don't compare unlike systems.** SQL aggregation benchmarks and HBase
  key-value access patterns need distinct workloads and separate reporting.
- **Keep provenance.** The course workbooks are parsed with explicit cell
  mappings; the resulting tidy CSV records source, stated units, and assumptions.

## Next benchmark profiles

The harness deliberately starts with a working Spark profile instead of
claiming a distributed multi-engine comparison before the environment is
controlled. An Impala/Hive comparison should use the same Parquet/Iceberg
fixture and equivalent SQL, then record engine version, cluster resources,
storage layout, cache policy, and query plan. HBase should have its own profile
for point lookups, batch reads, and writes, with latency percentiles and
throughput rather than SQL-engine rankings.

## Tests

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

## License

MIT. The license covers this project's code; upstream benchmark observations
remain attributed to the user-provided workbooks.
