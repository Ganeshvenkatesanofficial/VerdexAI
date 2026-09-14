# Verdex (Quotra) — Backend

**AI-driven tender intelligence platform for Indian Manufacturing MSMEs.**  
Verdex continuously monitors Indian government procurement portals (CPPP, GeM), reads complex Notice Inviting Tender (NIT) documents, and generates deterministic **GO / NO-GO / FIXABLE** verdicts with verbatim source citations for every qualification claim.

---

## The Verdex Doctrine

> **"Agents extract → Math reckons → The Model judges → The App presents."**

In government contracting, an AI hallucination is fatal: submitting a non-compliant tender leads to bid forfeiture, wasted EMD (Earnest Money Deposit), and potential debarment or blacklisting.

To eliminate hallucinations entirely:
1. **The LLM never computes numbers:** It only extracts verbatim text snippets and explicit clauses.
2. **The LLM never invents citations:** Every extracted claim passes through an automated **Citation Gate** that verifies quotes are exact, byte-for-byte substrings of the original tender document.
3. **Deterministic Python solves eligibility:** Code, not probabilistic token generation, decides whether a company satisfies turnover, experience, and certification criteria.

---

## System Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
|                           INDIAN PROCUREMENT PORTALS                              |
|   CPPP (eprocure.gov.in)                                 GeM (gem.gov.in)         |
+-----------------------------------------------------------------------------------+
                                         │ (Polite HTTP Scraper / APIs)
                                         ▼
+-----------------------------------------------------------------------------------+
|                       INGESTION & ADAPTER LAYER (Celery)                          |
|  - tenders/adapters/cppp_adapter.py                                               |
|  - Parse HTML tables, convert IST (UTC+5:30) to UTC (pytz)                        |
|  - Deduplicate via unique_together = ('source_portal', 'source_tender_id')        |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        CANONICAL TENDER DATABASE RECORD                           |
|  - Tender model: metadata, closing dates, raw_listing_text, evidence_file (PDF)   |
+-----------------------------------------------------------------------------------+
                                         │
                        ┌────────────────┴────────────────┐
                        │ Attached NIT PDF?               │
                       YES                                NO
                        │                                 │
                        ▼                                 ▼
+----------------------------------+     +----------------------------------+
|      PDF EXTRACTION ENGINE       |     |        RAW LISTING TEXT          |
|  - tenders/pdf_service.py        |     |  - High-level tender title &     |
|  - pypdf reader                  |     |    summary metadata              |
|  - Heuristic keyword windowing   |     +----------------------------------+
|    (eligibility, turnover, ISO)  |                      │
+----------------------------------+                      │
                        │                                 │
                        └────────────────┬────────────────┘
                                         ▼
+-----------------------------------------------------------------------------------+
|                      EXTRACTION LAYER (Local Ollama / LLM)                        |
|  - tenders/claude_service.py                                                      |
|  - Local gpt-oss:20b model (zero cloud cost, 100% data privacy)                   |
|  - Strict JSON schema enforcement with automated corrective retry                 |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        ZERO-HALLUCINATION CITATION GATE                           |
|  - tenders/citation_gate.py                                                       |
|  - Verifies quote is an exact, unparaphrased substring of source text             |
|  - Silently drops any claim that fails verbatim verification                      |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                      DETERMINISTIC ELIGIBILITY SOLVER                             |
|  - tenders/solver.py (Pure Python)                                                |
|  - Evaluates verified criteria against Company profile & Vault certificates       |
|  - Status per clause: matched | needs_confirmation | rejected                     |
|  - Final Verdict: GO | NO-GO | FIXABLE                                            |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                   MULTI-TENANT PERSISTENCE & REST API (DRF)                       |
|  - Verdict model: saved per (tender, company) pair with full proof_lines JSON     |
|  - Filtered by authenticated company tenant                                       |
+-----------------------------------------------------------------------------------+
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Django 6 + Django REST Framework | Core API, multi-tenant ORM, admin backoffice |
| **Database** | SQLite (Dev) / PostgreSQL (Production) | Relational persistence with JSONField support |
| **Async Task Queue** | Celery 5.6 + Redis 8 | Background tender scraping and asynchronous verdict generation |
| **Task Scheduling** | Celery Beat (`django-celery-beat`) | Database-driven cron scheduler for daily automated sweeps |
| **Local LLM Inference** | Ollama (`gpt-oss:20b`) | Private, zero-cost eligibility clause extraction |
| **PDF Extraction** | `pypdf` | NIT document parsing with smart eligibility windowing |
| **Web Scraping** | `requests` + `BeautifulSoup4` + `lxml` | Robust, polite scraping of public portal listings |
| **Timezone Management**| `pytz` + `django-timezone-field` | Exact IST (`Asia/Kolkata`) to UTC conversion |
| **Authentication** | Django Auth / Session (Superuser) | Multi-tenant user isolation (Google OAuth planned) |

---

## Project Directory Layout

```text
verdex-backend/
├── manage.py                     # Django management CLI
├── requirements.txt              # Frozen Python dependencies
├── README.md                     # Comprehensive project documentation
├── db.sqlite3                    # Local SQLite development database (gitignored)
│
├── verdex_core/                  # Project root configuration
│   ├── __init__.py               # Celery app initialization hook
│   ├── celery.py                 # Celery app definition and broker config
│   ├── settings.py               # Django configuration, Celery settings, media roots
│   ├── urls.py                   # Root URLconf with API discovery index
│   └── wsgi.py / asgi.py         # WSGI / ASGI deployment entrypoints
│
├── companies/                    # Multi-tenancy & Company Profiles
│   ├── models.py                 # Company (tenant) and UserProfile (owner/member)
│   ├── serializers.py            # DRF serializers for company metadata
│   ├── views.py                  # Scoped CompanyViewSet
│   ├── urls.py                   # /api/companies/ routing
│   └── admin.py                  # Admin configuration for companies and profiles
│
├── vault/                        # Secure Per-Company Document Storage
│   ├── models.py                 # Document model (datasheets, certificates, financials)
│   ├── serializers.py            # Multipart upload and document serializer
│   ├── views.py                  # DocumentViewSet isolated by tenant company
│   ├── urls.py                   # /api/documents/ routing
│   └── admin.py                  # Admin interface for uploaded company files
│
└── tenders/                      # Ingestion, Scrapers, LLM Pipeline & Verdicts
    ├── models.py                 # Tender (canonical portal feed) and Verdict models
    ├── serializers.py            # TenderSerializer (lean), TenderDetail, VerdictSerializer
    ├── views.py                  # Read-only TenderViewSet and company-scoped VerdictViewSet
    ├── urls.py                   # /api/tenders/ and /api/verdicts/ routing
    ├── admin.py                  # Tender and Verdict admin interfaces
    │
    ├── adapters/                 # Portal Scraper Adapter Layer
    │   ├── base.py               # BaseTenderAdapter abstract base class
    │   └── cppp_adapter.py       # Live Central Public Procurement Portal scraper
    │
    ├── pdf_service.py            # PDF text extraction with eligibility keyword filtering
    ├── claude_service.py         # Ollama chat client (gpt-oss:20b) with strict JSON schema
    ├── citation_gate.py          # Zero-hallucination verbatim quote verification
    ├── solver.py                 # Deterministic Python eligibility solver
    ├── ingest.py                 # run_daily_sweep Celery task
    ├── verdict_tasks.py          # generate_verdict Celery task (Extract → Verify → Solve)
    └── tasks.py                  # Celery task autodiscovery aggregation
```

---

## Data Model & Multi-Tenancy Design

Verdex uses a robust, isolated multi-tenant architecture designed around MSME business profiles:

```
                  +-------------------+
                  |    django.User    |
                  +-------------------+
                            │
               ┌────────────┴────────────┐
        1:1 (owner)               1:1 (user)
               │                         │
               ▼                         ▼
      +-----------------+       +-----------------+
      |     Company     |◄──────┤   UserProfile   |
      +-----------------+  FK   +-----------------+
      | id              |       | user_id         |
      | name            |       | company_id      |
      | category        |       | role (owner/    |
      | registration_no |       |       member)   |
      | certifications[]|       +-----------------+
      +-----------------+
        │             │
        │ 1:N         │ 1:N
        ▼             ▼
+---------------+  +-------------------------------------+
| vault.Document|  |           tenders.Verdict           |
+---------------+  +-------------------------------------+
| id            |  | id                                  |
| company_id    |  | tender_id (FK to Tender)            |
| title         |  | company_id (FK to Company)          |
| document_type |  | result (go / no_go / fixable)       |
| file          |  | proof_lines (JSON array of clauses) |
| uploaded_at   |  | computed_at                         |
+---------------+  +-------------------------------------+
                                ▲
                                │ 1:N
                   +----------------------------+
                   |       tenders.Tender       |
                   +----------------------------+
                   | id                         |
                   | source_portal (cppp / gem) |
                   | source_tender_id (unique)  |
                   | title                      |
                   | closing_date (UTC)         |
                   | raw_listing_text           |
                   | evidence_file (PDF)        |
                   | status                     |
                   +----------------------------+
```

### 1. `Company` (`companies/models.py`)
Represents an MSME tenant.
- `name` (`CharField`): Company legal entity name.
- `owner` (`OneToOneField` to Django `User`): The primary account administrator.
- `category` (`CharField`): Primary industry domain (e.g. `"electronics manufacturing"`).
- `registration_number` (`CharField`): Udyam / GSTIN registration number.
- `certifications` (`JSONField`): Persistent list of active certifications (e.g. `["ISO 9001:2015", "BIS", "CE", "RoHS"]`).

### 2. `UserProfile` (`companies/models.py`)
Links additional users to a company with role-based access (`owner` or `member`).

### 3. `Document` (`vault/models.py`)
Per-company vault storage for compliance and technical assets.
- `document_type`: Choice of `datasheet`, `certificate`, `financial`, or `other`.
- `file`: Stored under `media/vault_documents/`.
- Scoped strictly by `company_id`.

### 4. `Tender` (`tenders/models.py`)
Canonical, portal-agnostic tender record.
- `source_portal`: Portal identifier (`'cppp'` or `'gem'`).
- `source_tender_id`: Portal's original tender reference ID.
- `unique_together = ('source_portal', 'source_tender_id')`: Ensures database-level deduplication across Celery ingestion sweeps.
- `raw_listing_text`: The verbatim text captured from the listing, critical for citation verification.
- `evidence_file`: Optional uploaded NIT PDF document for full-clause extraction.

### 5. `Verdict` (`tenders/models.py`)
The evaluated qualification record.
- `result`: Outcome classification (`'go'`, `'no_go'`, or `'fixable'`).
- `proof_lines`: JSON list containing every extracted clause, exact quote, and evaluation status:
  ```json
  [
    {
      "clause": "Bidder must possess valid ISO 9001:2015 certification.",
      "citation": "The bidder shall have valid ISO 9001:2015 certificate as on date of tender opening.",
      "status": "matched"
    },
    {
      "clause": "Minimum average annual financial turnover of ₹50 Lakhs.",
      "citation": "Minimum Average Annual Turnover of the bidder should be Rs 50 Lakh during the last three years.",
      "status": "needs_confirmation"
    }
  ]
  ```
- `unique_together = ('tender', 'company')`: Enforces one immutable verdict record per tender-company pair.

---

## The Ingestion & Verdict Pipeline

### Step 1: Automated Portal Scraping (`tenders/ingest.py` & `tenders/adapters/cppp_adapter.py`)
Celery Beat triggers `run_daily_sweep` on a scheduled interval. The `CPPPAdapter`:
1. Fetches pages from `https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata` with a custom browser User-Agent.
2. Selects active tender rows from `table#table tbody tr`.
3. Parses closing and publication timestamps in Indian Standard Time (IST) using `pytz.timezone("Asia/Kolkata")` and translates them into UTC before storing.
4. Performs `Tender.objects.get_or_create(...)` using `(source_portal, source_tender_id)` to prevent redundant writes.
5. Implements polite 1-second delays between page requests to avoid hitting rate limits.

### Step 2: PDF Parsing & Eligibility Windowing (`tenders/pdf_service.py`)
Government tender documents (NITs) are often 40 to 100+ pages long. Sending an entire 100-page document into an LLM context window causes latency spikes, high memory consumption, and hallucinations.
`extract_text_from_pdf`:
- Reads the PDF using `pypdf.PdfReader`.
- If the document is small ($\le$ 14,000 characters), it processes the entire text.
- For large documents, it scans pages against `ELIGIBILITY_KEYWORDS` (`eligibility`, `qualification`, `turnover`, `experience`, `certificate`, `iso`, `pre-qualification`, `minimum`, `mandatory`, `annual turnover`).
- Only pages matching eligibility criteria are assembled and passed to the LLM (up to a safe 14,000-character budget).

### Step 3: LLM Extraction (`tenders/claude_service.py`)
The extracted text is sent to the local **Ollama** daemon running `gpt-oss:20b` via the `/api/chat` endpoint with `format: "json"`.
- A strict system prompt instructs the model to extract criteria into structured JSON containing `criterion_type`, `requirement_text`, and an exact `quote`.
- The prompt explicitly forbids the model from calculating numbers or inferring criteria not present in the text.
- If the output fails `json.loads()`, the service executes an automated single-shot corrective retry instructing the model to repair the malformed JSON.

### Step 4: The Zero-Hallucination Citation Gate (`tenders/citation_gate.py`)
Before any extracted criterion is accepted, it must pass `verify_citations`:
```python
def verify_citations(criteria: list, source_text: str) -> list:
    verified = []
    for criterion in criteria:
        quote = criterion.get("quote", "")
        if quote and quote in source_text:
            verified.append(criterion)
        else:
            print(f"[CITATION GATE] Rejected unverifiable claim: {criterion.get('requirement_text')}")
    return verified
```
If an LLM hallucinates an eligibility clause or alters a single word in the quote, `quote in source_text` evaluates to `False` and the claim is immediately discarded.

### Step 5: Deterministic Python Solver (`tenders/solver.py`)
The solver evaluates verified criteria using deterministic logic:
- **Certifications:** Compares required certifications against `company.certifications` (JSON list) as well as the titles of documents uploaded in the company's `vault` under `document_type="certificate"`. If matched, marked as `"matched"`. If missing, marked as `"needs_confirmation"` and flags the verdict as `"fixable"`.
- **Experience & Turnover:** Currently marked as `"needs_confirmation"`, flagging the bid as `"fixable"` for human-in-the-loop review.
- **Result:**
  - `GO`: All verified criteria are satisfied.
  - `FIXABLE`: Minor missing certifications or items requiring confirmation.
  - `NO-GO`: Hard disqualifying criteria failed.

---

## API Reference

All API routes are served under `/api/` and require Django session authentication (`IsAuthenticated`) unless explicitly designated public.

### Root Index Endpoint
`GET /` (Public)  
Returns a discovery index of all active API endpoints.

```json
{
  "message": "Welcome to the Verdex AI Tender Intelligence API",
  "status": "online",
  "version": "v1",
  "endpoints": {
    "companies": "/api/companies/",
    "vault_documents": "/api/documents/",
    "tenders": "/api/tenders/",
    "verdicts": "/api/verdicts/",
    "admin": "/admin/"
  }
}
```

---

### Companies API (`/api/companies/`)
Scope: Owner-scoped. Manage MSME company profile and active certifications.

#### `GET /api/companies/`
List companies owned by the authenticated user.

```json
[
  {
    "id": 1,
    "name": "Precision AeroTech India Pvt Ltd",
    "category": "aerospace precision machining",
    "registration_number": "UDYAM-TN-02-0049182",
    "certifications": ["ISO 9001:2015", "AS9100D", "BIS"],
    "created_at": "2026-09-13T10:39:05Z"
  }
]
```

#### `POST /api/companies/`
Create or register a new company profile.

```json
{
  "name": "Southern Electroplating Works",
  "category": "surface treatment",
  "registration_number": "UDYAM-TN-03-0091821",
  "certifications": ["ISO 9001:2015", "ISO 14001:2015"]
}
```

---

### Vault Documents API (`/api/documents/`)
Scope: Company-scoped. Upload and retrieve compliance documents and datasheets.

#### `GET /api/documents/`
List all documents belonging to the user's company.

```json
[
  {
    "id": 1,
    "title": "ISO 9001:2015 Certificate",
    "document_type": "certificate",
    "file": "/media/vault_documents/iso_9001_cert.pdf",
    "uploaded_at": "2026-09-13T11:20:00Z"
  }
]
```

#### `POST /api/documents/` (Multipart Form Data)
Upload a document to the company vault:
- `title` (text): e.g. `"Audited Balance Sheet FY 2024-25"`
- `document_type` (choice): `datasheet` | `certificate` | `financial` | `other`
- `file` (binary): PDF or image file

---

### Tenders API (`/api/tenders/`)
Scope: Global, read-only. Unified feed of active tenders from all indexed portals.

#### `GET /api/tenders/`
Returns a lean listing of tenders ordered by closing date.

```json
[
  {
    "id": 14,
    "source_portal": "cppp",
    "source_tender_id": "2026_BPCL_26648",
    "title": "Supply and Installation of Industrial Air Compressors",
    "category": "",
    "closing_date": "2026-10-15T10:30:00Z",
    "published_date": "2026-09-10T04:00:00Z",
    "status": "new",
    "ingested_at": "2026-09-14T06:00:00Z"
  }
]
```

#### `GET /api/tenders/{id}/`
Returns full tender details, including `raw_listing_text` and any attached `evidence_file`.

```json
{
  "id": 14,
  "source_portal": "cppp",
  "source_tender_id": "2026_BPCL_26648",
  "title": "Supply and Installation of Industrial Air Compressors",
  "category": "",
  "closing_date": "2026-10-15T10:30:00Z",
  "published_date": "2026-09-10T04:00:00Z",
  "raw_listing_text": "Tender ID: 2026_BPCL_26648 Organisation: Bharat Petroleum Corporation Limited...",
  "evidence_file": "/media/tender_evidence/NIT_Compressor_2026.pdf",
  "status": "verdict_ready",
  "ingested_at": "2026-09-14T06:00:00Z"
}
```

---

### Verdicts API (`/api/verdicts/`)
Scope: Company-scoped, read-only. Verdicts generated by the background pipeline.

#### `GET /api/verdicts/`
Returns all verdicts evaluated for the authenticated user's company.

```json
[
  {
    "id": 3,
    "tender": 14,
    "tender_title": "Supply and Installation of Industrial Air Compressors",
    "result": "fixable",
    "proof_lines": [
      {
        "clause": "Bidder must possess valid ISO 9001:2015 certification.",
        "citation": "The bidder shall have valid ISO 9001:2015 certificate as on date of tender opening.",
        "status": "matched"
      },
      {
        "clause": "Minimum average annual turnover of ₹50 Lakhs during the last three financial years.",
        "citation": "Minimum Average Annual Turnover of the bidder should be Rs 50 Lakh during the last three years.",
        "status": "needs_confirmation"
      }
    ],
    "computed_at": "2026-09-14T08:15:30Z"
  }
]
```

---

## Local Development Setup

### 1. Prerequisites
- **macOS** or **Linux**
- **Python 3.12+**
- **Redis** (`brew install redis` on macOS)
- **Ollama** (`brew install ollama` or official installer)

### 2. Clone the Repository
```bash
git clone https://github.com/Ganeshvenkatesanofficial/VerdexAI.git
cd verdex-backend
```

### 3. Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables (`.env`)
Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secure-django-secret-key-here
CELERY_BROKER_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
```

### 6. Apply Database Migrations
```bash
python manage.py migrate
```

### 7. Create Superuser (Admin Access)
```bash
python manage.py createsuperuser
```

### 8. Start Redis
```bash
brew services start redis
# verify redis is responding:
redis-cli ping
# returns: PONG
```

### 9. Setup Local LLM (Ollama)
In a dedicated terminal tab, start Ollama and pull the model:

```bash
ollama serve
# In a second tab (first run only — downloads the model):
ollama run gpt-oss:20b
```

---

## Running the Development Stack

Verdex requires four processes running concurrently during local development. Activate `venv` in each terminal tab:

```bash
# Tab 1 — Django Development Server
python manage.py runserver

# Tab 2 — Celery Task Worker
celery -A verdex_core worker --loglevel=info

# Tab 3 — Celery Beat Scheduler
celery -A verdex_core beat --loglevel=info

# Tab 4 — Ollama Local LLM Server
ollama serve
```

---

## Interactive Pipeline Verification

You can test the entire ingestion and verdict generation pipeline directly via Django shell:

```bash
python manage.py shell
```

```python
from tenders.ingest import run_daily_sweep
from tenders.verdict_tasks import generate_verdict
from tenders.models import Tender
from companies.models import Company

# 1. Trigger CPPP scraper sweep manually
new_count, skipped_count = run_daily_sweep()
print(f"Sweep complete: {new_count} new tenders, {skipped_count} skipped.")

# 2. Pick a tender and your company
tender = Tender.objects.first()
company = Company.objects.first()

# 3. Trigger asynchronous verdict generation via Celery
task = generate_verdict.delay(tender.id, company.id)
print(f"Dispatched Celery task ID: {task.id}")

# 4. Or execute synchronously to inspect immediately:
verdict_id = generate_verdict(tender.id, company.id)
print(f"Generated Verdict ID: {verdict_id}")
```

---

## Engineering Realities & Honest Status

1. **CPPP Detail Page CAPTCHA:**  
   The active tender listing index at `eprocure.gov.in/cppp/latestactivetendersnew/cpppdata` is publicly accessible without authentication. However, clicking into full tender view pages (`/cppp/tendersfullview/...`) requires solving an image CAPTCHA. Moreover, comprehensive eligibility clauses are stored inside attached Notice Inviting Tender (NIT) PDFs, not in the HTML markup.  
   *Current Workaround:* Users or administrators download the official NIT PDF and upload it via the Django admin interface (`/admin/tenders/tender/`) under `evidence_file`. The pipeline detects the attached PDF, parses it via `pdf_service.py`, and extracts real eligibility clauses automatically. Programmatic CAPTCHA bypassing is intentionally out of scope.

2. **Solver MVP Status:**  
   The deterministic solver in `solver.py` matches exact certification requirements against company profiles and vault documents. Criteria involving numerical comparisons (`turnover_minimum`, `years_experience`) are currently flagged with `"needs_confirmation"`, yielding a `"fixable"` verdict for human review. Full numeric parsing (e.g. converting `"₹50 Lakhs"` or `"3 Crores"` into comparable integers) is in active development.

3. **Category Tagging:**  
   CPPP listings do not expose industry category codes directly in the listing table. Currently, `category` is stored as a blank string during initial ingestion. Automated classification using keyword rules and LLM categorization is planned.

4. **Zero Cloud API Costs:**  
   The extraction pipeline runs entirely on local hardware via Ollama (`gpt-oss:20b`). No external tokens, cloud subscriptions, or proprietary API keys (Anthropic/OpenAI) are required.

---

## Security & Operational Safeguards

- `.env`, `db.sqlite3`, `media/`, `*.json` service keys, and `venv/` are explicitly gitignored.
- No cloud credentials or secrets are stored in this repository.
- Citations are never fabricated: any clause extracted by the LLM that does not match the source document verbatim is discarded by `citation_gate.py`.
- Multi-tenancy is enforced at both view and query levels using authenticated user foreign keys.

---

## Roadmap

- [x] Multi-tenant data models (`Company`, `UserProfile`, `Document`, `Tender`, `Verdict`)
- [x] Live CPPP scraper with IST-to-UTC timezone conversion and deduplication
- [x] Celery background worker and Celery Beat scheduler configuration
- [x] Local Ollama LLM integration (`gpt-oss:20b`) with strict JSON schema
- [x] Zero-hallucination verbatim Citation Gate
- [x] Deterministic Python solver for certifications
- [x] Large PDF text extraction with eligibility keyword windowing
- [ ] Automated numeric evaluation for turnover and experience thresholds
- [ ] GeM (Government e-Marketplace) portal adapter
- [ ] Google OAuth 2.0 authentication (`django-allauth`)
- [ ] Keyword and LLM-assisted industry category tagging
- [ ] Modern Next.js / React frontend with real-time GO/NO-GO breakdown
- [ ] Production deployment guide (PostgreSQL, Gunicorn, Nginx, Docker)

---

## License

Proprietary — All rights reserved © 2026 Verdex AI (Quotra).
