from deepeval.models import OllamaModel
from deepeval.synthesizer import Synthesizer

model = OllamaModel(
    model="qwen2.5:7b-instruct",
    base_url="http://localhost:11434",
    temperature=0,
)

synthesizer = Synthesizer(model=model)

goldens = synthesizer.generate_goldens_from_contexts(
     contexts=[
        [
            "SkyNova AI was founded by Eng. Mishaal Al-Qarni in 2009.",
            "SkyNova AI provides AI-related services."
        ],
        [
            "Python is a programming language.",
            "Python supports automation, data analysis, and web development."
        ]
    ],
    include_expected_output=True,
    max_goldens_per_context=3
)
print(f"Generated goldens: {len(goldens)}")

synthesizer.save_as(
    file_type="json",
    directory="./synthetic_data",
    file_name="llm_test_dataset"
)

