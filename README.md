# ResuMind

> Smart Resumes. Smarter Careers.

AI-powered career platform that matches your CV to real jobs, explains the gaps, and builds a personalised roadmap — designed for local-first deployment.

**Authors:** Gal Ratzon, Noa Negri, Avia Omesi — Final Project, Bar-Ilan University

---

## Project structure

```
ResuMind/
├── backend/                    Python backend
│   ├── recommendation/         Sentence-BERT job matching engine
│   │   └── recommendation.py
│   ├── llm.py                  LLM integration (Qwen via Ollama/llama.cpp)
│   ├── scraper.py              PDF / DOCX text extraction
│   ├── schema.sql              PostgreSQL + PGVector schema
│   ├── tests/                  deterministic matching tests
│   └── requirements.txt
├── frontend/                   React + Vite + Tailwind UI
│   ├── src/
│   │   ├── pages/              Landing, Resume (Flow 1), Jobs (Flow 2), Roadmap (Flow 3)
│   │   ├── components/         Navbar, Footer
│   │   ├── lib/                auth, CV state, YAML, PDF generation
│   │   └── theme.jsx           Light / dark theme context
│   ├── index.html
│   └── package.json
├── Dockerfile                  Production frontend + backend image
├── .dockerignore               Excludes secrets, caches, and local datasets
└── README.md
```

---

## Three user flows

| Flow | Description |
|------|-------------|
| **1 – Resume** | Upload a PDF/DOCX **or** build one via a 6-step form → YAML → PDF; generated resumes can be saved to the profile |
| **2 – Jobs** | Searchable semantic matching with skill coverage, CV evidence, salary, remote, work-type, and experience filters |
| **3 – Roadmap** | Role roadmap plus selected-job gap analysis; acquired skills influence future job matching |

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, Tailwind CSS, React Router |
| PDF generation | jsPDF (browser-side) |
| Backend | Python, FastAPI, Uvicorn |
| CV parsing | pypdf, python-docx, pytesseract (OCR fallback) |
| Embeddings | Sentence-BERT `all-MiniLM-L6-v2` (384-dim) |
| Vector DB | PostgreSQL + PGVector |
| LLM | Qwen through a local OpenAI-compatible llama.cpp/Ollama endpoint |
| Infra | Proxmox VM, Docker containers, local storage |

---

## Getting started

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
# Run once against PostgreSQL/PGVector:
psql "$DATABASE_URL" -f schema.sql
```

**Environment variables** — create `backend/.env`:

```env
# Local OpenAI-compatible inference endpoint
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:72b
OLLAMA_API_KEY=ollama

# PostgreSQL + PGVector
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
```

### Run the recommendation engine (local CSV mode)

```bash
cd backend
python recommendation/recommendation.py path/to/resume.pdf path/to/jobs.csv
```

### Run CV improvement suggestions (requires Ollama running)

```bash
cd backend
python llm.py path/to/resume.pdf "Backend Engineer"
```

### Docker image

The production image builds the React frontend, bundles the Sentence-BERT model, and serves both the SPA and FastAPI from port `8000`.

```bash
docker build -t resumind:local .

docker run --rm --name resumind \
  -p 8000:8000 \
  --add-host=host.docker.internal:host-gateway \
  -e DATABASE_URL=postgresql://postgres:password@host.docker.internal:5432/postgres \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
  -e OLLAMA_MODEL=qwen2.5:72b \
  -e JWT_SECRET=replace-with-a-long-random-secret \
  resumind:local
```

Open `http://localhost:8000`; API documentation remains available at `http://localhost:8000/docs`. PostgreSQL/PGVector and the OpenAI-compatible LLM endpoint run outside this image. Run `backend/schema.sql` and the ingestion scripts against the configured database before testing roadmap and job data.

---

## Architecture

```
User → Frontend (React)
         │
         ├─ Flow 1: PDF upload / Form → YAML → PDF (browser-side jsPDF)
         │
         ├─ Flow 2: CV + acquired skills ──► PGVector search ──► Filterable jobs
         │                                                        │
         │                                             Skill coverage + CV evidence
         │
         └─ Flow 3: Gap analysis ──► Roadmap JSON ──► Interactive skill tree
                                        │
                                  Mark skill acquired
                                        │
                                 Career profile re-embedded + jobs re-ranked
```

---

## Key design decisions

- **Explainable fit score** — combines 75% semantic similarity with 25% explicit skill coverage; it is an estimate, not a probability
- **Sentence-BERT over keyword matching** — handles synonyms ("JS" ↔ "JavaScript", "Full Stack" ↔ "Web Developer")
- **Local-first storage** — uploaded files are temporary, contact PII is redacted before AI analysis, and extracted profile data stays in the configured database
- **Job-specific roadmap context** — opening a roadmap from a job preserves that job's requirements and missing skills
- **Enriched job ingestion** — salary, benefits, industries, company size, employee counts, and posting dates are available for filtering and display

## Tests and verification

```bash
cd frontend && npm run build
cd ../backend && python -m unittest discover -s tests -v
```

The matching helper tests cover aliases, required-skill parsing, evidence, bounded scoring, and contact-PII redaction. The full end-to-end flow still requires a configured PostgreSQL/PGVector database and inference endpoint.
