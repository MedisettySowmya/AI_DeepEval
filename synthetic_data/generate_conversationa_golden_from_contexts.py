import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepeval.synthesizer import Synthesizer
from models.model_client import create_judge


# 1. Reuse your existing Ollama model.
synthesizer = Synthesizer(
    model=create_judge(),
    async_mode=False,
)


# 2. Provide the policy for generating scenarios.
contexts = [
    [
        "Customers can cancel subscriptions through Account Settings, "
        "then Subscriptions, then Cancel Subscription.",
        "Cancellation takes effect at the end of the billing period.",
        "Customers retain access until the billing period ends.",
        "Payments for the current billing period are not refunded.",
    ]
]


# 3. Generate one conversational golden.
print("Generating a conversation scenario...", flush=True)

goldens = synthesizer.generate_conversational_goldens_from_contexts(
    contexts=contexts,
    include_expected_outcome=True,
    max_goldens_per_context=1,
)


# 4. Display the result.
for golden in goldens:
    print("Scenario:", golden.scenario)
    print("Expected outcome:", golden.expected_outcome)


# 5. Save it.
synthesizer.save_as(
    file_type="json",
    directory="./synthetic_data",
    file_name="generate_conversational_goldens_from_contexts",
)
