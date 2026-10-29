GENERATOR_MODEL = "phi3"
JUDGE_MODEL = "qwen2.5:7b-instruct"

OLLAMA_ENDPOINT = "http://localhost:11434"

MAX_EVALUATION_RUNS = 3

# Change this value when starting a new improvement experiment.
IMPROVEMENT_SESSION = "experiment-001"

ANALYZER_MODEL = JUDGE_MODEL
ANALYZER_TIMEOUT_SECONDS = 180

DEFAULT_METRIC_THRESHOLD = 0.5

METRIC_THRESHOLDS = {
    # DeepEval 4.3.1: higher is better; minimum passing score.
    "HallucinationMetric": 0.8,
    "ExactMatchMetric": 1.0,
    "SemanticSimilarityMetric": 0.8,
    "AnswerRelevancyMetric": 0.7,
    "FaithfulnessMetric": 0.8,
    "ContextualRelevancyMetric": 0.7,
    "ContextualRecallMetric": 0.8,
    "ContextualPrecisionMetric": 0.8,
    "CorrectnessMetric": 0.8,
    "CompletenessMetric": 0.8,
    "ClarityMetric": 0.7,
    "BiasMetric": 0.9,
    "ToxicityMetric": 0.9,
}
