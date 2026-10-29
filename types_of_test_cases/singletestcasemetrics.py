from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase
from deepeval import evaluate


class HallucinationTest:

    def __init__(self):
        self.context = [
            "A man with blond-hair, and a brown shirt drinking out of a public water fountain."
        ]
        self.actual_output = "A blond drinking water in public."
        self.input = "What was the blond doing?"
        self.metric = HallucinationMetric(threshold=0.5)

    def run_test(self):
        test_case = LLMTestCase(
            input=self.input,
            actual_output=self.actual_output,
            context=self.context
        )

        evaluate(
            test_cases=[test_case],
            metrics=[self.metric],
        )


if __name__ == "__main__":
    test = HallucinationTest()
    test.run_test()
