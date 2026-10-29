from deepeval.metrics import BiasMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "BiasMetric"

REQUIRED_PARAMS = builtin_required_params(BiasMetric)


def create_metric(judge_model):
    return BiasMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )

