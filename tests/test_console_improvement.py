"""Offline coverage of Excel rows using the real console improvement loop."""
import importlib.util
import json

import pytest

from dataset.case_fields import normalize_case
from evaluate import improvement_runner as runner
from prompt.prompt_builder import build_prompt


def case(identifier):
    return {"id": identifier, "input": f"Question {identifier}?",
            "context": "Trusted answer", "retrieval_context": "Retrieved evidence"}


def results(passed=False):
    return [{"metric": name, "status": "completed", "passed": passed,
             "score": 1.0 if passed else 0.1, "threshold": 0.7,
             "reason": "Offline feedback"} for name in sorted(runner.TARGETS)]


@pytest.fixture
def pipeline(monkeypatch):
    monkeypatch.setattr(runner.settings, "MAX_EVALUATION_RUNS", 3)
    monkeypatch.setattr(runner, "print_case_report", lambda *args, **kwargs: None)
    prompts = []
    monkeypatch.setattr(runner, "generate_response",
                        lambda prompt: prompts.append(prompt) or f"Answer {len(prompts)}")
    return prompts


def test_all_enabled_metrics_control_reruns(monkeypatch, tmp_path, pipeline):
    baseline = results()
    for result in baseline:
        if result["metric"] in {"HallucinationMetric", "AnswerRelevancyMetric"}:
            result.update(passed=True, score=1.0)
    batches = iter([baseline, results(True)])
    monkeypatch.setattr(runner, "evaluate", lambda *args: next(batches))
    report = runner.improve_prompt(normalize_case(case("one")), None, tmp_path,
                                   review_fn=lambda _: "Approved prompt")
    assert len(pipeline) == 2
    assert report["best_run"] == 2
    assert report["stop_reason"] == "thresholds_met"
    saved = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert len(saved["runs"][0]["results"]) == len(runner.ENABLED_METRICS)


def test_ranking_rejects_old_two_metric_results():
    assert runner.rank_results(results()[:2]) is None
    assert runner.rank_results([]) is None


@pytest.mark.parametrize("status", ["error", "skipped"])
def test_incomplete_metrics_do_not_request_improvement(monkeypatch, tmp_path, pipeline, status):
    batch = results()
    batch[0].update(status=status, score=None, passed=None)
    monkeypatch.setattr(runner, "evaluate", lambda *args: batch)
    report = runner.improve_prompt(case("incomplete"), None, tmp_path,
                                   review_fn=lambda _: pytest.fail("Unexpected review"))
    assert report["stop_reason"] == "evaluation_incomplete"
    assert report["best_run"] is None
    assert len(pipeline) == 1


def test_limit_and_rejection(monkeypatch, tmp_path, pipeline):
    monkeypatch.setattr(runner, "evaluate", lambda *args: results())
    reviews = []
    def approve(suggestion):
        reviews.append(suggestion)
        return suggestion["improved_prompt"]
    report = runner.improve_prompt(case("limit"), None, tmp_path, review_fn=approve)
    assert len(pipeline) == 3 and len(reviews) == 2
    assert report["stop_reason"] == "run_limit"
    assert report["best_run"] == 1
    report = runner.improve_prompt(case("reject"), None, tmp_path, review_fn=lambda _: None)
    assert len(pipeline) == 4
    assert report["stop_reason"] == "review_declined"


def test_unavailable_stdin_preserves_suggestion(monkeypatch, tmp_path, pipeline):
    monkeypatch.setattr(runner, "evaluate", lambda *args: results())
    def unavailable(_):
        raise OSError("stdin is captured")
    report = runner.improve_prompt(case("no-stdin"), None, tmp_path, review_fn=unavailable)
    assert report["stop_reason"] == "awaiting_review"
    assert report["runs"][0]["suggestion"]
    assert len(pipeline) == 1


def test_generator_io_error_is_not_mistaken_for_review(monkeypatch, tmp_path):
    def unavailable(_):
        raise OSError("Model connection failed")
    monkeypatch.setattr(runner, "generate_response", unavailable)
    report = runner.improve_prompt(case("error"), None, tmp_path)
    assert report["stop_reason"] == "error"
    assert report["error"] == "Model connection failed"


def test_interrupt_saves_history_and_stops_batch(monkeypatch, tmp_path, pipeline):
    monkeypatch.setattr(runner, "evaluate", lambda *args: results())
    def interrupt(_):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        runner.improve_prompt(case("interrupt"), None, tmp_path, review_fn=interrupt)
    saved = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert saved["stop_reason"] == "interrupted"
    assert len(pipeline) == 1


def test_existing_excel_entry_point_improves_every_row(monkeypatch, tmp_path, pipeline):
    rows = [case(name) for name in ("improve", "reject", "error", "pass")]
    monkeypatch.setattr("dataset.dataset_loader.load_dataset", lambda _: rows)
    path = runner.PROJECT_ROOT / "tests" / "test_metrics.py"
    spec = importlib.util.spec_from_file_location("excel_metrics_entry", path)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    monkeypatch.setattr(entry, "REPORT_DIRECTORY", tmp_path)
    evaluated = []
    def evaluate(cases, judge):
        row = cases[0]
        evaluated.append(row)
        if row["id"] == "error":
            raise RuntimeError("Judge unavailable")
        return results(row["id"] == "pass" or
                       (row["id"] == "improve" and len(evaluated) == 2))
    monkeypatch.setattr(runner, "evaluate", evaluate)
    approvals = iter(["Approved revised prompt", None])
    monkeypatch.setattr(runner, "review_prompt", lambda _: next(approvals))
    report = {"run_id": "offline-excel", "cases": []}
    for row in entry.test_cases:
        entry.test_metrics(row, (None, None), report)
    assert [row["id"] for row in evaluated] == ["improve", "improve", "reject", "error", "pass"]
    assert len(pipeline) == 5  # No repeated baseline generation.
    assert len(report["cases"]) == 4
    assert [row["improvement"]["stop_reason"] for row in report["cases"]] == [
        "thresholds_met", "review_declined", "error", "thresholds_met"]
    assert report["cases"][0]["selected_run"] == 2
    assert report["cases"][0]["prompt"] == "Approved revised prompt"
    assert report["cases"][0]["actual_output"] == "Answer 2"
    assert report["cases"][2]["status"] == "error"
    assert all(row["expected_answer"] == row["reference_context"] == "Trusted answer" for row in evaluated)
    assert "Trusted answer" not in pipeline[0]
    saved = json.loads((tmp_path / "offline-excel.json").read_text())
    assert len(saved["cases"]) == 4
    assert len(list((tmp_path / "improvements").glob("*.json"))) == 4


def test_ground_truth_is_not_used_as_generation_fallback():
    row = normalize_case({"input": "Question?", "context": "Correct answer",
                          "expected_answer": "Old value", "prompt_context": "Old source"})
    assert row["expected_answer"] == row["reference_context"] == "Correct answer"
    assert build_prompt(row) == "Question?"
