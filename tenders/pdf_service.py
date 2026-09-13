from pypdf import PdfReader

ELIGIBILITY_KEYWORDS = [
    "eligibility",
    "qualification",
    "criteria",
    "turnover",
    "experience",
    "certificate",
    "certification",
    "iso",
    "pre-qualification",
    "financial",
    "minimum",
    "mandatory",
    "annual turnover",
]


def extract_text_from_pdf(pdf_source, max_chars=14000) -> str:
    """
    Extracts text from a PDF file path or file-like object.
    For long documents (e.g. 30-100 pages), intelligently prioritizes
    pages containing eligibility, qualification, and certification criteria
    to prevent LLM context overflow and timeouts.
    """
    try:
        reader = PdfReader(pdf_source)
        pages_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append((i + 1, text.strip()))

        if not pages_text:
            return ""

        full_text = "\n\n".join(t for _, t in pages_text)

        # If document is compact, return in full
        if len(full_text) <= max_chars:
            return full_text

        # For long PDFs, extract pages containing eligibility keywords
        relevant_pages = []
        for page_num, text in pages_text:
            text_lower = text.lower()
            if any(kw in text_lower for kw in ELIGIBILITY_KEYWORDS):
                relevant_pages.append(f"--- Page {page_num} ---\n{text}")

        if relevant_pages:
            filtered = "\n\n".join(relevant_pages)
            return filtered[:max_chars]

        # Fallback to the first pages if no keywords matched
        return full_text[:max_chars]
    except Exception as e:
        print(f"[PDF EXTRACTION] Error reading PDF: {e}")
        return ""
