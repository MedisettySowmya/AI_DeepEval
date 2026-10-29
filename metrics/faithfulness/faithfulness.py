from deepeval.metrics import FaithfulnessMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "FaithfulnessMetric"

REQUIRED_PARAMS = builtin_required_params(FaithfulnessMetric)


def create_metric(judge_model):
    return FaithfulnessMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
