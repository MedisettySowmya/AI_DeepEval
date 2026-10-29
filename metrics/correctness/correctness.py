from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from config import settings


KEY = "CorrectnessMetric"

REQUIRED_PARAMS = [
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
]


def create_metric(judge_model):
    return GEval(
        name="Correctness",
        criteria=(
            "Assess whether the actual output is factually correct compared with the expected output for the input. Accept equivalent wording. Penalize incorrect facts and contradictions; do not reward unsupported extra claims."
        ),
        evaluation_params=REQUIRED_PARAMS,
        model=judge_model,
        threshold=settings.METRIC_THRESHOLDS.get(
            KEY, settings.DEFAULT_METRIC_THRESHOLD
        ),
    )

