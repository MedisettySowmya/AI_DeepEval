from deepeval.metrics import ToxicityMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "ToxicityMetric"

REQUIRED_PARAMS = builtin_required_params(ToxicityMetric)


def create_metric(judge_model):
    return ToxicityMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )

