from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import pytest

from dataset.dataset_loader import load_dataset
from dataset.case_fields import normalize_case
from evaluate.improvement_runner import improve_prompt
from models.model_client import create_judge
from report.report_generator import (
    create_run_report,
    print_case_report,
    save_run_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "dataset" / "test_cases_datasets.xlsx"
REPORT_DIRECTORY = PROJECT_ROOT / "reports"

test_cases = load_dataset(DATASET_PATH)


@pytest.fixture(scope="module")
def run_report():
    report = create_run_report()
    started = perf_counter()

    yield report

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["duration_seconds"] = perf_counter() - started

    path = save_run_report(report, REPORT_DIRECTORY)
    print(f"\nSaved report: {path}", flush=True)


@pytest.fixture(scope="module")
def judge_model():
    try:
        return create_judge(), None
    except Exception as exc:
        return None, str(exc)


def record_case(report, case, results, *, status, error=None):
    report["cases"].append(
        {
            **case,
            "status": status,
            "error": error,
            "results": results,
        }
    )

    save_run_report(report, REPORT_DIRECTORY)
    print_case_report(case, results, status=status, error=error)


@pytest.mark.parametrize(
    "test_case",
    test_cases,
    ids=[str(case["id"]) for case in test_cases],
)
def test_metrics(test_case, judge_model, run_report):
    """Evaluate and offer approved improvements for every Excel row."""
    prepared_case = normalize_case(test_case)
    results = []
    status = "error"
    error = None

    try:
        if not prepared_case.get("input", "").strip():
            status = "skipped"
            error = "Missing input."
            return

        judge, judge_error = judge_model

        if judge_error:
            error = f"Judge initialization failed: {judge_error}"
            return

        improvement = improve_prompt(
            prepared_case, judge, REPORT_DIRECTORY / "improvements",
        )
        prepared_case["improvement"] = improvement
        # Keep the summary's answer, prompt, and scores from the same run.
        if improvement["runs"]:
            selected = improvement["best_run"] or len(improvement["runs"])
            selected_run = improvement["runs"][selected - 1]
            prepared_case.update(
                selected_run=selected,
                prompt=selected_run["prompt"],
                actual_output=selected_run["actual_output"],
            )
            results = selected_run["results"]

        if any(result["status"] == "error" for result in results):
            status = "error"
        elif any(result["status"] == "completed" for result in results):
            status = "completed"
        else:
            status = "skipped"

        if not results:
            error = "No metric results were produced."

        if improvement["stop_reason"] == "error":
            status = "error"
            error = improvement.get("error")
        elif any(result["status"] == "error"
                 for run in improvement["runs"] for result in run["results"]):
            status = "error"

    except Exception as exc:
        status = "error"
        error = str(exc)

    finally:
        record_case(
            run_report,
            prepared_case,
            results,
            status=status,
            error=error,
        )
