import ollama
from deepeval.models import OllamaModel

from config import settings


def generate_response(prompt):
    client = ollama.Client(host=settings.OLLAMA_ENDPOINT)

    response = client.chat(
        model=settings.GENERATOR_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        options={"temperature": 0},
    )

    return response["message"]["content"]


def create_judge():
    return OllamaModel(
        model=settings.JUDGE_MODEL,
        base_url=settings.OLLAMA_ENDPOINT,
        temperature=0,
    )