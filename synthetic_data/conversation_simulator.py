from deepeval.dataset import ConversationalGolden, Persona, EvaluationDataset
from deepeval.models import OllamaModel
from deepeval.simulator import ConversationSimulator
from deepeval.test_case import Turn


# 1. Define one conversation scenario.
golden = ConversationalGolden(
    scenario="A customer wants to cancel their subscription.",
    expected_outcome=(
        "The chatbot explains the cancellation process "
        "and confirms the cancellation if the customer is eligible."
    ),
    persona=Persona(
        characteristics=(
            "A frustrated customer who wants clear answers "
            "and asks follow-up questions."
        )
    ),
)


# 2. Define a sample chatbot callback.
async def chatbot_callback(input: str) -> Turn:
    # Replace this placeholder with your actual chatbot call.
    return Turn(
        role="assistant",
        content=f"Chatbot response to: {input}",
    )


# 3. Use Ollama to generate the simulated customer's messages.
simulator = ConversationSimulator(
    model_callback=chatbot_callback,
    simulator_model=OllamaModel(
        model="qwen2.5:7b-instruct",
        base_url="http://localhost:11434",
        temperature=0,
    ),
)


# 4. Simulate up to five user-assistant exchanges.
test_cases = simulator.simulate(
    conversational_goldens=[golden],
    max_user_simulations=5,
)


# 5. Display the conversations.
for test_case in test_cases:
    print("Scenario:", test_case.scenario)
    print("Expected outcome:", test_case.expected_outcome)

    for turn in test_case.turns:
        print(f"{turn.role}: {turn.content}")


# 6. Save the conversations to JSON.
dataset = EvaluationDataset()

for test_case in test_cases:
    dataset.add_test_case(test_case)

saved_path = dataset.save_as(
    file_type="json",
    directory="./synthetic_data",
    file_name="conversation_dataset",
    include_test_cases=True,
)

print(f"Saved to: {saved_path}")