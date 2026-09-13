def solve_eligibility(criteria: list, company) -> dict:
    proof_lines = []
    has_fixable = False

    company_certs = getattr(company, "certifications", []) or []
    if hasattr(company, "documents"):
        cert_docs = list(company.documents.filter(document_type="certificate").values_list("title", flat=True))
        company_certs = list(company_certs) + cert_docs

    for criterion in criteria:
        ctype = criterion.get("criterion_type")
        quote = criterion.get("quote", "")
        requirement = criterion.get("requirement_text", "")

        if ctype == "certification_required":
            has_cert = any(
                cert.lower() in requirement.lower() or requirement.lower() in cert.lower()
                or cert.lower() in quote.lower() or quote.lower() in cert.lower()
                for cert in company_certs
            )
            status = "matched" if has_cert else "needs_confirmation"
            if not has_cert:
                has_fixable = True
        else:
            # years_experience, turnover_minimum, other — MVP: flag for manual confirmation
            status = "needs_confirmation"
            has_fixable = True

        proof_lines.append({
            "clause": requirement,
            "citation": quote,
            "status": status,
        })

    result = "fixable" if has_fixable else "go"
    return {"result": result, "proof_lines": proof_lines}
