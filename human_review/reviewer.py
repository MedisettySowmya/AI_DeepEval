"""Console approval for each Excel case's proposed prompt revision."""


def review_prompt(suggestion):
    """Return the explicitly approved prompt, or None when rejected."""
    print("\nEvaluator feedback (possible causes, not proven diagnoses):")
    for reason in suggestion["reasons"]:
        print(f"- {reason}")
    print("\nPossible causes and items for human validation:")
    for cause in suggestion.get("causes", []):
        print(f"- Possible cause: {cause['possible_cause']}")
        print(f"  Evidence: {cause['evidence']}")
        print(f"  What to validate/change: {cause['human_check']}")
    print("\nRecommendations:")
    for recommendation in suggestion["recommendations"]:
        print(f"- {recommendation}")
    print("Review the question and supplied context for missing information too.")

    candidate = suggestion["improved_prompt"]
    while True:
        print(f"\nProposed prompt:\n{candidate}")
        choice = input("\nApprove, edit, or reject? [a/e/r]: ").strip().lower()
        if choice == "a":
            return candidate
        if choice == "r":
            return None
        if choice == "e":
            print("Enter the complete prompt. Finish with END on its own line.")
            lines = []
            while True:
                line = input()
                if line == "END":
                    break
                lines.append(line)
            edited = "\n".join(lines).strip()
            if edited:
                candidate = edited
            else:
                print("Prompt cannot be empty.")
        else:
            print("Choose a, e, or r.")
