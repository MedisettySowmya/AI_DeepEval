"""Offline regression checks for the shared DeepEval input requirements."""
from types import SimpleNamespace

import pytest

from config.metrics import ENABLED_METRICS
from dataset.case_fields import is_missing, prepare_fields
from evaluate.execute.e2e import execute_test_cases
from metrics.requirements import builtin_required_params


ROW = {
    "id": "case-1",
    "input": "Question",
    "actual_output": "Answer",
    "expected_answer": "Expected answer",
    "reference_context": "Reference evidence",
    "retrieval_context": "Retrieved evidence",
}


class RecordedMetric:
    threshold = 0.8
    score = 0.9
    reason = "Judge explanation"

    def __init__(self, measured):
        self.measured = measured

    def measure(self, case):
        self.measured.append(case)

    def is_successful(self):
        return True


@pytest.mark.parametrize("module", ENABLED_METRICS, ids=lambda m: m.KEY)
def test_all_configured_metrics_keep_result_contract(monkeypatch, module):
    measured = []
    monkeypatch.setattr(module, "create_metric", lambda judge: RecordedMetric(measured))
    result = execute_test_cases([ROW], [module], None)[0]
    assert result == {
        "id": "case-1", "metric": module.KEY, "status": "completed",
        "score": 0.9, "threshold": 0.8, "passed": True,
        "reason": "Judge explanation", "error": None, "calculation": None,
    }
    assert len(measured) == 1
    assert measured[0].input == ROW["input"]
    assert measured[0].actual_output == ROW["actual_output"]


@pytest.mark.parametrize("module", ENABLED_METRICS, ids=lambda m: m.KEY)
def test_blank_answer_skips_before_judge_creation(monkeypatch, module):
    monkeypatch.setattr(module, "create_metric", lambda judge: pytest.fail("Judge created for blank data"))
    result = execute_test_cases([{**ROW, "actual_output": "  "}], [module], None)[0]
    assert result["status"] == "skipped"
    assert result["reason"] == "Missing required fields: actual_output"
    assert result["score"] is result["passed"] is result["threshold"] is None


def test_missing_reference_only_skips_metrics_that_need_it(monkeypatch):
    measured = []
    for module in ENABLED_METRICS:
        monkeypatch.setattr(module, "create_metric", lambda judge: RecordedMetric(measured))
    results = execute_test_cases([{**ROW, "reference_context": "  "}], ENABLED_METRICS, None)
    skipped = [r for r in results if r["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["metric"] == "HallucinationMetric"
    assert skipped[0]["reason"] == "Missing required fields: context"
    assert len(measured) == len(ENABLED_METRICS) - 1


def test_unrelated_malformed_context_does_not_break_answer_relevancy(monkeypatch):
    module = next(m for m in ENABLED_METRICS if m.KEY == "AnswerRelevancyMetric")
    measured = []
    monkeypatch.setattr(module, "create_metric", lambda judge: RecordedMetric(measured))
    row = {**ROW, "reference_context": {"invalid": "context"}, "retrieval_context": 123}
    result = execute_test_cases([row], [module], None)[0]
    assert result["status"] == "completed"
    assert measured[0].context is measured[0].retrieval_context is None


def test_metric_error_does_not_stop_remaining_metrics(monkeypatch):
    measured = []
    first, second = ENABLED_METRICS[:2]

    class FailingMetric(RecordedMetric):
        def measure(self, case):
            raise RuntimeError("Judge unavailable")

    monkeypatch.setattr(first, "create_metric", lambda judge: FailingMetric(measured))
    monkeypatch.setattr(second, "create_metric", lambda judge: RecordedMetric(measured))
    failed, completed = execute_test_cases([ROW], [first, second], None)
    assert failed["status"] == "error"
    assert failed["error"] == "Judge unavailable"
    assert failed["score"] is failed["passed"] is None
    assert completed["status"] == "completed"


def test_compatibility_helper_does_not_mutate_library_requirements():
    original = ["field"]
    metric_class = SimpleNamespace(_required_params=original)
    result = builtin_required_params(metric_class)
    result.append("application-only")
    assert original == ["field"]


def test_missing_library_contract_has_actionable_error():
    class ChangedMetric:
        pass

    with pytest.raises(TypeError, match="Check metrics/requirements.py"):
        builtin_required_params(ChangedMetric)


def test_shared_field_mapping_keeps_evidence_separate():
    row = {**ROW, "context": "Generation-only context", "reference_context": None}
    fields = prepare_fields(row)
    assert fields["context"] is None
    assert fields["retrieval_context"] == ["Retrieved evidence"]
    assert fields["expected_output"] == "Expected answer"
    assert row["retrieval_context"] == "Retrieved evidence"
    assert is_missing([None, " ", []])
    assert not is_missing(["Evidence", " "])
