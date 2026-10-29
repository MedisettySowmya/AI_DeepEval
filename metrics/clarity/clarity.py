from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from config import settings


KEY = "ClarityMetric"

REQUIRED_PARAMS = [
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
]


def create_metric(judge_model):
    return GEval(
        name="Clarity",
        criteria=(
            "Assess whether the actual output is clear and understandable for the input. Reward logical organization, precise wording, and explanations appropriate to the question. Penalize confusing phrasing, ambiguity, and unnecessary repetition. Do not judge factual correctness or completeness."
        ),
        evaluation_params=REQUIRED_PARAMS,
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )

