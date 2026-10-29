from deepeval.metrics import ContextualPrecisionMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "ContextualPrecisionMetric"

REQUIRED_PARAMS = builtin_required_params(ContextualPrecisionMetric)


def create_metric(judge_model):
    return ContextualPrecisionMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
