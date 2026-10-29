from deepeval.metrics import AnswerRelevancyMetric
from metrics.requirements import builtin_required_params

from config import settings


KEY = "AnswerRelevancyMetric"

REQUIRED_PARAMS = builtin_required_params(AnswerRelevancyMetric)


def create_metric(judge_model):
    return AnswerRelevancyMetric(
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )
