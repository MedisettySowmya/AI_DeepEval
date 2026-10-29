def get_generator_context(test_case):
    """Prefer retrieved evidence; preserve the existing supplied-context fallback."""
    context = (
        test_case.get("retrieval_context")
        or test_case.get("prompt_context", test_case.get("context", ""))
    )
    if isinstance(context, list):
        return "\n\n".join(context)
    return context


def build_prompt(test_case, include_context=True):
    question = test_case["input"]
    context = get_generator_context(test_case)

    if not include_context or not context:
        prompt = question
    else:
        prompt = (
            "Use the supplied context to answer the question.\n\n"
            f"Supplied context:\n{context}\n\n"
            f"Question:\n{question}"
        )
    instructions = test_case.get("instructions", "").strip()
    if instructions:
        prompt = f"Additional instructions:\n{instructions}\n\n{prompt}"
    return prompt
