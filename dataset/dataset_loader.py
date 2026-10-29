from pathlib import Path

import pandas as pd


def _clean(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def load_dataset(file_path):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    test_cases = []

    with pd.ExcelFile(path) as workbook:
        for sheet_name in workbook.sheet_names:
            rows = pd.read_excel(workbook, sheet_name=sheet_name)

            for position, row in rows.iterrows():
                context = _clean(row.get("Context"))

                test_cases.append(
                    {
                        "id": (
                            _clean(row.get("ID"))
                            or f"{sheet_name}:{position}"
                        ),
                        "category": sheet_name,
                        "input": _clean(row.get("Input")),
                        "context": context,
                        "retrieval_context": _clean(
                            row.get("retrieval_context")
                        ),
                        "prompt_context": (
                            _clean(row.get("Prompt_Context"))
                            if "Prompt_Context" in rows.columns
                            else context
                        ),
                        "reference_context": (
                            _clean(row.get("Reference_Context"))
                            if "Reference_Context" in rows.columns
                            else context
                        ),
                        "expected_answer": _clean(row.get("Ground_Truth")),
                        "pattern": _clean(row.get("Pattern")),
                    }
                )

    return test_cases