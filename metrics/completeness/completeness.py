from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from config import settings


KEY = "CompletenessMetric"

REQUIRED_PARAMS = [
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
]


def create_metric(judge_model):
    return GEval(
        name="Completeness",
        criteria=(
            "Assess whether the actual output covers all parts of the input and all essential information in the expected output. Accept concise paraphrases and do not require identical wording. Penalize missing required information, not harmless differences in style."
        ),
        evaluation_params=REQUIRED_PARAMS,
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )

