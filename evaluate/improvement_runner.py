"""Console improvement workflow, called once for each Excel test case."""
import json
import math
from pathlib import Path
from uuid import uuid4

from config import settings
from config.metrics import ENABLED_METRICS
from evaluate import evaluate
from human_review.reviewer import review_prompt
from models.model_client import generate_response
from prompt.prompt_builder import build_prompt
from report.report_generator import print_case_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGETS = {metric.KEY for metric in ENABLED_METRICS}


def analyze_prompt(*args, **kwargs):
    """Reuse rule-based recommendations without starting the browser UI."""
    from ui.prompt_analyzer import analyze_prompt as analyze
    return analyze(*args, **kwargs)


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


def improve_prompt(test_case, judge, report_directory=None, *, review_fn=None,
                   on_update=None):
    """Evaluate baseline plus at most two explicitly approved revisions."""
    limit = settings.MAX_EVALUATION_RUNS
    review_fn = review_fn or review_prompt
    if type(limit) is not int or not 1 <= limit <= 3:
        raise ValueError("MAX_EVALUATION_RUNS must be between 1 and 3.")
    directory = Path(report_directory or PROJECT_ROOT / "reports" / "improvements")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"improvement-{uuid4().hex[:8]}.json"
    report = {
        "session": settings.IMPROVEMENT_SESSION,
        "generator_model": settings.GENERATOR_MODEL,
        "judge_model": settings.JUDGE_MODEL,
        "report_path": str(path),
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
            try:
                approved = review_fn(run["suggestion"])
            except (EOFError, OSError):
                # Captured/noninteractive stdin cannot approve another model call.
                report["stop_reason"] = "awaiting_review"
                break
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
    except KeyboardInterrupt:
        report["stop_reason"] = "interrupted"
        raise
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
