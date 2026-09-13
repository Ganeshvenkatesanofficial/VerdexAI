from celery import shared_task
from .models import Tender, Verdict
from .claude_service import extract_eligibility_criteria
from .citation_gate import verify_citations
from .solver import solve_eligibility
from .pdf_service import extract_text_from_pdf
from companies.models import Company


@shared_task
def generate_verdict(tender_id, company_id):
    tender = Tender.objects.get(id=tender_id)
    company = Company.objects.get(id=company_id)

    # Prioritize evidence_file (PDF) if available, fallback to raw listing text
    source_text = ""
    if tender.evidence_file:
        try:
            source_text = extract_text_from_pdf(tender.evidence_file.path)
        except Exception as e:
            print(f"[VERDICT] Failed reading PDF evidence file: {e}")
            source_text = ""

    if not source_text:
        source_text = tender.raw_listing_text

    extracted = extract_eligibility_criteria(source_text)
    criteria = extracted.get("criteria", [])

    verified_criteria = verify_citations(criteria, source_text)
    solved = solve_eligibility(verified_criteria, company)

    verdict, created = Verdict.objects.update_or_create(
        tender=tender,
        company=company,
        defaults={
            "result": solved["result"],
            "proof_lines": solved["proof_lines"],
        }
    )
    return verdict.id
