# ResuMind

> Smart Resumes. Smarter Careers.

AI-powered career platform that matches your CV to real jobs, explains the gaps, and builds a personalised roadmap — all processed locally, no cloud required.

**Authors:** Gal Ratzon, Noa Negri, Aviya Omisi — Final Project, Bar-Ilan University

---

## Project structure

```
ResuMind/
├── backend/                    Python backend
│   ├── recommendation/         Sentence-BERT job matching engine
│   │   └── recommendation.py
│   ├── llm.py                  LLM integration (Qwen via Ollama)
│   ├── scraper.py              PDF / DOCX text extraction
│   └── requirements.txt
├── frontend/                   React + Vite + Tailwind UI
│   ├── src/
│   │   ├── pages/              Landing, Resume (Flow 1), Jobs (Flow 2), Roadmap (Flow 3)
│   │   ├── components/         Navbar, Footer
│   │   ├── lib/                yaml.js, generatePdf.js
│   │   └── theme.jsx           Light / dark theme context
│   ├── index.html
│   └── package.json
└── README.md
```

---

## Three user flows

| Flow | Description |
|------|-------------|
| **1 – Resume** | Upload a PDF/DOCX **or** build one via a 6-step form → YAML → PDF |
| **2 – Jobs** | Semantic vector matching (Sentence-BERT + PGVector) returns jobs ≥ 80% similarity with contrastive explanations |
| **3 – Roadmap** | Interactive skill tree — check off acquired skills to update your CV and re-rank jobs automatically |

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, Tailwind CSS, React Router |
| PDF generation | jsPDF (browser-side) |
| Backend | Python, Flask (API layer — WIP) |
| CV parsing | pypdf, python-docx, pytesseract (OCR fallback) |
| Embeddings | Sentence-BERT `all-MiniLM-L6-v2` (384-dim) |
| Vector DB | PostgreSQL + PGVector (Supabase) |
| LLM | Qwen 3.5 80b via Ollama (local, CPU-only on Proxmox) |
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
```

**Environment variables** — create `backend/.env`:

```env
# Local Ollama (Qwen 3.5 80b)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:72b
OLLAMA_API_KEY=ollama

# Supabase / PostgreSQL
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-service-role-key
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

---

## Architecture

```
User → Frontend (React)
         │
         ├─ Flow 1: PDF upload / Form → YAML → PDF (browser-side jsPDF)
         │
         ├─ Flow 2: CV embeddings ──► PGVector search ──► Top jobs (≥80%)
         │                                                      │
         │                                               Contrastive explanation
         │                                               (LLM via Ollama)
         │
         └─ Flow 3: Gap analysis ──► Roadmap JSON ──► Interactive skill tree
                                        │
                                  Mark skill acquired
                                        │
                                 CV updated + jobs re-ranked
```

---

## Key design decisions

- **80% match threshold** — empirically set to eliminate false positives that appear at 70%
- **Sentence-BERT over keyword matching** — handles synonyms ("JS" ↔ "JavaScript", "Full Stack" ↔ "Web Developer")
- **Local-only storage** — CV files and personal data never leave the machine (Privacy by Design)
- **English-only UI** — avoids Hebrew grammatical gender bias in embeddings
- **CPU inference** — Qwen 3.5 80b runs on 256 GB RAM / 12-core Proxmox host without GPU; ~4–5 min/request
