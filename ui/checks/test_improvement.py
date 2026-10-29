import json

import pytest

from ui import app as runner
from ui.prompt_analyzer import analyze_prompt


CASE = {"id": "demo", "input": "What is the capital?",
        "prompt_context": "The capital is Paris.",
        "reference_context": "The capital is Paris."}


def results(passed=False):
    return [{"metric": name, "status": "completed", "passed": passed,
             "score": 1.0 if passed else 0.1, "threshold": 0.7,
             "reason": "The answer includes unrelated unsupported claims."}
            for name in sorted(runner.TARGETS)]


def setup_pipeline(monkeypatch, batches):
    prompts, evaluated = [], []

    def generate(prompt):
        prompts.append(prompt)
        return "A generated answer"

    def evaluate(cases, judge):
        evaluated.append(cases[0])
        return batches[len(evaluated) - 1]

    monkeypatch.setattr(runner, "generate_response", generate)
    monkeypatch.setattr(runner, "evaluate", evaluate)
    monkeypatch.setattr(runner.settings, "MAX_EVALUATION_RUNS", 3)
    return prompts, evaluated


def test_approved_prompt_is_rerun_with_original_evaluation_question(monkeypatch, tmp_path):
    prompts, evaluated = setup_pipeline(monkeypatch, [results(), results(True)])
    report = runner.improve_prompt(CASE, None, tmp_path,
                                   review_fn=lambda suggestion: "Human edited prompt")
    assert len(prompts) == 2
    assert prompts[1] == "Human edited prompt"
    assert all(case["input"] == CASE["input"] for case in evaluated)
    assert all(case["reference_context"] == CASE["reference_context"] for case in evaluated)
    assert report["best_run"] == 2
    assert report["stop_reason"] == "thresholds_met"
    saved = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert saved["runs"][0]["review"]["approved"] is True


def test_rejection_prevents_another_generation(monkeypatch, tmp_path):
    prompts, _ = setup_pipeline(monkeypatch, [results()])
    report = runner.improve_prompt(CASE, None, tmp_path, review_fn=lambda suggestion: None)
    assert len(prompts) == 1
    assert report["stop_reason"] == "review_declined"


def test_three_total_runs_and_no_review_after_final_run(monkeypatch, tmp_path):
    prompts, _ = setup_pipeline(monkeypatch, [results()] * 3)
    reviews = []

    def approve(suggestion):
        reviews.append(suggestion)
        return suggestion["improved_prompt"]

    report = runner.improve_prompt(CASE, None, tmp_path, review_fn=approve)
    assert len(prompts) == 3
    assert len(reviews) == 2
    assert report["best_run"] == 1
    assert report["stop_reason"] == "run_limit"


@pytest.mark.parametrize("status", ["error", "skipped"])
def test_incomplete_evaluation_cannot_win_or_request_review(monkeypatch, tmp_path, status):
    batch = results()
    batch[0].update(status=status, score=None, passed=None)
    prompts, _ = setup_pipeline(monkeypatch, [batch])
    report = runner.improve_prompt(CASE, None, tmp_path,
                                   review_fn=lambda _: pytest.fail("Unexpected review"))
    assert len(prompts) == 1
    assert report["best_run"] is None
    assert report["stop_reason"] == "evaluation_incomplete"


def test_template_keeps_original_prompt_without_copying_judge_claims():
    suggestion = analyze_prompt(CASE, "Original question and context", results())
    assert "Original question and context" in suggestion["improved_prompt"]
    assert "unsupported claims" not in suggestion["improved_prompt"]
    again = analyze_prompt(CASE, suggestion["improved_prompt"], results())
    assert again["improved_prompt"] == suggestion["improved_prompt"]


def test_unavailable_terminal_preserves_suggestion_without_rerun(monkeypatch, tmp_path):
    prompts, _ = setup_pipeline(monkeypatch, [results()])

    def unavailable(suggestion):
        raise EOFError()

    report = runner.improve_prompt(CASE, None, tmp_path, review_fn=unavailable)
    assert len(prompts) == 1
    assert report["stop_reason"] == "awaiting_review"
    assert report["runs"][0]["suggestion"] is not None
    assert report["runs"][0]["review"] is None


def test_analysis_flags_different_context_for_human_validation():
    case = {**CASE, "prompt_context": "A different source."}
    suggestion = analyze_prompt(case, "Prompt", results())
    assert any("different context" in cause["possible_cause"]
               for cause in suggestion["causes"])
