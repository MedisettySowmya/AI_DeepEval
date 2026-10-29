# Prompt improvement

## Console: every Excel row

Use the existing evaluation command from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py -s
```

The existing parameterization processes every row from every sheet in
`dataset/test_cases_datasets.xlsx`. No separate bulk command is required.

Each row follows this sequence:

1. Normalize `Context` as ground truth and expected answer; use `retrieval_context` as the model's supporting passages.
2. Generate once and evaluate all metrics enabled in `config/metrics.py`.
3. If all completed metrics pass, finish the row.
4. If completed metrics miss thresholds, print feedback and rule-based prompt recommendations.
5. Ask for approval: `a` approves, `e` edits the complete prompt (finish with `END`), and `r` ends improvement for that row.
6. Rerun only after approval, up to `MAX_EVALUATION_RUNS` total runs (currently 3, including baseline).
7. Save the row's results and continue to the next Excel row.

The baseline is generated and evaluated only once. Rankings use all enabled
metrics: passing count, then minimum score, then average score; earlier runs win
ties. Missing/skipped metrics and evaluation errors stop improvement for that row
and are preserved in reports. They do not prevent subsequent rows from running.

Use `-s` so pytest allows terminal input. If stdin is unavailable, the proposal is
saved as `awaiting_review`; there is no automatic approval. Ctrl+C saves the
current improvement history and interrupts the batch. Restarting starts new runs,
not a resume of the interrupted experiment.

Suggestions currently come from rules, not the separate LLM prompt analyzer.
Prompt changes cannot supply missing source facts or fix retrieval by themselves.

## Reports

Each row gets `reports/improvements/improvement-<suffix>.json` containing all
prompts, answers, metrics, suggestions, approvals, and the stop reason.

The main `reports/<run-id>.json` contains every processed row. Each row includes
its full `improvement` history and `selected_run`. Its top-level prompt, answer,
and metric results all come from the best complete run, or the latest run if none
completed. An error in a later attempt remains an error in the case summary even
when an earlier complete run supplies the selected scores.

## Browser: one selected case

```powershell
.\.venv\Scripts\python.exe -m ui.app
```

Open http://127.0.0.1:8000 and select or enter one case. Context is the ground truth;
Retrieved context contains the passages supplied to the model. The browser uses
its existing edit and approval controls. Console improvements do not require
starting this server. Neither workflow changes the source workbook.

## Relevant code

- `tests/test_metrics.py`: existing Excel entry point, one improvement history per row.
- `dataset/case_fields.py`: shared context mapping for console and UI.
- `evaluate/improvement_runner.py`: console generation/evaluation/review loop.
- `human_review/reviewer.py`: terminal approve/edit/reject input.
- `ui/prompt_analyzer.py`: pure rule-based recommendations reused by the console.
- `ui/app.py`: single-case browser workflow.

Offline checks (no model calls):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_console_improvement.py tests/test_execution.py ui/checks -q
```
