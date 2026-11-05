import argparse
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


SOURCES = {
    ("Hive", "simple"): {
        "file": "Experiment Data - HIVE.xlsx",
        "sheet": "simplequery",
        "column": "C",
        "first_row": 4,
        "source_unit": "ms",
        "unit_basis": "Source header says ms; converted literally; unit needs verification",
    },
    ("Hive", "moderate"): {
        "file": "Experiment Data - HIVE.xlsx",
        "sheet": "moderatequery",
        "column": "E",
        "first_row": 4,
        "source_unit": "s",
        "unit_basis": "Summary worksheet explicitly labels execution time as seconds",
    },
    ("Hive", "complex"): {
        "file": "Experiment Data - HIVE.xlsx",
        "sheet": "complexquery",
        "column": "F",
        "first_row": 5,
        "source_unit": "s",
        "unit_basis": "Summary worksheet explicitly labels execution time as seconds",
    },
    ("Pig", "simple"): {
        "file": "Experiment Data - PIG.xlsx",
        "sheet": "simplequery",
        "column": "C",
        "first_row": 4,
        "source_unit": "s",
        "unit_basis": "Source header explicitly labels execution time as seconds",
    },
    ("Pig", "moderate"): {
        "file": "Experiment Data - PIG.xlsx",
        "sheet": "moderatequery",
        "column": "F",
        "first_row": 4,
        "source_unit": "not stated",
        "unit_basis": "Workbook omits units; seconds assumed for analysis",
    },
    ("Pig", "complex"): {
        "file": "Experiment Data - PIG.xlsx",
        "sheet": "complexquery",
        "column": "I",
        "first_row": 5,
        "source_unit": "not stated",
        "unit_basis": "Workbook omits units; seconds assumed for analysis",
    },
    ("Impala", "simple"): {
        "file": "Experiment Data - IMPALA.xlsx",
        "sheet": "simplequery",
        "column": "C",
        "first_row": 4,
        "source_unit": "not stated",
        "unit_basis": "Workbook omits units; seconds assumed for analysis",
    },
    ("Impala", "moderate"): {
        "file": "Experiment Data - IMPALA.xlsx",
        "sheet": "moderatequery",
        "column": "C",
        "first_row": 4,
        "source_unit": "not stated",
        "unit_basis": "Workbook omits units; seconds assumed for analysis",
    },
    ("Impala", "complex"): {
        "file": "Experiment Data - IMPALA.xlsx",
        "sheet": "complexquery",
        "column": "C",
        "first_row": 4,
        "source_unit": "not stated",
        "unit_basis": "Workbook omits units; seconds assumed for analysis",
    },
}


def import_observations(input_dir: Path) -> pd.DataFrame:
    rows = []
    for (engine, workload), source in SOURCES.items():
        workbook_path = input_dir / source["file"]
        if not workbook_path.is_file():
            raise FileNotFoundError(f"Source workbook not found: {workbook_path}")
        workbook = load_workbook(workbook_path, read_only=True, data_only=True)
        try:
            worksheet = workbook[source["sheet"]]
            for run in range(1, 11):
                row_number = source["first_row"] + run - 1
                value = worksheet[f"{source['column']}{row_number}"].value
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Expected a numeric timing at "
                        f"{source['file']}:{source['sheet']}!"
                        f"{source['column']}{row_number}"
                    )
                scale = 0.001 if source["source_unit"] == "ms" else 1.0
                rows.append(
                    {
                        "engine": engine,
                        "workload": workload,
                        "run": run,
                        "elapsed_value": value,
                        "source_unit": source["source_unit"],
                        "elapsed_seconds": value * scale,
                        "unit_basis": source["unit_basis"],
                        "source_workbook": source["file"],
                    }
                )
        finally:
            workbook.close()
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert source workbooks to tidy CSV.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/observations.csv"))
    args = parser.parse_args()

    observations = import_observations(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    observations.to_csv(args.output, index=False)
    print(f"Wrote {len(observations)} observations to {args.output}")


if __name__ == "__main__":
    main()
