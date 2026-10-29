import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepeval.dataset import Golden
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.optimizer import PromptOptimizer
from deepeval.optimizer.algorithms import GEPA
from deepeval.prompt import Prompt

from models.model_client import generate_response, create_judge

judge = create_judge()

def model_callback(prompt: Prompt, golden: Golden) -> str:
    rendered_prompt = prompt.interpolate(input=golden.input)
    return generate_response(rendered_prompt)

optimizer = PromptOptimizer(
    model_callback=model_callback,
    metrics=[AnswerRelevancyMetric(model=judge)],
    optimizer_model=judge,
    algorithm=GEPA(
        iterations=5,
        pareto_size=2,
        reflection_model=judge,
        mutation_model=judge,
    ),
)

goldens = [
    Golden(input="What is an LLM?"),
    Golden(input="Explain retrieval augmented generation."),
]

best_prompt = optimizer.optimize(
    prompt=Prompt(
        text_template="Answer this question: {input}"
    ),
    goldens=goldens,
)

print(best_prompt.text_template)
print(optimizer.optimization_report)