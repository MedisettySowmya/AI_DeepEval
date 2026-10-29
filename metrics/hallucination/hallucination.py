from deepeval.metrics import HallucinationMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "HallucinationMetric"

REQUIRED_PARAMS = builtin_required_params(HallucinationMetric)


def create_metric(judge_model):
    return HallucinationMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
