from deepeval.metrics import ContextualRelevancyMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "ContextualRelevancyMetric"

REQUIRED_PARAMS = builtin_required_params(ContextualRelevancyMetric)


def create_metric(judge_model):
    return ContextualRelevancyMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
