from metrics.hallucination import hallucination
from metrics.answer_relevency import answer_relevency
from metrics.faithfulness import faithfulness
from metrics.contextual_relevancy import contextual_relevancy
from metrics.contextual_recall import contextual_recall
from metrics.contextual_precision import contextual_precision
from metrics.correctness import correctness
from metrics.completeness import completeness
from metrics.clarity import clarity
from metrics.bias import bias
from metrics.toxicity import toxicity


ENABLED_METRICS = [
    hallucination,
    answer_relevency,
    faithfulness,
    contextual_relevancy,
    contextual_recall,
    contextual_precision,
    correctness,
    completeness,
    clarity,
    bias,
    toxicity,
]


