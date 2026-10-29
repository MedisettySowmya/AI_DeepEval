from deepeval.models import OllamaEmbeddingModel
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import ContextConstructionConfig

from config import settings
from models.model_client import create_judge

#.\.venv\Scripts\python.exe -m pip install chromadb langchain-core langchain-community langchain-text-splitters docx2txt
# Install the tokenizer dependency
#.\.venv\Scripts\python.exe -m pip install tiktoken==0.14.0
# Download and cache the tokenizer vocabulary
#.\.venv\Scripts\python.exe -c "import tiktoken; tiktoken.get_encoding('gpt2'); print('Tokenizer ready')"
# Download the Ollama embedding model
#ollama pull nomic-embed-text
# Run document-based golden generation
#.\.venv\Scripts\python.exe -X utf8 -u -m synthetic_data.generate_goldens_from_docs
#.\.venv\Scripts\python.exe -X utf8 -u -m synthetic_data.generate_goldens_from_docs
# 1. Reuse your existing generation model.
model = create_judge()

synthesizer = Synthesizer(
    model=model,
    async_mode=False,
)
document_paths=["./docs/Python_DeepEval_AI_Hallucination_Notes.docx"]

# 2. Configure local document processing.
context_config = ContextConstructionConfig(
    critic_model=model,
    embedder=OllamaEmbeddingModel(
        model="nomic-embed-text",
        base_url=settings.OLLAMA_ENDPOINT,
    ),
    max_contexts_per_document=1,
    max_context_length=1,
    chunk_size=512,
)


# 3. Generate questions and expected answers.
print("Generating from document...", flush=True)

goldens = synthesizer.generate_goldens_from_docs(
    document_paths=document_paths,
    include_expected_output=True,
    max_goldens_per_context=2,
    context_construction_config=context_config,
)


# 4. Display and save.
for golden in goldens:
    print("Question:", golden.input)
    print("Expected answer:", golden.expected_output)
    print()

synthesizer.save_as(
    file_type="json",
    directory="./synthetic_data",
    file_name="generate_goldens_from_docs",
)