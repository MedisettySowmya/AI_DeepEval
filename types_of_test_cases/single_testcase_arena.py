import ollama

from deepeval import compare
from deepeval.metrics import ArenaGEval
from deepeval.models import OllamaModel
from deepeval.test_case import (
    ArenaTestCase,
    Contestant,
    LLMTestCase,
    SingleTurnParams,
)


class SingleTestCaseArena:

    def run_test(self):
        endpoint = "http://localhost:11434"
        client = ollama.Client(host=endpoint)

        # 1. One question shared by all three models
        prompt_input = (
            "Write a short paragraph explaining quantum computing "
            "to a 10-year-old."
        )

        # 2. Three generator models
        generator_models = [
            "phi3",
            "qwen2.5:7b-instruct",
        ]

        # 3. Generate answers and create contestants
        contestants = []

        for model_name in generator_models:
            response = client.chat(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt_input}
                ],
                options={"temperature": 0},
            )

            answer = response["message"]["content"]
            print(f"\n{model_name}:\n{answer}\n")

            contestants.append(
                Contestant(
                    name=model_name,
                    hyperparameters={"model": model_name},
                    test_case=LLMTestCase(
                        input=prompt_input,
                        actual_output=answer,
                    ),
                )
            )

        # 4. Group all three answers into one arena test case
        arena_test_case = ArenaTestCase(
            contestants=contestants
        )

        # 5. Select the model that will judge the answers
        judge = OllamaModel(
            model="qwen2.5:7b-instruct",
            base_url=endpoint,
            temperature=0,
        )

        arena_metric = ArenaGEval(
            name="Child Friendly Explanation",
            criteria=(
                "Choose the answer that explains quantum computing "
                "most accurately, simply, and engagingly for a 10-year-old. "
                "Penalize misleading explanations and exaggerated claims."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
            ],
            model=judge,
        )

        # 6. Compare the answers
        return compare(
            test_cases=[arena_test_case],
            metric=arena_metric,
        )


if __name__ == "__main__":
    test = SingleTestCaseArena()
    test.run_test()