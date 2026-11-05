import argparse
import hashlib
import json
import os
import platform
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

try:
    from pyspark.sql import DataFrame, Row, SparkSession, functions as F
except ModuleNotFoundError as error:
    if error.name != "pyspark":
        raise
    raise SystemExit(
        "PySpark is provided by the benchmark Docker image. From the project "
        "root, run: docker compose --profile spark run --build --rm spark-benchmark"
    ) from error


QUERIES = {
    "simple": """
        SELECT COUNT(*) AS matching_events
        FROM events
        WHERE event_type = 'purchase'
    """,
    "moderate": """
        SELECT region, event_type, COUNT(*) AS event_count,
               ROUND(SUM(amount), 2) AS revenue
        FROM events
        GROUP BY region, event_type
        ORDER BY region, event_type
    """,
    "complex": """
        SELECT c.segment, e.region, COUNT(*) AS event_count,
               ROUND(SUM(e.amount), 2) AS revenue
        FROM events e
        JOIN customers c ON e.customer_id = c.customer_id
        WHERE e.event_type IN ('purchase', 'return')
        GROUP BY c.segment, e.region
        ORDER BY c.segment, e.region
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic Spark SQL workloads and append JSONL results."
    )
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("results/spark-results.jsonl"))
    parser.add_argument(
        "--cache-policy",
        choices=("uncached", "cached"),
        default="uncached",
        help="Keep the generated Parquet dataset uncached or persist it in Spark memory.",
    )
    args = parser.parse_args()
    if args.rows < 1 or args.warmups < 0 or args.repetitions < 1:
        parser.error("rows and repetitions must be positive; warmups cannot be negative")
    return args


def build_events(spark: SparkSession, rows: int) -> DataFrame:
    events = spark.range(rows).select(
        F.col("id").alias("event_id"),
        F.pmod(F.col("id"), F.lit(max(1, rows // 20))).alias("customer_id"),
        F.pmod(F.col("id") * F.lit(31), F.lit(1_000)).alias("product_id"),
        F.element_at(
            F.array(
                F.lit("north"),
                F.lit("south"),
                F.lit("east"),
                F.lit("west"),
            ),
            (F.pmod(F.col("id"), F.lit(4)) + F.lit(1)).cast("int"),
        ).alias("region"),
        F.element_at(
            F.array(
                F.lit("purchase"),
                F.lit("browse"),
                F.lit("return"),
                F.lit("review"),
            ),
            (F.pmod(F.col("id"), F.lit(4)) + F.lit(1)).cast("int"),
        ).alias("event_type"),
        (
            F.pmod(F.col("id") * F.lit(17), F.lit(100_000)) / F.lit(100)
        ).alias("amount"),
    )
    return events


def canonical_result(rows: list[Row]) -> str:
    records = [row.asDict(recursive=True) for row in rows]
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    args = parse_args()
    spark = (
        SparkSession.builder.appName("lakehousebench-spark")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        with tempfile.TemporaryDirectory(prefix="lakehousebench-") as directory:
            parquet_path = str(Path(directory) / "events")
            build_events(spark, args.rows).write.mode("overwrite").parquet(parquet_path)
            spark.read.parquet(parquet_path).createOrReplaceTempView("events")

            customer_rows = max(1, args.rows // 20)
            customers = spark.range(customer_rows).select(
                F.col("id").alias("customer_id"),
                F.element_at(
                    F.array(
                        F.lit("consumer"),
                        F.lit("business"),
                        F.lit("enterprise"),
                    ),
                    (F.pmod(F.col("id"), F.lit(3)) + F.lit(1)).cast("int"),
                ).alias("segment"),
            )
            customers.createOrReplaceTempView("customers")

            records = []
            timestamp = datetime.now(timezone.utc).isoformat()
            benchmark_id = str(uuid.uuid4())
            for workload, query in QUERIES.items():
                query_hash = hashlib.sha256(
                    " ".join(query.split()).encode("utf-8")
                ).hexdigest()
                if args.cache_policy == "cached":
                    spark.table("events").cache()
                    spark.table("events").count()

                for _ in range(args.warmups):
                    spark.sql(query).collect()

                for run in range(1, args.repetitions + 1):
                    if args.cache_policy == "uncached":
                        spark.catalog.clearCache()
                    started = perf_counter()
                    result = spark.sql(query).collect()
                    elapsed = perf_counter() - started
                    records.append(
                        {
                            "engine": "Spark SQL",
                            "benchmark_id": benchmark_id,
                            "workload": workload,
                            "run": run,
                            "elapsed_seconds": elapsed,
                            "dataset_rows": args.rows,
                            "warmups": args.warmups,
                            "cache_policy": args.cache_policy,
                            "query_sha256": query_hash,
                            "result_rows": len(result),
                            "result_sha256": canonical_result(result),
                            "spark_version": spark.version,
                            "spark_master": spark.sparkContext.master,
                            "shuffle_partitions": spark.conf.get(
                                "spark.sql.shuffle.partitions"
                            ),
                            "python_version": platform.python_version(),
                            "runtime_platform": platform.platform(),
                            "runtime_cpu_count": os.cpu_count(),
                            "recorded_at_utc": timestamp,
                        }
                    )

                spark.catalog.clearCache()

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as output_file:
            for record in records:
                output_file.write(json.dumps(record, sort_keys=True) + "\n")
        print(
            f"Recorded {len(records)} timed Spark runs "
            f"({len(QUERIES)} workloads x {args.repetitions} repetitions) "
            f"to {args.output}"
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
