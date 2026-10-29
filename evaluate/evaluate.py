from config.metrics import ENABLED_METRICS
from .execute import execute_test_cases


def evaluate(test_cases, judge_model):
    if not isinstance(test_cases, list):
        raise TypeError("test_cases must be a list.")

    if any(not isinstance(row, dict) for row in test_cases):
        raise TypeError("Each test case must be a dictionary.")

    if not ENABLED_METRICS:
        raise ValueError("No metrics are enabled.")

    return execute_test_cases(
        rows=test_cases,
        metric_modules=ENABLED_METRICS,
        judge_model=judge_model,
    )
