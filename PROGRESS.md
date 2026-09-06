# ResuMind Project Progress

Last updated: 2026-09-06

## Project overview

ResuMind is an AI-assisted career platform with three main flows:

1. Upload or create a resume and receive improvement suggestions.
2. Match a saved resume against job postings using semantic similarity.
3. Track acquired and missing skills through a role-based career roadmap.

The application consists of a React/Vite frontend and a FastAPI backend. The README still refers to Flask in places, but the active API implementation uses FastAPI.

## Work completed

### Project inspection and startup

- Inspected the frontend, backend, recommendation engine, authentication flow, ingestion scripts, and runtime configuration.
- Confirmed that the frontend production build succeeds.
- Confirmed that the FastAPI application imports and starts successfully.
- Confirmed that the Vite `/api` proxy communicates with the backend.
- Previously tested the application on:
  - Frontend: `http://127.0.0.1:5173`
  - Backend: `http://127.0.0.1:8000`
  - FastAPI documentation: `http://127.0.0.1:8000/docs`
- The local frontend and backend development servers are not running as of this update.

### Resume replacement flow

The navigation bar now provides an account menu when the user clicks their email address.

- Added **Upload a new resume** to the desktop account menu.
- Added the same action to the mobile navigation menu.
- The action returns the user to the existing onboarding flow.
- Completing onboarding replaces the stored resume text, filename, target role, and detected skills.
- The dropdown closes when the user clicks outside it or presses Escape.
- Sign out is now included in the account menu.

Changed file:

- `frontend/src/components/Navbar.jsx`

The frontend production build passes with this change.

### Active LLM alignment

- Queried the llama.cpp OpenAI-compatible `/v1/models` endpoint to obtain the active model ID.
- Configured the deployed app to use `Qwen3.8-27B-UD-Q4_K_XL.gguf`.
- Kept the API base URL at `http://192.168.1.72:8080/v1`.
- Verified from the response headers and running process that port 8080 is the
  llama.cpp server itself. LiteLLM is not in the request path.
- Verified the configuration through the same Python OpenAI client used by the backend.
- The configured model and response model both reported `Qwen3.8-27B-UD-Q4_K_XL.gguf`.
- The test inference returned `ResuMind AI ready` successfully.

The FastAPI backend must be restarted after an environment change because it reads the model name during application startup.

### Resume coach and job-specific CV fitting

- The Resume page is split into role-based coaching and job-specific CV fitting.
- The role coach uses the same role catalog as the Roadmap page.
- The job coach uses the selected job's title, company, description, required
  skills, experience level, and deterministic skill-gap analysis as context.
- Resume contact details are redacted before context is sent to the model.
- The Qwen chat template now receives `enable_thinking=false` for these concise,
  structured tasks.
- Resume-coach responses are capped at 650 tokens; roadmap and onboarding calls
  have separate bounded output limits.
- Automatic OpenAI-client retries are disabled because llama.cpp currently has
  one request slot and a retry would only add another slow request to its queue.
- The frontend now detects non-JSON server responses and displays a useful error
  instead of `Unexpected token '<'`.

The original failure was caused by a request using the llama.cpp server default
of 4,096 output tokens with Qwen reasoning enabled. It monopolised the only model
slot, causing subsequent browser requests to wait and eventually receive a
timeout response. A direct no-thinking test completed in about 1.1 seconds. The
full authenticated CV analysis for job `3901961133` completed successfully with
HTTP 200 in 17.44 seconds and returned an overall verdict, four strengths, four
gaps, four improvements, and eight keywords.

### Docker deployment

The production image is deployed directly on the Proxmox Docker VM:

- Application host: `192.168.1.99`
- Application URL: `http://192.168.1.99:8000`
- Container: `resumind`
- Image: `resumind:local`
- Published port: `8000:8000`
- Restart policy: `unless-stopped`
- Runtime environment file: `/etc/resumind/resumind.env`

The container is healthy and its database connection to PostgreSQL/PGVector at
`192.168.1.77:5432` has been verified. The application image does not contain
llama.cpp, Ollama, LiteLLM, or PostgreSQL; those services remain external.

## Recommendation system

The recommendation system uses NLP and a pretrained embedding model:

- Model: `all-MiniLM-L6-v2`
- Library: Sentence Transformers
- Embedding size: 384 dimensions
- Vector database: PostgreSQL with PGVector

During job ingestion, the title, description, and skills of every technology-related job are combined and converted into an embedding. When a user requests recommendations, the saved resume text is converted into an embedding using the same model.

PGVector calculates cosine similarity with:

```sql
1 - (embedding <=> resume_vector)
```

The API removes results below `0.60`, orders the remaining jobs by similarity, and returns the top ten. Displayed scores are normalized into a 70–97 range and are therefore not literal cosine-similarity percentages.

`all-MiniLM-L6-v2` was selected as a practical baseline because it is small, fast on CPU, works locally, and supports semantic matching better than simple keyword comparison. A future improvement would retrieve a larger candidate set and rerank it with a cross-encoder.

## RAG and roadmap behavior

The project contains two related roadmap paths.

### Generative roadmap endpoint

`POST /api/roadmap`:

1. Extracts text from a submitted resume.
2. Retrieves a selected job from PostgreSQL by `job_id`.
3. Sends resume text, job description, and required skills to the LLM.
4. Requests structured JSON containing acquired skills, missing skills, resources, impacts, and a match score.

This is a small retrieval-augmented generation flow because retrieved job data grounds the generated answer. It does not perform vector retrieval inside the roadmap endpoint itself.

### Authenticated roadmap UI

`GET /api/user/roadmap` does not call the LLM when the page loads. It joins predefined `role_skills` with the user's `user_skills` and calculates progress from stored skill weights.

During onboarding, the LLM receives the resume and the predefined skill list for the selected role. It identifies skills already present in the resume, and those results are stored for later use.

## Data storage

The application uses one PostgreSQL database:

- Host: `192.168.1.77`
- Port: `5432`
- Database: `postgres`
- PGVector is an extension in this database, not a separate database.

Application tables referenced by the code:

- `users`: email address and password hash.
- `user_profiles`: extracted resume text, original filename, desired role, and onboarding status.
- `user_skills`: acquired state for each user's role skills.
- `role_skills`: predefined skills, stages, categories, and weights for each role.
- `jobs`: job details and vector embeddings.

Passwords are hashed with PBKDF2-SHA256 and are not stored as plaintext.

Uploaded PDF and DOCX files are used temporarily for text extraction and then deleted. The database retains the extracted text and original filename, not the original uploaded file.

After login, the frontend stores a 30-day JWT in browser `localStorage` under `rm_token`. It does not store the user's password or resume in browser storage.

## llama.cpp server

Server address: `192.168.1.72`

Hardware observed during setup:

- Ubuntu 24.04
- Intel Xeon W-2150B, 20 logical CPUs
- 128 GiB RAM
- NVIDIA RTX A4000, 16 GiB
- NVIDIA RTX A2000, 12 GiB
- CUDA-enabled llama.cpp build

The server was initially tested successfully with Gemma 4 26B-A4B Instruct through the OpenAI-compatible endpoint on port 8080. The project's Python OpenAI client returned `ResuMind AI ready` in that test.

### Current server state

As of 2026-09-06, llama.cpp is healthy at:

```text
http://192.168.1.72:8080/v1
```

It currently serves:

```text
Qwen3.8-27B-UD-Q4_K_XL.gguf
```

Current server characteristics include:

- 65,536-token context
- Both NVIDIA GPUs
- Flash attention
- Quantized KV cache
- MTP speculative decoding
- One parallel request slot
- Direct OpenAI-compatible API; no LiteLLM proxy

## Current model configuration

The project currently has this model configured in `backend/.env`:

```env
OLLAMA_BASE_URL=http://192.168.1.72:8080/v1
OLLAMA_MODEL=Qwen3.8-27B-UD-Q4_K_XL.gguf
LLM_TIMEOUT_SECONDS=120
LLM_MAX_TOKENS=900
```

This matches the model ID currently advertised by llama.cpp. A direct inference through the project's backend client completed successfully and confirmed that the response came from the same model ID.

No database password, JWT secret, SSH key, or other credential is included in this document.

## Remaining work

1. Complete a final manual browser pass for onboarding, resume coaching, jobs,
   and roadmap behavior.
2. Add a systemd unit for llama.cpp so it starts automatically after a reboot.
3. Publish the app through the planned Cloudflare Tunnel and configure its public hostname.
4. Evaluate recommendation quality with labeled resume-to-job examples before
   changing the embedding model or similarity threshold.

## Current working-tree improvements (not committed)

- Added deterministic skill aliases, skill coverage, evidence excerpts, bounded fit scoring, and contact-PII redaction before AI/embedding calls.
- Added pageable and filterable authenticated job search across the catalog, including remote, work type, experience, industry, and salary filters when enriched job columns are present.
- Added job-specific roadmap context and made acquired roadmap skills influence the matching profile.
- Added the ability to save a resume created by the browser builder to the authenticated profile.
- Added enriched job ingestion for salary, benefits, industries, company size, employee counts, and posting dates.
- Added an idempotent `backend/schema.sql`, `backend/.env.example`, safer upload/auth validation, clear scanned-PDF errors, and deterministic backend tests.
- Updated the landing page and README to describe the active FastAPI behavior and explainable score instead of the previous 80%/contrastive-explanation claims.
- Added role-based and job-specific CV coaching grounded in Roadmap roles and
  real job records.
- Added bounded direct llama.cpp requests, disabled extended Qwen thinking for
  structured tasks, and made frontend AI-response parsing resilient.
- Added and deployed the Docker production image on `192.168.1.99`; backend unit
  tests and the frontend production build pass.

## Useful development commands

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Frontend production check:

```bash
cd frontend
npm run build
```
