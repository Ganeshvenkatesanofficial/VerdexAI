# Verdex (Quotra) — Backend

AI-driven tender intelligence platform for Indian Manufacturing MSMEs. Verdex watches government procurement portals, reads every tender clause, and tells a company **GO / NO-GO / FIXABLE** — with a verbatim citation for every claim.

> **Core doctrine:** *Agents extract → math reckons → the model judges → the app presents.*  
> The model never computes a number or invents a citation; deterministic Python code does the deciding.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend framework** | Django 6 + Django REST Framework |
| **Database** | SQLite (dev) — PostgreSQL planned for production |
| **Async task queue** | Celery + Redis |
| **Scheduling** | Celery Beat (`django-celery-beat`) |
| **LLM inference** | Local Ollama (`gpt-oss:20b`) — zero-cost extraction layer |
| **PDF parsing** | `pypdf` |
| **Web scraping** | `requests` + `BeautifulSoup4` + `lxml` |
| **Auth** | Django built-in (superuser) — Google OAuth planned |

---

## Project Structure

```text
verdex-backend/
├── verdex_core/          # Project settings, root URLs, Celery app config
├── companies/            # Company profiles, user↔company linking (multi-tenancy)
├── vault/                # Per-company document storage (datasheets, certs, financials)
├── tenders/              # Tender feed, adapters, extraction pipeline, verdicts
│   ├── adapters/
│   │   ├── base.py             # Abstract adapter interface
│   │   └── cppp_adapter.py     # Real CPPP (eprocure.gov.in) scraper
│   ├── claude_service.py       # LLM extraction layer (Ollama / gpt-oss:20b backed)
│   ├── pdf_service.py          # PDF text extraction (NIT/tender documents)
│   ├── citation_gate.py        # Verbatim quote verification — zero-hallucination gate
│   ├── solver.py               # Deterministic eligibility solver (pure Python)
│   ├── ingest.py               # Daily tender sweep (Celery task)
│   ├── tasks.py                # Celery autodiscovery task exports
│   └── verdict_tasks.py        # Extract → verify → solve → persist (Celery task)
├── manage.py
└── requirements.txt
```

---

## Local Setup

### 1. Clone and enter the project
```bash
git clone https://github.com/Ganeshvenkatesanofficial/VerdexAI.git
cd verdex-backend
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply migrations
```bash
python manage.py migrate
```

### 5. Create an admin superuser
```bash
python manage.py createsuperuser
```

### 6. Install and start Redis (macOS)
```bash
brew install redis
brew services start redis
```

---

## Environment Variables (`.env`)

Create a `.env` file in the root directory:

```env
DEBUG=True
SECRET_KEY=your-django-secret-key
CELERY_BROKER_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
```

---

## Local LLM (Ollama)

```bash
ollama serve                  # keep running in its own terminal tab
ollama run gpt-oss:20b        # first run pulls the model if not already present
```

---

## Running the Full Stack (Development)

Four processes run concurrently, each in its own terminal tab (activate `venv` in each):

```bash
# Tab 1 — Django dev server
python manage.py runserver

# Tab 2 — Celery worker (executes tasks)
celery -A verdex_core worker --loglevel=info

# Tab 3 — Celery Beat (triggers scheduled tasks)
celery -A verdex_core beat --loglevel=info

# Tab 4 — Ollama server (LLM inference)
ollama serve
```

---

## Data Model

- **`Company`** — One row per tenant (MSME). Holds name, owner, category, registration number, and certifications (`JSONField`).
- **`UserProfile`** — Links a Django User to a Company with a role (`owner` / `member`). Foundation for multi-tenancy.
- **`Document` (`vault` app)** — Per-company uploaded files (datasheets, certificates, financials), scoped by company foreign key.
- **`Tender`** — Canonical, portal-agnostic tender record. `unique_together = ('source_portal', 'source_tender_id')` prevents duplicate ingestion across sweeps.
- **`Verdict`** — One per `(tender, company)` pair. Holds `result` (`go` / `no_go` / `fixable`) and `proof_lines` (`JSONField` — clause, citation, status per criterion).

---

## API Endpoints

All endpoints require authentication (`IsAuthenticated`) unless noted. Company-scoped endpoints automatically filter to the logged-in user's company.

| Endpoint | Method | Scope | Notes |
|---|---|---|---|
| `/` | `GET` | Public | Root API index listing all available endpoints |
| `/api/companies/` | `GET`, `POST` | Owner-scoped | List/create companies owned by the logged-in user |
| `/api/documents/` | `GET`, `POST` | Company-scoped | Vault document upload/list |
| `/api/tenders/` | `GET` | Global, read-only | Full unified tender feed (lean list serializer) |
| `/api/tenders/{id}/` | `GET` | Global, read-only | Full detail — includes `raw_listing_text`, `evidence_file` |
| `/api/verdicts/` | `GET` | Company-scoped, read-only | Verdicts are only ever written by the backend pipeline |
| `/admin/` | — | Superuser only | Django admin — inspect/edit all models directly |

---

## The Ingestion & Verdict Pipeline

### 1. Daily Tender Sweep (`tenders/ingest.py`)

A Celery Beat–scheduled task (`run_daily_sweep`) runs `CPPPAdapter`, which:
1. Fetches N pages of `https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata`
2. Parses each `<tr>` into the canonical `Tender` shape
3. Converts IST timestamps to UTC correctly (`pytz.timezone("Asia/Kolkata")`)
4. Deduplicates via `get_or_create` on `(source_portal, source_tender_id)`

> **Adapter Pattern:** Every portal implements `BaseTenderAdapter` (`fetch_raw_listings()` + `normalize()`), so adding a second portal (e.g. GeM, state portals) means writing one new adapter class — the rest of the pipeline remains untouched.

### 2. Verdict Generation (`tenders/verdict_tasks.py`)

`generate_verdict(tender_id, company_id)`:
1. **Extract** — `claude_service.py` sends tender text (PDF text via `pdf_service.py` if `evidence_file` is attached, else `raw_listing_text`) to local Ollama (`gpt-oss:20b`) with a strict-JSON system prompt. One corrective retry on malformed JSON.
2. **Verify (Citation Gate)** — `citation_gate.py` rejects any extracted criterion whose quote is not an exact verbatim substring of the source text. This provides the zero-hallucination guarantee.
3. **Solve** — `solver.py` deterministically evaluates verified criteria against `company.certifications` and uploaded vault certificates. No LLM involvement in this step — pure Python, ensuring every verdict is reproducible and auditable.
4. **Persist** — `Verdict.objects.update_or_create(...)` — one row per `(tender, company)`.

---

## Known Limitations & Honest Status

- **CPPP listing pages contain no eligibility clauses** — only title, dates, and organization name. Real criteria live in attached NIT/tender PDFs, which are gated behind an image CAPTCHA on the detail page. Current workflow: download PDF → upload via `/admin` → pipeline picks it up automatically via `evidence_file`.
- **Solver is an MVP** — `years_experience` and `turnover_minimum` criteria are currently flagged `needs_confirmation` rather than numerically evaluated.
- **Category tagging** — CPPP listings don't expose a category field directly; currently stored blank. Candidate solutions: keyword tagging or LLM categorization.
- **No frontend yet** — this is currently an API-only backend build.
- **No OAuth yet** — authentication is Django superuser / session auth; Google Sign-In (`django-allauth`) is planned.
- **Single portal currently live** — CPPP is the live adapter; GeM adapter is planned next.
- **LLM is local (`Ollama / gpt-oss:20b`)** — zero cloud costs and private on-device processing.

---

## Security Notes

- `.env`, `*.json` credential files, `venv/`, `db.sqlite3`, and `media/` are all gitignored.
- No cloud credentials (GCP/Anthropic) are stored in this repo.
- Never commit API keys, service account files, or `.env` contents.

---

## Roadmap

- [ ] Automate real NIT/PDF fetching
- [ ] Numeric solver logic for turnover/experience criteria
- [ ] Category classification (LLM-assisted or keyword-based)
- [ ] Google OAuth via `django-allauth`
- [ ] Second portal adapter (GeM)
- [ ] Frontend (React + Tailwind)
- [ ] Production database (PostgreSQL) + deployment configuration
