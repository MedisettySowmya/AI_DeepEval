from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from deepeval.test_case import LLMTestCase, SingleTurnParams

from dataset import dataset_loader
from evaluate.execute.e2e import execute_test_cases, prepare_fields


def test_context_text_conversion():
    row = {
        "input": "Question",
        "actual_output": "Answer",
        "reference_context": " Source passage ",
        "retrieval_context": "Retrieved passage",
    }
    case = LLMTestCase(**prepare_fields(row))
    assert case.context == ["Source passage"]
    assert case.retrieval_context == ["Retrieved passage"]
    assert row["reference_context"] == " Source passage "


def test_context_list_preserved():
    passages = ["First passage", "Second passage"]
    fields = prepare_fields({"reference_context": passages, "retrieval_context": " "})
    assert fields["context"] == passages
    assert fields["retrieval_context"] == []


@pytest.mark.parametrize("reference", [None, "", "Reference evidence"])
def test_reference_is_separate(reference):
    fields = prepare_fields({"context": "Generation evidence", "reference_context": reference})
    assert fields["context"] == ([reference] if reference else ([] if reference == "" else None))
    assert prepare_fields({"context": "Generation evidence"})["context"] is None


@pytest.mark.parametrize("reference", [None, "", "Reference evidence"])
def test_dataset_reference(monkeypatch, reference):
    row = {"Input": "Question", "Context": "Generation evidence"}
    if reference is not None:
        row["Reference_Context"] = reference
    workbook = MagicMock()
    workbook.__enter__.return_value.sheet_names = ["Cases"]
    monkeypatch.setattr(dataset_loader.pd, "ExcelFile", lambda path: workbook)
    monkeypatch.setattr(dataset_loader.pd, "read_excel", lambda *args, **kwargs: pd.DataFrame([row]))
    case = dataset_loader.load_dataset(__file__)[0]
    assert case["context"] == "Generation evidence"
    assert case["reference_context"] == (reference or "")


def test_verdicts_and_missing_context():
    measured = []

    class Metric:
        threshold = 0.5
        score = 1.0
        reason = "Supported"

        def measure(self, case):
            measured.append(case)
            self.verdicts = [SimpleNamespace(verdict="yes", reason="Supported")]

        def is_successful(self):
            return True

    module = SimpleNamespace(
        KEY="HallucinationMetric",
        REQUIRED_PARAMS=[SingleTurnParams.CONTEXT],
        create_metric=lambda judge: Metric(),
    )
    results = execute_test_cases([
        {"id": 1, "input": "Question", "actual_output": "Answer", "reference_context": "Source"},
        {"id": 2, "input": "Question", "actual_output": "Answer", "context": "Generation only"},
    ], [module], None)
    assert len(measured) == 1
    assert measured[0].context == ["Source"]
    assert results[0]["status"] == "completed"
    assert results[0]["calculation"]["verdicts"][0]["item"] == "Source"
    assert results[0]["calculation"]["passing"] == 1
    assert results[1]["status"] == "skipped"
    assert results[1]["reason"] == "Missing required fields: context"
