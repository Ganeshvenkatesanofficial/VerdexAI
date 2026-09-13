import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gpt-oss:20b"

EXTRACTION_SYSTEM_PROMPT = """You are a procurement document analyst. You extract eligibility criteria from Indian government tender text into strict JSON.

Rules:
- Only extract criteria that are EXPLICITLY stated in the text.
- For each criterion, you MUST include an exact verbatim quote from the source text (word-for-word, no paraphrasing) proving the criterion exists.
- Do NOT compute, calculate, or infer any numbers — only extract what is written.
- If the tender text is too short/incomplete to determine a criterion, return an empty list: {"criteria": []}.
- Respond with ONLY valid JSON, no preamble, no markdown formatting, no backticks.

Output schema:
{
  "criteria": [
    {
      "criterion_type": "turnover_minimum | years_experience | certification_required | other",
      "requirement_text": "human-readable description of what's required",
      "quote": "exact verbatim quote from source text"
    }
  ]
}
"""


def _call_ollama(messages: list) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "format": "json",
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def extract_eligibility_criteria(tender_text: str) -> dict:
    """
    Calls local Ollama model (gpt-oss:20b) to extract structured eligibility criteria from raw tender text.
    Returns parsed JSON dict. Raises on malformed response after one retry.
    """
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Tender text:\n\n{tender_text}"},
    ]
    raw_text = _call_ollama(messages)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # one corrective retry — ask the model to fix its own output
        retry_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": "That was not valid JSON. Respond with ONLY valid JSON according to the schema, nothing else.",
            },
        ]
        retry_text = _call_ollama(retry_messages)
        return json.loads(retry_text)
