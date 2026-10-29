# DeepEval Hallucination Testing Framework

A Python framework for generating local LLM responses and evaluating their quality with **PyTest**, **DeepEval 4.3.1**, and **Ollama**. Excel workbooks supply test inputs and evaluation evidence. Results are printed in the terminal and saved as JSON for inspection.

## How to Run the Application

Use the browser application to select or enter a test case, evaluate it, and review the results.

### First-time setup

Install Python and Ollama as described in [Windows prerequisites](#windows-prerequisites). Open PowerShell and run:

```powershell
Set-Location E:\AI_DeepEval

# Create the environment only if .venv does not already exist
python -m venv .venv

# Install the project dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Download the generator and judge models
ollama pull phi3
ollama pull qwen2.5:7b-instruct
```

Replace `E:\AI_DeepEval` with your project location if different. The commands use the virtual environment's interpreter directly, so activation is optional.

### Start the application

1. Start the Ollama Windows application. If it is not already serving requests, run this in a separate PowerShell window and leave it open:

   ```powershell
   ollama serve
   ```

2. In your project PowerShell window, launch the browser application:

   ```powershell
   Set-Location E:\AI_DeepEval
   .\.venv\Scripts\python.exe -m ui.app
   ```

3. Open **http://127.0.0.1:8000** in your browser.
4. Select a workbook and test case, or create a manual case. Review the inputs, start evaluation, and inspect the scores and reasons. Approve any proposed revision before re-running it.
5. Press `Ctrl+C` in the application terminal to stop the server.

For more detail, see [browser evaluation and prompt improvement](#optional-browser-evaluation-and-prompt-improvement). To execute automated tests, see the separate [Running tests](#running-tests) section.

## Overview and objectives

The project helps assess hallucination, answer relevance, grounding, retrieval quality, correctness, completeness, clarity, bias, and toxicity. It separates response generation from judging and preserves missing-data and execution errors alongside successful measurements.

An optional browser console supports editable cases, human-approved prompt revisions, and comparison of evaluation runs. The existing pytest workflow processes every Excel row with its own console improvement loop and approval prompts.

### Verified configuration

| Item | Current implementation |
| --- | --- |
| Generator | Ollama `phi3` |
| Judge | Ollama `qwen2.5:7b-instruct` (not `phi3`) |
| Ollama endpoint | `http://localhost:11434` |
| Main dataset | `dataset/test_cases_datasets.xlsx` |
| Dependency specification | `requirements.txt`; only DeepEval is explicitly pinned |
| Default test discovery | `tests/`, configured in `pytest.ini` |
| Reporting | Terminal output and custom JSON reports |
| HTML / Allure | Neither configured nor listed in `requirements.txt` |
| Azure DevOps | No `azure-pipelines.yml` or other pipeline YAML found in the inspected project files |

The requested `hallucination_dataset.xlsx` is not present or referenced by the active test. The existing workbook has one sheet, `Prompt`, with one data row and columns `ID`, `Input`, `Context`, `retrieval_context`, and `Ground_Truth`. For console evaluation, `Context` now supplies both trusted reference evidence and the expected answer; `retrieval_context` supplies the generator. Review older workbook contents to ensure `Context` contains the intended ground truth.

## Architecture and execution workflow

```text
Excel workbook -> dataset_loader -> pytest parameterized cases
                                       |
                                prompt_builder
                                       |
                               Ollama generator
                                       |
                         evaluate -> execution engine
                                       |
                       enabled metrics -> Ollama judge
                                       |
                         terminal output + JSON report
```

1. `tests/test_metrics.py` loads every sheet of the configured workbook at collection time and creates one parameterized test per row.
2. `dataset/case_fields.py` normalizes each case: `Context` becomes reference evidence and the expected answer; only `retrieval_context` supplies generation evidence. `prompt/prompt_builder.py` builds the prompt.
3. `models/model_client.py` generates an answer using `phi3` with temperature `0` and constructs the separate DeepEval Ollama judge with temperature `0`.
4. `evaluate/evaluate.py` selects the 11 modules in `config/metrics.py`.
5. `evaluate/execute/e2e.py` maps fields into `LLMTestCase`, checks each metric's requirements, measures it, and preserves its score, threshold, pass flag, reason, or error. Cases and metrics execute sequentially in this engine.
6. `evaluate/improvement_runner.py` offers console approval for prompt revisions when completed scores miss thresholds. Each row has at most three total runs. Passing, rejected, incomplete, or failed cases finish independently so processing can continue to the next row.
7. `report/report_generator.py` saves the selected best complete run (or latest run if none is complete), plus the full improvement history, after each case and again during fixture teardown.

`tests/test_execution.py` checks field conversion, dataset mapping, and result handling using mocks rather than live model calls.

## Windows prerequisites

- Python with the `venv` module and pip. The inspected environment uses Python **3.14.6**; the repository does not declare a minimum version or a supported-version matrix. Compatibility with other versions requires confirmation.
- PowerShell and a local copy of this project.
- Ollama for Windows, with enough memory and disk space to run both configured models. The project specifies no hardware minimum.
- Internet access for initial Python package and model downloads.

## Installation and virtual environment

Run these commands from the repository root. The path below is the inspected location; substitute your own checkout location if different.

1. Open PowerShell and enter the project directory:

   ```powershell
   Set-Location E:\AI_DeepEval
   python --version
   ```

2. Create a virtual environment if `.venv` does not already exist:

   ```powershell
   python -m venv .venv
   ```

3. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the explicit interpreter instead; activation is optional:

   ```powershell
   .\.venv\Scripts\python.exe --version
   ```

4. Install the declared dependencies using that interpreter:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m pip check
   ```

   `requirements.txt` contains `deepeval==4.3.1`, `ollama`, `pandas`, `openpyxl`, and `pytest`. The remaining packages are unpinned, so fresh installations may resolve different versions.

5. Confirm the interpreter and imports:

   ```powershell
   .\.venv\Scripts\python.exe -c "import sys, deepeval, ollama, pandas, openpyxl, pytest; print(sys.executable)"
   ```

To leave an activated environment, run `deactivate`.

## Ollama setup and verification

1. Install and start Ollama using the official [Windows instructions](https://docs.ollama.com/windows). Reopen PowerShell if the `ollama` command is not yet on PATH.
2. Download the exact models configured in `config/settings.py`:

   ```powershell
   ollama pull phi3
   ollama pull qwen2.5:7b-instruct
   ollama ls
   ```

3. If Ollama is not already running, start it in a separate terminal and leave it running:

   ```powershell
   ollama serve
   ```

   Do not start a second server if the Windows application already serves port `11434`. These commands follow the official [Ollama CLI reference](https://docs.ollama.com/cli).

4. Verify the configured endpoint and available models:

   ```powershell
   Invoke-RestMethod -Uri http://localhost:11434/api/tags
   ```

   The response should list both models. `/api/tags` is Ollama's [local-model listing endpoint](https://github.com/ollama/ollama/blob/main/docs/api.md).

5. Optionally exercise the project's judge constructor:

   ```powershell
   .\.venv\Scripts\python.exe -c "from models.model_client import create_judge; print(create_judge())"
   ```

   Construction alone does not prove that a judge inference succeeds. Running an evaluation verifies the complete integration.

### Settings, environment variables, and API keys

The active evaluation path reads model names, endpoint, and thresholds from `config/settings.py`. It does not require an API key, `.env` file, or project-defined environment variables. Both active model clients explicitly use Ollama.

The optional UI reads `EVAL_UI_PORT` (default `8000`):

```powershell
$env:EVAL_UI_PORT = "8001"
.\.venv\Scripts\python.exe -m ui.app
```

`singletestcasemetrics.py` is a separate demonstration that constructs `HallucinationMetric(threshold=0.5)` without the project's Ollama judge. Its default provider and any required credentials need confirmation before use. It is not part of the configured pytest suite; do not assume it shares the local-model setup. Never put credentials in source files or reports.

## Dataset format

`dataset/dataset_loader.py` reads all sheets, uses each sheet name as the case category, trims text, and converts empty cells to empty strings. Column names are case-sensitive. The loader does not enforce a workbook schema; missing fields become empty values and individual metrics may skip.

| Excel column | Loaded field / purpose | Requirement |
| --- | --- | --- |
| `ID` | Case identifier | Optional; fallback is `<sheet_name>:<zero-based row position>` |
| `Input` | `input`: question | Needed for evaluation; blank input produces a skipped case |
| `Context` | Ground truth; used as reference evidence and expected answer | Required by hallucination, correctness, completeness, contextual recall, and contextual precision |
| `retrieval_context` | Retrieved passages supplied to the generator | Required by faithfulness and retrieval metrics |
| `Pattern` | Metadata | Optional |

The loader still reads older `Prompt_Context`, `Reference_Context`, and `Ground_Truth` columns, but the console and UI normalize cases to the two-field convention above. `Context` takes precedence over the older reference and expected-answer values, including when blank. It is never used as a generation fallback when retrieved passages are missing. Original workbooks are not modified.

`actual_output` is generated at runtime. Nonempty context strings become single-item lists for DeepEval; the loader does not split an Excel cell into multiple passages.

To exercise every enabled metric, provide `Input`, `Context`, and `retrieval_context`, plus a successfully generated answer. Review evidence quality as well as field presence. Missing required evidence is reported as skipped and stops improvement for that row.

## Metrics and thresholds

The following metrics are enabled in `config/metrics.py`. Thresholds come from `config/settings.py`; the fallback for a missing threshold entry is `0.5`. Every metric requires `input` and `actual_output` because the execution engine enforces both.

| Metric key | Evaluation purpose | Threshold | Additional fields required |
| --- | --- | --- | --- |
| `HallucinationMetric` | Agreement with reference evidence | 0.8 | `Context` |
| `AnswerRelevancyMetric` | Whether the response addresses the question | 0.7 | None |
| `FaithfulnessMetric` | Support for response claims in retrieved evidence | 0.8 | `retrieval_context` |
| `ContextualRelevancyMetric` | Relevance of retrieved evidence to the question | 0.7 | `retrieval_context` |
| `ContextualRecallMetric` | Coverage of expected information by retrieved evidence | 0.8 | `retrieval_context`, `Context` |
| `ContextualPrecisionMetric` | Ranking of relevant retrieved passages | 0.8 | `retrieval_context`, `Context` |
| `CorrectnessMetric` | Factual agreement with the expected answer; custom GEval criteria | 0.8 | `Context` |
| `CompletenessMetric` | Coverage of required information; custom GEval criteria | 0.8 | `Context` |
| `ClarityMetric` | Organization, precision, and understandable wording; custom GEval criteria | 0.7 | None |
| `BiasMetric` | Bias evaluation | 0.9 | None |
| `ToxicityMetric` | Toxicity evaluation | 0.9 | None |

The project targets DeepEval **4.3.1** and treats scores as higher-is-better, with `score >= threshold` passing. The engine stores the result of `metric.is_successful()` rather than implementing a separate comparison. In particular, do not apply older lower-is-better hallucination, bias, or toxicity interpretations without checking the pinned implementation.

`ExactMatchMetric` (1.0) and `SemanticSimilarityMetric` (0.8) appear only as threshold entries. They have no enabled metric modules and are not evaluated. The `hallucination` and `exact_match` pytest marker declarations also do not activate metrics or mark the current tests.

## Running tests

Run all commands from the project root. Explicit interpreter paths avoid accidentally selecting a different Python installation.

### Default configured suite

```powershell
.\.venv\Scripts\python.exe -m pytest
```

This collects live Excel evaluation and the offline execution/console-runner checks. It includes live model evaluation and requires the workbook and Ollama. `pytest.ini` supplies verbose output, strict markers, and `--capture=tee-sys`.

### Individual files and cases

```powershell
# Evaluate and improve every Excel row; -s enables console approval input
.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py -s

# Mocked execution and loader checks
.\.venv\Scripts\python.exe -m pytest tests/test_execution.py

# Inspect actual parameterized node IDs without generating answers
.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py --collect-only

# Run one execution-engine check
.\.venv\Scripts\python.exe -m pytest tests/test_execution.py::test_context_text_conversion
```

To select a workbook row, copy its exact node ID from collection output and pass it in quotes to the same pytest command. IDs come from workbook `ID` values or loader fallbacks; do not assume a particular numeric ID.

### Optional UI checks and all Python test directories

`ui/checks/` is outside the default `testpaths`. Select it explicitly:

```powershell
.\.venv\Scripts\python.exe -m pytest ui/checks
.\.venv\Scripts\python.exe -m pytest ui/checks/test_app.py
.\.venv\Scripts\python.exe -m pytest ui/checks/test_improvement.py

# All Python test directories, including live workbook evaluation
.\.venv\Scripts\python.exe -m pytest tests ui/checks
```

The UI checks use mocked evaluation. `ui/checks/check_review.cjs` is a separate browser-check artifact, not a pytest test; this README does not prescribe an unverified Node setup.

## Result statuses and reporting

| Metric status | Meaning |
| --- | --- |
| `completed` | Measurement finished; inspect `passed` to determine whether the threshold was met |
| `skipped` | Required fields were missing; score and pass flag remain unset |
| `error` | Metric initialization or measurement raised an exception; inspect `error` |

Case status is `error` if any metric errors, otherwise `completed` if any metric completes, otherwise `skipped`. Missing input skips the case; judge initialization or generation failures produce case errors.

**A pytest PASS does not establish that quality thresholds passed.** `tests/test_metrics.py` records exceptions and evaluation outcomes without asserting `passed`. Its skipped/error labels are report fields, not calls to `pytest.skip()` or `pytest.fail()`. A below-threshold metric can belong to a completed case and a passing pytest test. Read the JSON `passed`, `status`, and `error` fields to assess quality. Collection errors, assertion failures in other tests, and report-writing errors can still fail pytest.

| Output | Location and contents |
| --- | --- |
| Terminal | Case question, contexts, ground truth, output, raw metric scores, targets, reasons, pass flags, and errors |
| Normal evaluation JSON | `reports/<run_id>.json`; run ID combines UTC time and a random suffix |
| Normal report metadata | Models, DeepEval version, timestamps, duration at teardown, case/metric status counts, case details, and results |
| Metric details | Score, threshold, pass flag, reason/error, and judge verdict breakdowns where exposed |
| Per-case improvement history (console and UI) | `reports/improvements/improvement-<suffix>.json`; prompts, answers, feedback, reviews, run comparisons, and stop reason |

The report writer uses a temporary file and atomic replacement. Reports can contain complete prompts, source evidence, and generated answers; review their contents before sharing. `execution_reports/` contains existing artifacts but is not the configured output directory of either active entry point.

No pytest-html or Allure dependency, plugin configuration, or report command is configured. HTML/Allure generation instructions are therefore intentionally omitted; installing those tools would be a separate project change.

## Optional browser evaluation and prompt improvement

```powershell
.\.venv\Scripts\python.exe -m ui.app
```

Open `http://127.0.0.1:8000` (or the configured UI port). Select a workbook from `dataset/*.xlsx` and a row, or enter a manual case. Review the editable inputs, run evaluation, and inspect scores and reasons. The UI uses a shared context field for generation and judging, unlike the separate contexts in the pytest Excel path.

If completed results miss thresholds, the UI offers rule-based suggestions and requires approval before generating a revised response. It uses all enabled metrics and permits up to three total runs (`MAX_EVALUATION_RUNS = 3`): baseline plus two approved revisions. Missing-data skips or evaluation errors stop improvement. It also stops when all metrics pass, review is rejected, or the run limit is reached.

Best complete runs are ranked by number of passing metrics, then minimum score, then average score; earlier runs win ties. Editing evaluation inputs changes the experiment and affects comparison validity. UI edits do not rewrite the workbook. Stop the server with `Ctrl+C`.

`PROMPT_IMPROVER.md` provides further UI guidance, but its references to “both metrics” reflect an older two-metric setup. The current source enables 11. Legacy terminal improvement/reviewer modules are retained for reference and are not used by the active pytest or UI entry points.

## Project directory structure

The following reflects the inspected project. Python package `__init__.py` files, bytecode, IDE state, caches, temporary test directories, and individual generated report names are omitted for readability.

```text
AI_DeepEval/
|-- README.md
|-- requirements.txt
|-- pytest.ini
|-- PROMPT_IMPROVER.md
|-- singletestcasemetrics.py       # Standalone default-provider demonstration
|-- config/
|   |-- settings.py               # Models, endpoint, thresholds, run limit
|   `-- metrics.py                # Enabled metric modules
|-- dataset/
|   |-- dataset_loader.py
|   `-- test_cases_datasets.xlsx
|-- models/
|   `-- model_client.py           # Ollama generation and judge construction
|-- prompt/
|   |-- prompt_builder.py
|   `-- prompt_analyzer.py        # Separate LLM analyzer, not active UI analyzer
|-- metrics/
|   |-- answer_relevency/answer_relevency.py
|   |-- hallucination/hallucination.py
|   |-- faithfulness/faithfulness.py
|   |-- contextual_relevancy/contextual_relevancy.py
|   |-- contextual_recall/contextual_recall.py
|   |-- contextual_precision/contextual_precision.py
|   |-- correctness/correctness.py
|   |-- completeness/completeness.py
|   |-- clarity/clarity.py
|   |-- bias/bias.py
|   `-- toxicity/toxicity.py
|-- evaluate/
|   |-- evaluate.py
|   |-- execute/e2e.py            # Field validation and per-metric execution
|   `-- improvement_runner.py     # Per-row console improvement workflow
|-- human_review/
|   `-- reviewer.py               # Console approve/edit/reject prompts
|-- report/
|   `-- report_generator.py
|-- tests/
|   |-- test_metrics.py           # Live dataset evaluation
|   `-- test_execution.py         # Mocked engine and loader checks
|-- ui/
|   |-- app.py                    # Local HTTP server and approved improvement loop
|   |-- index.html
|   |-- prompt_analyzer.py        # Active rule-based suggestions
|   |-- templates/improvement.txt
|   `-- checks/
|       |-- test_app.py
|       |-- test_improvement.py
|       `-- check_review.cjs
|-- reports/
|   `-- improvements/
`-- execution_reports/            # Existing artifacts
    `-- improvements/
```

## Troubleshooting

| Symptom | Checks and resolution |
| --- | --- |
| `ModuleNotFoundError` | Re-run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Use that same interpreter to execute pytest. `openpyxl` is needed for Excel loading. |
| IDE imports fail but terminal works | Select `E:\AI_DeepEval\.venv\Scripts\python.exe` as the IDE interpreter, adjusting for your checkout. Confirm with `import sys; print(sys.executable)`. |
| Activation script blocked | Use `.\.venv\Scripts\python.exe` directly; changing machine-wide execution policy is unnecessary. |
| Ollama connection refused / timeout | Verify Ollama is running, query `/api/tags`, and compare the endpoint with `config/settings.py`. Check local firewall/proxy settings and model resource usage. Avoid duplicate servers on port `11434`. |
| Model not found | Pull both exact configured model tags and verify them with `ollama ls`. A downloaded generator does not also supply the judge. |
| HTTP 429 | Inspect the recorded exception and identify the responding provider or proxy. The active project uses local Ollama; it has no project-level rate-limit retry policy. A 429 is not evidence that this path needs an OpenAI key. If a separate provider/default-provider demo is used, check its actual limits and retry guidance before rerunning; reduce request frequency and respect any retry delay returned. |
| Dataset missing / collection fails | Confirm `dataset/test_cases_datasets.xlsx` exists. It is read during test collection, before fixtures run. Check workbook readability and close Excel if a file-lock error occurs. |
| Hallucination is skipped | Supply nonempty `Context` ground truth in the workbook. Console normalization maps it to judge reference evidence and the expected answer. |
| Other metrics skipped | Read `reason` for the missing field names and compare with the metric table. Blank ground truth or retrieval evidence prevents dependent metrics from running. |
| Pytest passes but evaluations fail | Inspect `reports/*.json`; the live evaluation test records results without enforcing threshold assertions. Check metric `passed` and `error`, not just the pytest exit status. |
| Judge output parsing / execution error | Inspect the per-metric error, verify the pinned DeepEval version and configured judge, and reproduce with one collected case. Structured-output compatibility and adequate model resources matter; do not silently switch providers. |
| No report or report-writing failure | Ensure `reports/` is writable. Errors during collection happen before the reporting fixture starts; no new report is expected then. |
| UI port already in use | Stop the existing UI server or set `EVAL_UI_PORT` to another free port before starting it. |

## CI/CD and details requiring confirmation

No Azure DevOps pipeline is present in the inspected project files, so there is no verified Azure execution or artifact-publication procedure to document.

Confirm these items with the maintainer before relying on them:

- Whether the intended judge should remain `qwen2.5:7b-instruct` or be changed to the requested `phi3`.
- Whether the dataset should be renamed to `hallucination_dataset.xlsx`; the current code uses `test_cases_datasets.xlsx`.
- The approved reference evidence to add for hallucination measurement.
- Supported Python versions and hardware sizing beyond the inspected local environment.
- Whether quality failures should eventually fail CI, and whether HTML/Allure or Azure DevOps should be added.
- Provider configuration and credential requirements for the standalone demonstration, if it is to be supported.

## Contributing and maintenance

1. Review the loader, metric modules, settings, and reporting contract before making changes.
2. Keep trusted reference evidence separate from generation evidence in Excel-driven evaluations. Use stable IDs and do not commit sensitive source data or credentials.
3. When adding a metric, define its key and factory; enable it in `config/metrics.py`, add its threshold, and update this README. For built-in metrics, derive `REQUIRED_PARAMS` with `metrics.requirements.builtin_required_params()` instead of copying the library's field list. Custom `GEval` metrics still declare their own evaluation fields.
4. Run `tests/test_execution.py` and `ui/checks` for relevant engine or UI changes. Run live dataset evaluation when changing models, metric behavior, or prompts, with Ollama available.
5. Compare report scores, skips, and errors as well as pytest outcomes. Record model and dependency versions when assessing changes.
6. Review DeepEval release behavior before changing the pinned version, especially score direction, thresholds, and judge verdict formats. The requirements helper isolates access to DeepEval 4.3.1's internal `_required_params` attribute; verify that contract on upgrades. Run `tests/test_evaluation_contract.py` to check completed results, skips, and isolated errors. Refresh documentation when configuration changes.

No contribution policy, license file, or repository remote was supplied in the inspected root. Contribution submission and licensing details require maintainer confirmation.
