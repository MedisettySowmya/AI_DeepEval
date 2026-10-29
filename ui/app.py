"""Optional browser UI: python -m ui.app.

Browser editing, approval, HTTP routes, and job state belong to this module.
The normal evaluation workflow must not import ui, so this folder is removable.
"""
import copy
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from config.metrics import ENABLED_METRICS
from dataset.dataset_loader import load_dataset
from dataset.case_fields import normalize_case
from evaluate import evaluate
from models.model_client import create_judge, generate_response
from prompt.prompt_builder import build_prompt
from ui.prompt_analyzer import analyze_prompt
from report.report_generator import print_case_report

HOST = "127.0.0.1"
PORT = int(os.environ.get("EVAL_UI_PORT", "8000"))
DATASET_DIRECTORY = PROJECT_ROOT / "dataset"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "improvements"
_jobs = {}
_lock = threading.Lock()


TARGETS = {metric.KEY for metric in ENABLED_METRICS}


def rank_results(results):
    """Only complete results can win. DeepEval 4.3.1: higher is better."""
    if not results or len(results) != len(TARGETS) or {r["metric"] for r in results} != TARGETS:
        return None
    for result in results:
        score = result.get("score")
        if (result.get("status") != "completed"
                or not isinstance(result.get("passed"), bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(score)):
            return None
    scores = [r["score"] for r in results]
    return (sum(r["passed"] for r in results), min(scores), sum(scores) / len(scores))


def improve_prompt(test_case, judge, report_directory=None, *, review_fn,
                   on_update=None):
    """Evaluate baseline plus at most two explicitly approved revisions."""
    limit = settings.MAX_EVALUATION_RUNS
    if type(limit) is not int or not 1 <= limit <= 3:
        raise ValueError("MAX_EVALUATION_RUNS must be between 1 and 3.")
    directory = Path(report_directory or PROJECT_ROOT / "reports" / "improvements")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"improvement-{uuid4().hex[:8]}.json"
    report = {
        "session": settings.IMPROVEMENT_SESSION,
        "generator_model": settings.GENERATOR_MODEL,
        "judge_model": settings.JUDGE_MODEL,
        "case": dict(test_case), "runs": [], "best_run": None,
        "stop_reason": None,
        "stage": "generating",
        "ranking": "passing metrics, minimum score, average score; earlier wins ties",
    }

    def save():
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                        allow_nan=False), encoding="utf-8")
        temporary.replace(path)
        if on_update:
            on_update(report)

    current_case = dict(test_case)
    prompt = build_prompt(current_case)
    best_rank = None
    try:
        if not str(test_case.get("input") or "").strip():
            raise ValueError("The test case needs a question.")
        for number in range(1, limit + 1):
            report["stage"] = "generating"
            run = {"run": number, "prompt": prompt, "actual_output": None,
                   "results": [], "suggestion": None, "review": None,
                   "test_case": dict(current_case),
                   "evaluation_inputs_changed": any(
                       current_case.get(key) != test_case.get(key)
                       for key in ("input", "prompt_context", "reference_context", "retrieval_context", "expected_answer")
                   )}
            report["runs"].append(run)
            save()
            run["actual_output"] = generate_response(prompt)
            report["stage"] = "evaluating"
            save()
            # Browser review may explicitly approve revised question/context too.
            run["results"] = evaluate(
                [{**current_case, "actual_output": run["actual_output"]}], judge
            )
            print(f"\nRun {number}")
            print_case_report(
                {**current_case, "actual_output": run["actual_output"]},
                run["results"], status="evaluated",
            )
            rank = rank_results(run["results"])
            if rank is None:
                report["stop_reason"] = "evaluation_incomplete"
                break
            if best_rank is None or rank > best_rank:
                best_rank = rank
                report["best_run"] = number
            save()
            if rank[0] == len(TARGETS):
                report["stop_reason"] = "thresholds_met"
                break
            if number == limit:
                report["stop_reason"] = "run_limit"
                break
            run["suggestion"] = analyze_prompt(current_case, prompt, run["results"])
            report["stage"] = "awaiting_review"
            save()  # Preserve the suggestion before waiting for approval.
            approved = review_fn(run["suggestion"])
            if isinstance(approved, dict):
                current_case = dict(approved["test_case"])
                approved = build_prompt(current_case)
            run["review"] = {"approved": approved is not None, "prompt": approved}
            if approved is not None:
                run["review"]["test_case"] = dict(current_case)
            if approved is None:
                report["stop_reason"] = "review_declined"
                break
            if not isinstance(approved, str) or not approved.strip():
                raise ValueError("Approved prompt must be nonempty text.")
            prompt = approved
            save()  # Record approval before the next model call.
    except (EOFError, OSError):
        # No terminal input (for example CI): preserve the proposal for review.
        report["stop_reason"] = "awaiting_review"
    except KeyboardInterrupt:
        report["stop_reason"] = "interrupted"
    except Exception as exc:
        report["stop_reason"] = "error"
        report["error"] = str(exc)
    finally:
        report["stage"] = "finished"
        save()

    print(f"\nStopped: {report['stop_reason']}\nReport: {path}")
    if report["best_run"] is not None:
        best = report["runs"][report["best_run"] - 1]
        print(f"Best run: {best['run']}\nBest prompt:\n{best['prompt']}")
    return report


def read_dataset(name=None):
    files = sorted(path.name for path in DATASET_DIRECTORY.glob("*.xlsx")
                   if not path.name.startswith("~$"))
    if not files:
        raise ValueError("No Excel workbooks found in the dataset folder.")
    name = name or ("test_cases_datasets.xlsx" if "test_cases_datasets.xlsx" in files else files[0])
    if name not in files:
        raise ValueError("Choose an Excel workbook from the dataset folder.")
    return {"workbooks": files, "workbook": name,
            "cases": load_dataset(DATASET_DIRECTORY / name)}


def get_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        snapshot = copy.deepcopy({key: value for key, value in job.items()
                                  if key not in {"event", "decision"}})
    snapshot["elapsed"] = round(time.monotonic() - snapshot.pop("started"), 1)
    return snapshot


def submit_review(job_id, decision, prompt=None, run_number=None, edits=None):
    if decision not in {"approve", "reject"}:
        raise ValueError("Decision must be approve or reject.")
    if decision == "approve" and edits is None and (not isinstance(prompt, str) or not prompt.strip()):
        raise ValueError("An approved prompt cannot be empty.")
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise ValueError("Evaluation not found.")
        if (job["state"] != "awaiting_review" or not job.get("event")
                or job.get("decision") is not None):
            raise ValueError("This evaluation is not waiting for a review.")
        if run_number != job["report"]["runs"][-1]["run"]:
            raise ValueError("This review is outdated. Refresh the evaluation.")
        if decision == "approve" and edits is not None:
            case = copy.deepcopy(job["report"]["runs"][-1].get("test_case", job["case"]))
            case.update(validate_edits(edits))
            if not case.get("input", "").strip():
                raise ValueError("A question is required before approving the next run.")
            case = normalize_ui_case(case)
            job["decision"] = {"test_case": case, "prompt": build_prompt(case)}
        else:
            job["decision"] = {"prompt": prompt if decision == "approve" else None}
        job["state"] = "review_submitted"
        job["event"].set()


def _run_job(job_id, case):
    def update(report):
        with _lock:
            _jobs[job_id]["report"] = copy.deepcopy(report)
            # Registering the review event below makes approval available.
            if report["stage"] != "awaiting_review":
                _jobs[job_id]["state"] = report["stage"]

    def review(suggestion):
        event = threading.Event()
        with _lock:
            _jobs[job_id].update(state="awaiting_review", event=event, decision=None)
        event.wait()  # The browser supplies a decision; never auto-approve.
        with _lock:
            decision = _jobs[job_id].pop("decision")
            _jobs[job_id].pop("event")
        return decision if "test_case" in decision else decision["prompt"]

    try:
        report = improve_prompt(case, create_judge(), REPORT_DIRECTORY,
                                review_fn=review, on_update=update)
        with _lock:
            _jobs[job_id].update(state="finished", report=copy.deepcopy(report))
    except Exception as error:
        with _lock:
            _jobs[job_id].update(state="error", error=str(error))


EDITABLE_FIELDS = {"input", "context", "retrieval_context", "instructions"}


def validate_edits(edits):
    if not isinstance(edits, dict) or set(edits) - EDITABLE_FIELDS:
        raise ValueError("Provide only question, context, retrieved context, and instruction fields.")
    if any(not isinstance(value, str) for value in edits.values()):
        raise ValueError("Test case fields must be text.")
    return {key: value.strip() for key, value in edits.items()}


def normalize_ui_case(case):
    """Map ground truth to judge inputs and retrieved passages to generation."""
    return normalize_case(case)


def start_job(workbook, case_index, *, custom_case=None, overrides=None):
    if custom_case is not None:
        edits = validate_edits(custom_case)
        case = {"id": f"manual-{uuid4().hex[:8]}", "category": "Manual", **edits,
                "source": {"type": "manual"}}
        workbook = None
    else:
        dataset = read_dataset(workbook)
        if type(case_index) is not int or not 0 <= case_index < len(dataset["cases"]):
            raise ValueError("Choose a valid Excel row.")
        original = dataset["cases"][case_index]
        case = copy.deepcopy(original)
        if overrides is not None:
            case.update(validate_edits(overrides))
        workbook = dataset["workbook"]
        case["source"] = {"type": "excel", "workbook": workbook,
                          "case_index": case_index, "original_case": copy.deepcopy(original)}
    case = normalize_ui_case(case)
    if not case.get("input", "").strip():
        raise ValueError("A question is required.")
    job_id = uuid4().hex
    with _lock:
        _jobs[job_id] = {"id": job_id, "state": "starting",
                         "started": time.monotonic(), "report": None,
                         "workbook": workbook, "case": copy.deepcopy(case)}
    threading.Thread(target=_run_job, args=(job_id, case), daemon=True).start()
    return job_id


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, status, data, content_type="application/json; charset=utf-8"):
        body = (json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
                if content_type.startswith("application/json") else data)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path)
        query = parse_qs(route.query)
        try:
            if route.path in {"/", "/index.html"}:
                return self.send(200, (Path(__file__).parent / "index.html").read_bytes(),
                                 "text/html; charset=utf-8")
            if route.path == "/api/config":
                return self.send(200, {"generator": settings.GENERATOR_MODEL,
                                      "judge": settings.JUDGE_MODEL,
                                      "max_runs": settings.MAX_EVALUATION_RUNS,
                                      "thresholds": settings.METRIC_THRESHOLDS})
            if route.path == "/api/dataset":
                return self.send(200, read_dataset(query.get("name", [None])[0]))
            if route.path == "/api/status":
                job = get_job(query.get("id", [""])[0])
                return self.send(200 if job else 404, job or {"error": "Evaluation not found."})
            if route.path == "/api/reports":
                files = sorted(REPORT_DIRECTORY.glob("improvement-*.json"),
                               key=lambda path: path.stat().st_mtime, reverse=True)[:50]
                return self.send(200, {"reports": [path.name for path in files]})
            if route.path == "/api/report":
                name = query.get("name", [""])[0]
                files = {path.name: path for path in REPORT_DIRECTORY.glob("improvement-*.json")}
                if name not in files:
                    return self.send(404, {"error": "Report not found."})
                return self.send(200, json.loads(files[name].read_text(encoding="utf-8")))
            self.send(404, {"error": "Not found."})
        except (ValueError, FileNotFoundError) as error:
            self.send(400, {"error": str(error)})
        except Exception as error:
            self.send(500, {"error": str(error)})

    def do_POST(self):
        try:
            # Only the local console may submit decisions to this local service.
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                return self.send(403, {"error": "Use the local evaluation console."})
            length = int(self.headers.get("Content-Length", 0))
            if length < 0 or length > 1_000_000:
                raise ValueError("Request is too large.")
            form = json.loads(self.rfile.read(length))
            if not isinstance(form, dict):
                raise ValueError("Expected a JSON object.")
            route = urlparse(self.path).path
            if route == "/api/run":
                return self.send(202, {"id": start_job(
                    form.get("workbook"), form.get("case_index"),
                    custom_case=form.get("case"), overrides=form.get("overrides"))})
            if route == "/api/review":
                submit_review(form.get("id"), form.get("decision"), form.get("prompt"),
                              form.get("run"), form.get("edits"))
                return self.send(200, {"accepted": True})
            self.send(404, {"error": "Not found."})
        except (ValueError, TypeError) as error:
            self.send(400, {"error": str(error)})
        except Exception as error:
            self.send(500, {"error": str(error)})


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Excel evaluation console: http://{HOST}:{PORT}")
    print("Review prompt changes in the browser. Ctrl+C stops the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
