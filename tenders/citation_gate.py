def verify_citations(criteria: list, source_text: str) -> list:
    """
    For each criterion, checks if its quote appears verbatim in source_text.
    Any criterion whose quote doesn't match exactly is REJECTED — never rendered.
    """
    verified = []
    for criterion in criteria:
        quote = criterion.get("quote", "")
        if quote and quote in source_text:
            verified.append(criterion)
        else:
            print(f"[CITATION GATE] Rejected unverifiable claim: {criterion.get('requirement_text')}")
    return verified
