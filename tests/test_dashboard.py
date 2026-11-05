from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_shows_command_when_spark_results_do_not_exist(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("LAKEHOUSEBENCH_RESULTS", str(tmp_path / "not-yet-run.jsonl"))

    app = AppTest.from_file(str(PROJECT_ROOT / "app" / "dashboard.py")).run()

    assert not app.exception
    assert any("No Spark runs recorded yet." in message.value for message in app.info)
    assert any(
        "docker compose --profile spark run --build --rm spark-benchmark"
        in code.value
        for code in app.code
    )


def test_dashboard_renders_checked_in_spark_run() -> None:
    app = AppTest.from_file(str(PROJECT_ROOT / "app" / "dashboard.py")).run()

    assert not app.exception
    assert any("Benchmark run" in item.label for item in app.selectbox)
