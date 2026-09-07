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

## Core user flows

| Flow | Description |
|------|-------------|
| **1 – Resume** | Upload a PDF/DOCX **or** build one via a 6-step form → YAML → PDF; generated resumes can be saved to the profile |
| **2 – Jobs** | Searchable semantic matching with skill coverage, CV evidence, salary, remote, work-type, and experience filters |
| **Statistics** | Deterministic skill-demand and fit statistics across every job currently recommended to the user's profile |
| **3 – Roadmap** | Role and job-specific learning plans, with CV-detected skills and saved manual progress; acquired skills influence future job matching |

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

For an existing installation, apply this small migration before starting the
updated backend (run from `backend`, with `DATABASE_URL` exported):

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/20260907_roadmap_manual_override.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/20260907_devops_git_github_cicd.sql
```

It adds a flag so explicit skill check/uncheck choices take precedence over CV
detection, and adds GitHub and CI/CD to the DevOps roadmap. Git and GitHub are
displayed separately but share learned progress. Existing post-onboarding skill
updates are preserved as manual choices. Both migrations are idempotent and do
not delete profiles or progress.

Jobs default to **Highest fit first**: all candidates passing the semantic
threshold and filters are ranked by the displayed score before pagination
(75% semantic similarity + 25% detected skill coverage). Title A–Z remains available.

### Your statistics

The authenticated **Your statistics** navbar page analyses every job currently
passing the user's recommendation threshold. For each detected skill it reports:

- the number and percentage of recommended postings that mention the skill;
- whether the skill is found in the saved CV or acquired roadmap progress;
- the user's strongest skills ordered by demand;
- the most frequently mentioned skills not found in the profile;
- average estimated fit and strong/good/exploratory fit distribution.

For example, “Docker — 70%” means that 7 of 10 recommended job postings mention
Docker. It does **not** mean the candidate has a 70% hiring probability, and a
posting mention can represent a mandatory skill, preference, or descriptive
technology. The page shows its denominator and skill-data coverage so the number
can be explained during evaluation.

`GET /api/user/statistics` is authenticated, read-only, and uses the same profile,
recommendation threshold, embedding, skill aliases, explicit roadmap progress,
and 75/25 fit formula as the Jobs page. Each skill is counted at most once per
posting. The calculations are deterministic and do not call the chat model.

### Match explanations and full job details

On the Jobs page, select a posting and expand **Why this match?** to see:

- The actual semantic and skill-coverage contributions to its estimated fit.
  With no detected posting skills, the score uses semantic similarity alone.
- Up to three related CV/job excerpt pairs, compared separately with the same
  embedding model. These are supporting examples, **not** causal model reasoning
  or contributions that add up to the whole-document semantic score.
- Evidence distinguishing CV mentions from skills acquired in the roadmap, plus
  practical CV suggestions that do not assume missing skills are already learned.

The token-count warning is not shown in the UI. As an implementation detail, the
current `all-MiniLM-L6-v2` configuration still reads at most 256 tokens for a single
embedding; skill coverage checks the full profile. Excerpts are sampled across
the full saved text (up to 32 per document, 320 characters each).

Explanations load on demand from authenticated
`GET /api/user/jobs/{job_id}/explanation`, using the same saved CV and acquired
skills as job ranking. This does not change scoring, embeddings stored in the
database, or job ordering. Contact emails/phone numbers are redacted before
excerpt comparison; there is no LLM call, shared profile cache, or database write.

**Full job details**, next to **Apply**, opens a keyboard-accessible dialog with
the full saved description, supplied requirements, detected skills, benefits,
and available location, salary, experience, company and posting-date metadata.
HTML is displayed as plain text and application links allow only HTTP/HTTPS.
The view cannot restore text omitted during ingestion: the current importer caps
stored descriptions at 4,000 characters and builds job embeddings from the title,
the first 1,000 description characters and supplied skills. Always check the
original listing for complete, current information.

### Roadmap learning resources

Expand **Learn** below an unlearned skill on a role or job-specific roadmap. It contains
up to three links: a relevant [roadmap.sh learning path](https://roadmap.sh/roadmaps/)
and/or primary-source tutorials and documentation, such as
[Docker getting started](https://docs.docker.com/get-started/) and the
[Python tutorial](https://docs.python.org/3/tutorial/).

- Links open in a new tab; opening them never marks a skill as learned.
- Marking a skill as learned hides its Learn section; unchecking it shows the
  section again. This also applies when loading previously saved progress.
- `backend/learning_resources.py` maintains exact skill/alias mappings. All 159
  unique skills currently stored in role roadmaps and all 184 skills in the job
  extraction vocabulary have a curated resource. Unknown future skill names
  receive clearly labelled searches, not fabricated documentation URLs.
- The authenticated roadmap API attaches `learning_resources` to each skill.
  No schema migration, AI call or web fetch is needed to display them.
- Guides are starting points, not endorsements of paid courses. External sites
  may require an account or charge for optional labs, products or cloud usage.
- Resume text, account details and job descriptions are not included in links.
  Search fallbacks contain only the skill label, and links suppress referrers.

To check the static catalog for moved or broken links, run from the project root:

```bash
python backend/check_learning_resources.py
```

The checker reports redirects/status issues without changing the catalog.
Some providers block automated requests (403); verify those in a browser before
removing a resource. Unit tests do not depend on external website availability.

### Backend environment variables

Create `backend/.env`:

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

The 55 deterministic backend tests cover matching/ranking, market statistics, roadmap progress,
learning resources, score explanations, real excerpt evidence, HTML-to-text
display, bounded inference work, token-window diagnostics and contact-PII redaction.
The full end-to-end flow still requires a configured PostgreSQL/PGVector database
and inference endpoint.
