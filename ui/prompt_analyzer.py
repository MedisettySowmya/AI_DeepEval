"""UI-only prompt recommendations based on evaluator feedback."""
from pathlib import Path


# Optional instructions are omitted for retrieval problems: fix the evidence instead.
METRIC_GUIDANCE = {
    "AnswerRelevancyMetric": {
        "cause": "The response may drift from the question or interpret it differently.",
        "check": "Compare the answer with the question; clarify the intended scope if needed.",
        "instruction": "Answer the question directly and omit unrelated details. If the question is ambiguous, ask for clarification.",
    },
    "HallucinationMetric": {
        "cause": "The response may add unsupported details or conflict with the reference.",
        "check": "Check each flagged claim and verify that the supplied and reference contexts are accurate and sufficient.",
        "instruction": "Do not invent facts or unsupported details. If the supplied information is insufficient or conflicting, explain the limitation instead of guessing.",
    },
    "FaithfulnessMetric": {
        "cause": "The answer may contain claims unsupported by the retrieved passages.",
        "check": "Check the flagged claims against the retrieved passages and verify the sources.",
        "instruction": "Base factual claims on the retrieved passages. State when they do not contain enough information.",
    },
    "ContextualRelevancyMetric": {
        "cause": "Retrieved passages may include unrelated information.",
        "check": "Remove irrelevant passages or improve the retrieval query. Changing answer instructions alone will not fix retrieval quality.",
        "instruction": None,
    },
    "ContextualRecallMetric": {
        "cause": "Retrieved passages may omit facts needed for the expected answer.",
        "check": "Verify ground truth and retrieve the missing source information. Changing answer instructions alone will not fix retrieval quality.",
        "instruction": None,
    },
    "ContextualPrecisionMetric": {
        "cause": "Relevant passages may rank below irrelevant passages.",
        "check": "Review passage order and place the most relevant sources first. Changing answer instructions alone will not fix retrieval quality.",
        "instruction": None,
    },
    "CorrectnessMetric": {
        "cause": "The answer may contain incorrect facts.",
        "check": "Verify the expected answer and compare the flagged facts with the sources.",
        "instruction": "Use verified source information. State uncertainty instead of guessing.",
    },
    "CompletenessMetric": {
        "cause": "The answer may omit required information.",
        "check": "Check every part of the question and whether sources contain the missing information.",
        "instruction": "Address every part of the question. Clearly identify information unavailable in the sources.",
    },
    "ClarityMetric": {
        "cause": "The answer may be difficult to understand.",
        "check": "Check confusing wording, organization, and repetition.",
        "instruction": "Use clear language, organize the answer logically, and avoid unnecessary repetition.",
    },
    "BiasMetric": {
        "cause": "The answer may contain prejudiced opinions.",
        "check": "Review the flagged wording for stereotypes or unequal treatment.",
        "instruction": "Use neutral language and avoid unsupported generalizations about groups.",
    },
    "ToxicityMetric": {
        "cause": "The answer may contain hostile or abusive language.",
        "check": "Review the flagged wording in its original context.",
        "instruction": "Use respectful language and avoid insults, threats, and personal attacks.",
    },
}


def analyze_prompt(test_case, current_prompt, results):
    reasons = []
    recommendations = []
    causes = []
    for result in results:
        if result.get("passed") is True:
            continue
        reasons.append(f"{result['metric']}: {result.get('reason') or result.get('error') or 'No explanation provided.'}")
        if result.get("status", "completed") != "completed":
            causes.append({
                "possible_cause": "The metric could not complete.",
                "evidence": result.get("reason") or result.get("error"),
                "human_check": "Resolve missing inputs or evaluation errors before reviewing answer quality.",
            })
            continue
        guidance = METRIC_GUIDANCE.get(result["metric"])
        if guidance is None:
            continue
        causes.append({
            "possible_cause": guidance["cause"],
            "evidence": result.get("reason"),
            "human_check": guidance["check"],
        })
        instruction = guidance["instruction"]
        if instruction and instruction not in recommendations:
            recommendations.append(instruction)

    supplied_context = test_case.get("retrieval_context") or test_case.get("prompt_context", test_case.get("context"))
    reference_context = test_case.get("reference_context")
    if not supplied_context:
        causes.append({
            "possible_cause": "The generator was given no supporting context.",
            "evidence": "No retrieved or supplied context is available.",
            "human_check": "Provide verified source information in the edited prompt if this question needs it.",
        })
    elif reference_context and supplied_context != reference_context:
        causes.append({
            "possible_cause": "The generator and evaluator received different context.",
            "evidence": "Supplied context differs from reference context; this difference may be intentional.",
            "human_check": "Check whether the supplied material omits or contradicts facts needed to answer.",
        })

    template = (Path(__file__).parent / "templates" / "improvement.txt").read_text(
        encoding="utf-8"
    )
    instruction = "\n".join(recommendations)
    # Avoid appending identical instructions on every unsuccessful run.
    improved = current_prompt
    if instruction and instruction not in current_prompt:
        improved = template.replace("{instructions}", instruction).replace(
            "{original_prompt}", current_prompt
        )
    return {
        "reasons": reasons,
        "causes": causes,
        "recommendations": recommendations,
        "improved_prompt": improved,
    }
