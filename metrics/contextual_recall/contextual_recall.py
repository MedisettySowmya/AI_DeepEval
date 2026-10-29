from deepeval.metrics import ContextualRecallMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "ContextualRecallMetric"

REQUIRED_PARAMS = builtin_required_params(ContextualRecallMetric)


def create_metric(judge_model):
    return ContextualRecallMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
