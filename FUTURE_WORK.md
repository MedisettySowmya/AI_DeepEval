# Future Work

Recorded: 25 October 2026

## Postponed: Three-model generation, evaluation, and prompt improvement

Status: Planned, not implemented. Revisit from 26 October 2026 when ready; no automatic task is scheduled.

### Objective

Keep the project simple while using three models with separate responsibilities:

1. Generate an answer.
2. Evaluate its quality with DeepEval.
3. Suggest an improved prompt when completed evaluations miss thresholds.

The user reviews and approves the suggested prompt before another generation. This is a multi-model pipeline, not a merged or jointly trained model.

### Proposed model assignments

| Role | Current setup | Proposed setup |
| --- | --- | --- |
| Answer generator | `phi3` | `gemma3:4b` |
| Evaluation judge | `qwen2.5:7b-instruct` | Keep `qwen2.5:7b-instruct` |
| Prompt improver | Active UI uses rule-based suggestions; separate LLM analyzer shares the judge setting | Connect `qwen3.5:4b` to the UI improvement workflow |

These are starting candidates, not proven best models for this dataset. Verify answer quality, judge output validity, prompt improvement quality, and runtime before adopting them.

Hardware inspected: 16 GB RAM and Intel Iris Xe graphics. Plan sequential execution and explicit model unloading between roles to limit memory use. Validate actual runtime memory and latency; download size does not equal RAM requirements.

### Intended workflow

```text
Prompt -> Gemma generates -> Qwen2.5 evaluates
                                  |
                     Completed scores miss thresholds
                                  |
                     Qwen3.5 proposes a better prompt
                                  |
                           Human approval
                                  |
                        Gemma generates again
```

Preserve the existing maximum of three evaluation runs. Handle missing evidence and evaluation errors separately from low scores. Preserve rule-based suggestions as a fallback if the prompt improver times out or returns invalid output.

### Installation tasks

- [ ] Install or update Ollama from https://ollama.com/download/windows.
- [ ] Open Ollama and reopen PowerShell.
- [ ] Check the version with `ollama --version`.
- [ ] Download or update the proposed models, one at a time:

```powershell
ollama pull gemma3:4b
ollama pull qwen2.5:7b-instruct
ollama pull qwen3.5:4b
ollama ls
```

- [ ] Test each model individually and unload it before testing the next:

```powershell
ollama run gemma3:4b "What is software testing? Answer in two sentences."
ollama stop gemma3:4b

ollama run qwen2.5:7b-instruct "Is this statement correct: Paris is the capital of France?"
ollama stop qwen2.5:7b-instruct

ollama run qwen3.5:4b "Rewrite this prompt to be clearer: Explain testing."
ollama stop qwen3.5:4b
```

### Code changes still required

- [ ] In `config/settings.py`, replace the generator setting and assign a separate analyzer model:

```python
GENERATOR_MODEL = "gemma3:4b"
JUDGE_MODEL = "qwen2.5:7b-instruct"
ANALYZER_MODEL = "qwen3.5:4b"
```

- [ ] Adapt the existing LLM analyzer in `prompt/prompt_analyzer.py` to the inputs and output expected by the active UI. Validate its JSON response and nonempty improved prompt; retain the configured timeout.
- [ ] Connect that analyzer to `ui/app.py`. The active UI currently uses `ui/prompt_analyzer.py` for rule-based suggestions. Preserve the existing review screen, approval step, and run limit.
- [ ] Add fallback handling for analyzer timeouts, unavailable models, and invalid responses.
- [ ] Implement and verify model unloading between roles where needed for this machine.
- [ ] Record the analyzer model and suggestion source in saved improvement reports.
- [ ] Update mocked UI checks for successful suggestions and fallback behavior.
- [ ] Run a live end-to-end case, checking judge JSON compatibility, memory usage, latency, and human approval before retries.
- [ ] Update README setup and workflow instructions.

Initial estimate discussed: roughly 80-150 changed lines across 4-5 files for the basic integration. Treat this as provisional; memory handling and compatibility fixes may increase the scope.

### Completion criteria

- All three models can run locally.
- The configured generator produces answers and the judge evaluates them successfully.
- Below-threshold completed results can trigger the third model's prompt suggestion.
- Suggestions appear in the existing review screen and require approval before reuse.
- Analyzer failures fall back gracefully, with the source recorded in the report.
- The workflow respects the run limit and works within available memory.

### Status at handoff

No model downloads or project implementation changes were performed during this planning discussion. Existing installed models were not inventoried. This file records the postponed work; changing settings alone will not activate the third model in the UI.

References:

- Ollama Windows setup: https://docs.ollama.com/windows
- Ollama CLI: https://docs.ollama.com/cli
- Generator candidate: https://ollama.com/library/gemma3:4b
- Judge: https://ollama.com/library/qwen2.5:7b-instruct
- Prompt improver candidate: https://ollama.com/library/qwen3.5:4b
