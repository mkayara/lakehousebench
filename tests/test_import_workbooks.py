from pathlib import Path

from openpyxl import Workbook

from scripts.import_workbooks import SOURCES, import_observations


def test_importer_converts_explicit_milliseconds_to_seconds(tmp_path: Path) -> None:
    workbooks = {}
    for source in SOURCES.values():
        filename = source["file"]
        if filename not in workbooks:
            workbook = Workbook()
            workbook.remove(workbook.active)
            workbooks[filename] = workbook
        workbook = workbooks[filename]
        worksheet = workbook.create_sheet(source["sheet"])
        for run in range(1, 11):
            row = source["first_row"] + run - 1
            worksheet[f"{source['column']}{row}"] = 100 if run == 1 else 50
    for filename, workbook in workbooks.items():
        workbook.save(tmp_path / filename)

    observations = import_observations(tmp_path)
    hive_simple = observations[
        (observations["engine"] == "Hive")
        & (observations["workload"] == "simple")
    ]
    assert len(observations) == 90
    assert hive_simple.iloc[0]["elapsed_seconds"] == 0.1
    assert hive_simple.iloc[0]["source_unit"] == "ms"
