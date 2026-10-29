import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepeval.dataset import EvaluationDataset
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import StylingConfig
from deepeval.test_case import LLMTestCase

from models.model_client import create_judge, generate_response


# 1. Describe the questions to generate.
styling = StylingConfig(
    scenario="Beginners learning Python.",
    task="Answer basic Python programming questions.",
    input_format="Short questions in simple English.",
)

synthesizer = Synthesizer(
    model=create_judge(),
    styling_config=styling,
    async_mode=False,
)


# 2. Generate three question inputs.
print("Generating questions...", flush=True)

goldens = synthesizer.generate_goldens_from_scratch(
    num_goldens=3,
)


# 3. Answer each generated question.
dataset = EvaluationDataset()

for golden in goldens:
    test_case = LLMTestCase(
        input=golden.input,
        actual_output=generate_response(golden.input),
    )
    dataset.add_test_case(test_case)

    print("Question:", test_case.input)
    print("Answer:", test_case.actual_output)
    print()


# 4. Save the answered cases.
dataset.save_as(
    file_type="json",
    directory="./synthetic_data",
    file_name="generate_goldens_from_scratch",
    include_test_cases=True,
)