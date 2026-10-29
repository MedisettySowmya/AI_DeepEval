from deepeval.test_case import LLMTestCase


# Re-export these names for existing callers while keeping data preparation
# in the dataset layer.
from dataset.case_fields import is_missing, prepare_fields


def calculation_details(metric, metric_key, fields):
    """Expose actual judge verdicts, not a second independent score."""
    if metric_key in {
        "CorrectnessMetric", "CompletenessMetric", "ClarityMetric",
        "BiasMetric", "ToxicityMetric",
    }:
        return None
    verdicts = getattr(metric, "verdicts", None)
    if metric_key == "ContextualRelevancyMetric":
        groups = getattr(metric, "verdicts_list", None)
        verdicts = None if groups is None else [v for group in groups for v in group.verdicts]
    if verdicts is None:
        return None
    passing = {"yes"}
    if metric_key == "AnswerRelevancyMetric" or (
        metric_key == "FaithfulnessMetric" and not getattr(metric, "penalize_ambiguous_claims", False)
    ):
        passing.add("borderline")
    items = {
        "HallucinationMetric": fields.get("context"),
        "AnswerRelevancyMetric": getattr(metric, "statements", None),
        "FaithfulnessMetric": getattr(metric, "claims", None),
        "ContextualPrecisionMetric": fields.get("retrieval_context"),
    }.get(metric_key) or []
    entries = []
    for index, verdict in enumerate(verdicts):
        label = str(verdict.verdict).strip().lower()
        item = getattr(verdict, "statement", None) or getattr(verdict, "expected_output", None)
        entries.append({
            "item": item or (str(items[index]) if index < len(items) else f"Judged item {index + 1}"),
            "verdict": label, "reason": getattr(verdict, "reason", None),
            "counts_as_pass": label in passing,
        })
    passed = sum(entry["counts_as_pass"] for entry in entries)
    formula = "(yes + borderline verdicts) / all verdicts" if "borderline" in passing else "yes verdicts / all verdicts"
    details = {
        "passing": passed, "total": len(entries), "verdicts": entries,
        "formula": formula,
        "empty_score": 0 if metric_key in {"ContextualPrecisionMetric", "ContextualRelevancyMetric", "ContextualRecallMetric"} else 1,
        "strict_mode": bool(getattr(metric, "strict_mode", False)),
    }
    if metric_key == "ContextualPrecisionMetric":
        relevant = 0
        terms = []
        for rank, entry in enumerate(entries, 1):
            if entry["counts_as_pass"]:
                relevant += 1
                terms.append(f"{relevant}/{rank}")
        details["formula"] = "Sum of precision at each relevant passage rank / number of relevant passages"
        details["equation"] = "(" + " + ".join(terms) + f") / {relevant}" if relevant else "No relevant passages: score = 0"
    return details


def execute_metric(row, fields, metric_module, judge_model):
    """Evaluate one metric, preserving skipped and error results."""
    result = {
        "id": row.get("id"),
        "metric": metric_module.KEY,
        "status": None,
        "score": None,
        "threshold": None,
        "passed": None,
        "reason": None,
        "error": None,
    }

    try:
        required = list(dict.fromkeys([
            "input",
            "actual_output",
            *[param.value for param in metric_module.REQUIRED_PARAMS],
        ]))

        missing = [
            field for field in required
            if is_missing(fields.get(field))
        ]

        if missing:
            result["status"] = "skipped"
            result["reason"] = "Missing required fields: " + ", ".join(missing)
        else:
            # Include only fields this metric needs.
            # Unrelated malformed data cannot affect this metric.
            case_fields = {
                field: fields[field] for field in required
            }

            test_case = LLMTestCase(**case_fields)
            metric = metric_module.create_metric(judge_model)
            result["threshold"] = metric.threshold
            metric.measure(test_case)

            result.update(
                status="completed",
                score=metric.score,
                passed=metric.is_successful(),
                reason=metric.reason,
                calculation=calculation_details(metric, metric_module.KEY, fields),
            )

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def execute_test_cases(rows, metric_modules, judge_model):
    results = []
    for row in rows:
        fields = prepare_fields(row)
        for metric_module in metric_modules:
            results.append(execute_metric(row, fields, metric_module, judge_model))
    return results
