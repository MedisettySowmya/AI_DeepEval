"""Optional UI checks. Run explicitly; normal pytest does not require the UI."""
import json
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ui import app as improvement_runner
from evaluate.execute.e2e import calculation_details
from ui import app


CASE = {"id": "1", "category": "Example", "input": "What is the capital?",
        "context": "The capital is Paris.", "retrieval_context": "Paris is the French capital.",
        "prompt_context": "Paris is the French capital.",
        "reference_context": "The capital is Paris.", "expected_answer": "Paris"}


@pytest.fixture
def console(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "REPORT_DIRECTORY", tmp_path)
    monkeypatch.setattr(app, "read_dataset", lambda name=None: {
        "workbooks": ["example.xlsx"], "workbook": "example.xlsx", "cases": [CASE]
    })
    monkeypatch.setattr(app, "create_judge", lambda: None)
    monkeypatch.setattr(improvement_runner.settings, "MAX_EVALUATION_RUNS", 3)
    prompts, cases = [], []

    def generate(prompt):
        prompts.append(prompt)
        return "Paris"

    def evaluate(rows, judge):
        cases.append(rows[0])
        passed = len(cases) > 1
        return [{"metric": key, "status": "completed", "score": 1.0 if passed else 0.2,
                 "threshold": 0.7, "passed": passed, "reason": "Offline feedback."}
                for key in sorted(improvement_runner.TARGETS)]

    monkeypatch.setattr(improvement_runner, "generate_response", generate)
    monkeypatch.setattr(improvement_runner, "evaluate", evaluate)
    server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"

    def request(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    yield request, prompts, cases
    # Release any review still waiting if an assertion failed.
    with app._lock:
        for job in app._jobs.values():
            if job.get("event") and job.get("decision") is None:
                job["decision"] = {"prompt": None}
                job["event"].set()
    server.shutdown()
    server.server_close()


def wait_for(request, job_id, state):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status, job = request("/api/status?id=" + job_id)
        assert status == 200
        if job["state"] == state:
            return job
        time.sleep(0.01)
    pytest.fail(f"Evaluation never reached {state}: {job}")


def test_excel_to_browser_review_and_rerun(console):
    request, prompts, cases = console
    status, dataset = request("/api/dataset")
    assert status == 200 and dataset["cases"][0]["id"] == "1"
    status, response = request("/api/run", {"workbook": "example.xlsx", "case_index": 0})
    assert status == 202
    job = wait_for(request, response["id"], "awaiting_review")
    assert len(prompts) == 1
    assert job["report"]["runs"][0]["suggestion"]["causes"]

    status, _ = request("/api/review", {"id": response["id"], "decision": "approve",
                                       "prompt": "Human edited prompt", "run": 1})
    assert status == 200
    finished = wait_for(request, response["id"], "finished")
    assert prompts[1] == "Human edited prompt"
    assert len(cases) == 2
    assert cases[1]["input"] == CASE["input"]
    assert cases[1]["reference_context"] == CASE["reference_context"]
    assert finished["report"]["best_run"] == 2
    assert finished["report"]["stop_reason"] == "thresholds_met"
    status, saved = request("/api/reports")
    status, report = request("/api/report?name=" + saved["reports"][0])
    assert status == 200 and report["runs"][0]["review"]["approved"]


def test_browser_reject_stale_and_empty_approval(console):
    request, prompts, _ = console
    _, response = request("/api/run", {"case_index": 0})
    job_id = response["id"]
    wait_for(request, job_id, "awaiting_review")
    assert request("/api/review", {"id": job_id, "decision": "approve", "prompt": "", "run": 1})[0] == 400
    assert request("/api/review", {"id": job_id, "decision": "approve", "prompt": "Hi", "run": 0})[0] == 400
    assert len(prompts) == 1
    assert request("/api/review", {"id": job_id, "decision": "reject", "run": 1})[0] == 200
    finished = wait_for(request, job_id, "finished")
    assert finished["report"]["stop_reason"] == "review_declined"
    assert len(prompts) == 1
    assert request("/api/review", {"id": job_id, "decision": "approve", "prompt": "Hi", "run": 1})[0] == 400


def test_bad_case_index_and_unknown_report(console):
    request, _, _ = console
    assert request("/api/run", {"case_index": -1})[0] == 400
    assert request("/api/run", {"case_index": "0"})[0] == 400
    assert request("/api/report?name=../../config/settings.py")[0] == 404


def test_manual_case_does_not_require_excel(console, monkeypatch):
    request, prompts, evaluated = console
    monkeypatch.setattr(app, "read_dataset", lambda *args: pytest.fail("Manual mode read Excel"))
    manual = {"input": "A question typed in the UI?", "context": "Trusted answer",
              "retrieval_context": "Retrieved source"}
    status, response = request("/api/run", {"case": manual})
    assert status == 202
    job = wait_for(request, response["id"], "awaiting_review")
    assert job["workbook"] is None
    assert job["case"]["source"]["type"] == "manual"
    assert "A question typed in the UI?" in prompts[0]
    assert "Retrieved source" in prompts[0]
    assert "Trusted answer" not in prompts[0]
    assert evaluated[0]["reference_context"] == "Trusted answer"
    assert evaluated[0]["expected_answer"] == "Trusted answer"
    assert evaluated[0]["prompt_context"] == "Retrieved source"
    assert evaluated[0]["retrieval_context"] == "Retrieved source"
    assert request("/api/review", {"id": response["id"], "decision": "reject", "run": 1})[0] == 200
    wait_for(request, response["id"], "finished")


def test_excel_edits_use_draft_without_changing_original(console):
    request, prompts, evaluated = console
    status, response = request("/api/run", {"case_index": 0, "overrides": {
        "input": "Edited question?", "retrieval_context": "Edited source",
        "context": "Edited truth",
    }})
    assert status == 202
    job = wait_for(request, response["id"], "awaiting_review")
    assert job["case"]["id"] == CASE["id"]
    assert "Edited question?" in prompts[0]
    assert evaluated[0]["reference_context"] == "Edited truth"
    assert evaluated[0]["expected_answer"] == "Edited truth"
    assert evaluated[0]["prompt_context"] == "Edited source"
    assert job["case"]["source"]["original_case"] == CASE
    assert request("/api/dataset")[1]["cases"][0] == CASE
    assert request("/api/review", {"id": response["id"], "decision": "reject", "run": 1})[0] == 200
    wait_for(request, response["id"], "finished")


def test_approve_from_test_case_form_updates_both_generator_and_judge(console):
    request, prompts, evaluated = console
    _, response = request("/api/run", {"case_index": 0})
    job_id = response["id"]
    wait_for(request, job_id, "awaiting_review")
    revised = {"input": "Which city is the capital of France?", "context": "Paris is the capital of France.",
               "retrieval_context": "A retrieved passage about Paris", "instructions": "Answer directly. Do not guess."}
    status, _ = request("/api/review", {"id": job_id, "decision": "approve", "run": 1, "edits": revised})
    assert status == 200
    finished = wait_for(request, job_id, "finished")
    assert len(prompts) == 2
    assert revised["input"] in prompts[1]
    assert revised["instructions"] in prompts[1]
    assert revised["retrieval_context"] in prompts[1]
    assert revised["context"] not in prompts[1]
    assert evaluated[1]["input"] == revised["input"]
    assert evaluated[1]["prompt_context"] == revised["retrieval_context"]
    assert evaluated[1]["retrieval_context"] == revised["retrieval_context"]
    assert evaluated[1]["reference_context"] == revised["context"]
    assert evaluated[1]["expected_answer"] == revised["context"]
    runs = finished["report"]["runs"]
    assert runs[0]["test_case"]["input"] == CASE["input"]
    assert runs[1]["test_case"]["input"] == revised["input"]
    assert runs[0]["review"]["prompt"] == prompts[1]
    assert runs[1]["evaluation_inputs_changed"] is True


def test_empty_question_in_review_form_keeps_review_pending(console):
    request, prompts, _ = console
    _, response = request("/api/run", {"case_index": 0})
    job_id = response["id"]
    wait_for(request, job_id, "awaiting_review")
    status, _ = request("/api/review", {"id": job_id, "decision": "approve", "run": 1,
                                       "edits": {"input": " ", "context": "A source"}})
    assert status == 400
    assert len(prompts) == 1
    assert request("/api/status?id=" + job_id)[1]["state"] == "awaiting_review"
    request("/api/review", {"id": job_id, "decision": "reject", "run": 1})
    wait_for(request, job_id, "finished")


@pytest.mark.parametrize("form", [
    {"case": {"input": " "}},
    {"case": {"input": 123}},
    {"case": {"input": "Question", "score": 1}},
    {"case_index": 0, "overrides": {"input": []}},
])
def test_invalid_editor_fields_do_not_generate(console, form):
    request, prompts, _ = console
    assert request("/api/run", form)[0] == 400
    assert not prompts


@pytest.mark.parametrize("metric_key,expected", [
    ("HallucinationMetric", 1), ("AnswerRelevancyMetric", 2),
])
def test_actual_verdict_breakdown(metric_key, expected):
    metric = SimpleNamespace(verdicts=[
        SimpleNamespace(verdict="yes", reason="Supported"),
        SimpleNamespace(verdict="borderline", reason="Partial relevance"),
        SimpleNamespace(verdict="no", reason="Unsupported"),
    ], statements=["First", "Second", "Third"], strict_mode=False)
    detail = calculation_details(metric, metric_key, {"context": ["Source"]})
    assert detail["passing"] == expected
    assert detail["total"] == 3
    assert len(detail["verdicts"]) == 3


def test_missing_retrieval_does_not_supply_ground_truth_to_generator():
    case = app.normalize_ui_case({"input": "Question?", "context": "Trusted answer"})
    assert app.build_prompt(case) == "Question?"
    assert case["reference_context"] == case["expected_answer"] == "Trusted answer"
    assert case["retrieval_context"] == ""


def test_clearing_ground_truth_removes_old_evaluation_values():
    case = app.normalize_ui_case({"context": "", "expected_answer": "Old answer",
                                  "reference_context": "Old source", "retrieval_context": "Evidence"})
    assert case["expected_answer"] == case["reference_context"] == ""
    assert case["prompt_context"] == "Evidence"
