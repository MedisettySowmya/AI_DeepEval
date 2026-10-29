"""Translate the two context fields into generation and evaluation inputs."""
import copy


def is_missing(value):
    """Preserve the application's blank-value policy for evaluation inputs."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value or all(is_missing(item) for item in value)
    return False


def prepare_fields(row):
    """Map application fields to DeepEval fields without changing the row.

    Reference evidence and retrieved evidence have separate roles. Do not
    substitute generation context for a missing reference here. Keep empty
    contexts as empty lists so existing skip handling remains unchanged.
    """
    fields = {
        "input": row.get("input"),
        "actual_output": row.get("actual_output"),
        "expected_output": row.get("expected_answer"),
        "context": row.get("reference_context"),
        "retrieval_context": row.get("retrieval_context"),
    }
    for name in ("context", "retrieval_context"):
        value = fields[name]
        if isinstance(value, str):
            fields[name] = [value.strip()] if value.strip() else []
    return fields


def normalize_case(case):
    prepared = copy.deepcopy(case)
    context = prepared.get("context", prepared.get("expected_answer")
                           or prepared.get("reference_context") or "")
    if isinstance(context, list):
        context = "\n\n".join(context)
    retrieved = prepared.get("retrieval_context") or ""
    prepared.update(context=context, reference_context=context,
                    expected_answer=context, retrieval_context=retrieved,
                    prompt_context=retrieved)
    return prepared
