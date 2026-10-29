# Future plan: synthetic evaluation dataset generation

This is a future implementation plan. No generation functionality has been implemented as part of saving this document.

## Workflow

Trusted source text -> generated questions and reference answers -> validation -> human review -> Excel dataset -> existing evaluation.

## 1. Initial scope

Start with trusted text passages and generate 10–20 cases. Cover factual questions, paraphrases, and questions requiring multiple facts. Add PDF ingestion and more complex scenarios later.

## 2. Dataset format

| Column | Content |
| --- | --- |
| ID | Unique case identifier |
| Input | Generated question |
| Context | Verified reference answer used for judging |
| retrieval_context | Source passage supplied to the answering model |
| Pattern | Factual, paraphrase, or multi-fact scenario |

The current project normalizes Context into both reference evidence and expected answer. Preserve this convention initially and retain the original source separately for auditing.

## 3. Proposed components

- synthetic/generator.py: generate candidate cases through Ollama.
- synthetic/prompts.py: grounded question-and-answer generation instructions.
- synthetic/validator.py: structure, required fields, duplicates, and source-support checks.
- synthetic/exporter.py: export approved cases to a new workbook.
- synthetic/cli.py: terminal workflow.

Keep synthetic generation separate from response generation and evaluation.

## 4. Structured generation

Request JSON containing the question, reference answer, source passage identifier, supporting quotation, and scenario type. Require source-supported answers. Configure the generation model, temperature, case count, and retry limits separately from existing response settings.

## 5. Validation and review

- Validate structure and required fields.
- Remove exact and near-duplicate questions.
- Verify that supporting quotations exist in the source.
- Check whether evidence supports each reference answer.
- Flag ambiguous or unsupported cases for review.

Model-based checks can assist review; generated answers remain candidates until reviewed.

## 6. Export and evaluation

Save approved cases to a separate workbook, such as dataset/synthetic_cases.xlsx. Save source information, generation settings, and rejection reasons in companion JSON. Load approved cases through the existing loader and run the usual response-generation and evaluation pipeline.

## 7. Pilot verification

Check malformed responses, duplicate removal, missing evidence, retry limits, and Excel round-trip compatibility. Manually review the first 10–20 cases. Evaluate a few through the existing framework before increasing volume.

## Implementation order

Terminal generation -> validation -> review and export -> existing evaluation -> browser UI integration.

First milestone: a small, reviewed synthetic workbook that the current evaluator can consume successfully.
