# ResuMind Project Progress

Last updated: 2026-09-07

## Project overview

ResuMind is an AI-assisted career platform with three main flows:

1. Upload or create a resume and receive improvement suggestions.
2. Match a saved resume against job postings using semantic similarity.
3. Track acquired and missing skills through a role-based career roadmap.

The application consists of a React/Vite frontend and a FastAPI backend. The README still refers to Flask in places, but the active API implementation uses FastAPI.

## Work completed

### User market statistics (2026-09-07)

- Added **Your statistics** to desktop and mobile navigation with a protected
  `/statistics` page.
- Added authenticated, read-only `GET /api/user/statistics`. It uses the exact
  matching profile and all jobs above the existing semantic recommendation
  threshold; no chat-model request or database write is involved.
- Each normalized skill is counted once per job. The page shows recommended-job
  count, average estimated fit, fit distribution, most demanded skills already
  in the profile, most demanded profile gaps, and the top 50 skills overall.
  Every percentage includes its numerator and denominator.
- Wording distinguishes a skill mention from a mandatory requirement because
  source postings may describe required, preferred or alternative technologies.
  Fit remains a product score rather than hiring probability.
- Verification: 55 backend tests and the production frontend build pass. A
  mocked browser test covers authentication, the Docker 70% example, strongest
  skills, methodology, desktop/mobile navigation and responsive width. A
  read-only real-data check calculated aggregates across 790 matched jobs, 784
  with recognizable skills, without exposing resume text or changing user data.
  Deployed to `http://192.168.1.99:8000`; the container is healthy and the
  deployed statistics browser check passes. The previous recommendation-only
  container is retained as `resumind-before-statistics-20260907`.

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

### Match explanations and full job details (2026-09-07)

- Added an on-demand **Why this match?** panel to the selected job: actual
  semantic/coverage score contributions, up to three related CV/posting excerpt
  pairs, CV-versus-roadmap skill evidence, and grounded improvement suggestions.
- The new authenticated `GET /api/user/jobs/{job_id}/explanation` endpoint shares
  the exact matching-profile loader with job ranking. It uses local Sentence-BERT
  inference, not llama.cpp or an external proxy, and does not write user data.
- Excerpt comparisons are labelled as separate illustrative similarities, not
  causal model reasoning or additive parts of the overall semantic score.
  Work is bounded to 32 excerpts per document, each at most 320 characters.
- Added an input-window notice: the bundled model embeds at most 256 tokens of
  a matching profile. Explicit skill coverage still checks the full profile.
  Contact emails and phone numbers are redacted before excerpt comparison.
- Subsequently removed the token-count warning at the user's request, including
  its duplicate under **How this explanation works**. Internal token diagnostics,
  the embedding input limit and all scoring behavior remain unchanged.
  This update is deployed; all 46 backend tests and the browser checks passed.
  Live API checks confirm the warning is absent. The prior container is retained
  as `resumind-before-remove-token-warning-20260907` for rollback.
- Added **Full job details** beside **Apply**, with all saved description and
  requirements text, benefits and available posting/company/salary metadata.
  Imported HTML is converted to plain text; application links accept only
  HTTP/HTTPS. The dialog supports Escape, backdrop dismissal, focus restoration,
  background-scroll locking and mobile scrolling.
- The UI explains the ingestion limit: saved descriptions may stop at 4,000
  characters; source listings can change or close. Opening details does not fetch
  the original website or silently claim the saved record is complete/current.
- Verification: 46 deterministic backend tests, frontend production build and
  Docker build passed. Chrome checks passed in production and React StrictMode,
  covering on-demand loading, retry after HTML errors, request cancellation when
  changing jobs, safe/missing links, full text, keyboard controls and mobile layout.
  Existing job-to-roadmap navigation and Learn-visibility regression checks passed.
- Read-only candidate checks against the existing database covered three profiles
  and four explanations. Existing job responses (excluding new display-text fields),
  scores and order matched the prior deployment exactly. Warm explanation requests
  took approximately 0.18–0.54 seconds in these checks; these are smoke-test timings,
  not a load benchmark. Authentication and missing-profile/job/embedding errors
  were checked without changing resumes or progress.
- Deployed the updated image to `http://192.168.1.99:8000`. The container is
  healthy, and live authenticated explanation checks passed for the same three
  profiles (approximately 0.35–0.40 seconds per explanation). The deployed frontend
  also passed the mocked-API browser suite. The previous container is retained as
  `resumind-before-match-explanation-20260907` for rollback. No Git commit or push
  was made.

### Job skill comparison fix (2026-09-07)

- Only 523 of the 33,040 stored jobs have a nonempty `skills_desc` field. Jobs,
  job-specific Roadmap panels and the resume coach now also extract named skills
  from the job description using a shared technology vocabulary and aliases.
- Existing explicit skills are merged with description mentions and deduplicated.
  This runs at request time and does not require re-ingestion or an LLM call.
- Matched and missing skills, profile evidence and skill coverage use the same
  extracted list. Skill coverage can therefore affect estimated-fit scores for
  jobs that previously had no skills information available to the comparison.
- Empty panels distinguish unavailable job information from full coverage.
  Description mentions may include preferred skills or alternatives; they are
  not a complete, validated list of mandatory requirements.
- Fourteen helper tests cover extraction, real job prose, aliases, HTML, text
  boundaries, acquired roadmap skills, missing data and the existing scoring rules.
- Deployed to `192.168.1.99:8000` and verified the served frontend and authenticated
  APIs. All ten returned jobs for a test profile had populated skill comparisons;
  the previously empty Java posting produced 28 detected skills. The prior
  container is stopped as `resumind-before-skill-fix-20260907` for rollback.

### Fit ordering and roadmap fixes (2026-09-07)

- Jobs now sort all eligible candidates by displayed fit before pagination,
  with deterministic tie-breakers. Title sorting and filters remain available.
  Shared job-skill extraction is cached; user-specific matching is not cached.
- Role roadmaps recover explicitly detectable CV skills when onboarding AI
  detection fails. Thinking wrappers are stripped before parsing AI output,
  and onboarding retains deterministic CV evidence if the model is unavailable.
- Added `user_skills.manual_override` and an idempotent migration to preserve
  explicit check/uncheck choices. Legacy updates after onboarding are treated as
  manual choices; older history cannot be identified perfectly from timestamps.
- Build roadmap now creates a plan from the selected posting's detected skills,
  rather than reusing the onboarding role. Known catalog skills supply suggested
  stages; other detected skills start at Core Tools. Job skills have equal weight.
- Job-specific progress is stored under `role = 'job:<job_id>'`; it does not
  change the user's target role. Job coverage panels reflect saved learning.
- Any stage's skills can be marked learned. Loading state resets on navigation,
  stale requests are cancelled, saves are serialized, and failed saves display
  an error with retry rather than silently reverting.
- Verification: 26 helper tests, frontend/Docker builds, and browser interaction
  checks (mocked APIs) pass. Candidate APIs were checked against the real database:
  75 jobs stayed descending across three pages, and three selected jobs produced
  different relevant plans (10, 13 and 28 skills). The affected role's nine CV
  skills yield 67% weighted progress. Offline-model onboarding still detected
  six skills from a synthetic CV. All integration-test writes were rolled back.
- One candidate timing sample: the first request including model startup took
  8.71 seconds; the next two pages took 0.12 and 0.13 seconds. These are smoke-test
  timings, not a load test or recommendation-quality evaluation.
- Deployed and verified on `192.168.1.99:8000`; the container is healthy. Live
  authenticated checks confirmed descending fit across two pages, correct role
  and selected-job plans, and the updated frontend bundle. The migration passed
  repeated execution tests in an isolated schema that was rolled back.
  Previous container: `resumind-before-roadmap-fix-20260907` (stopped, retained
  for rollback). Changes remain uncommitted and have not been pushed to GitHub.

### Roadmap learning resources (2026-09-07)

- Added an expandable Learn section below every skill, for both role and
  job-specific roadmaps. Reading a guide is separate from marking progress.
- Added a maintained resource catalog covering all 159 unique stored role skills
  and all 184 named skills recognized in job descriptions. Canonical aliases
  share resources; each response contains up to three deduplicated links.
- Sources include roadmap.sh paths and official guides from Python, Docker,
  Kubernetes, HashiCorp, MDN, Google, Apple, OWASP and the relevant tool authors.
  Unknown future labels receive explicitly labelled search links.
- Reviewed 217 unique catalog URLs. Corrected moved Trivy, Splunk, Retrofit,
  Cassandra, Confluence and Salesforce links. Some providers block automated
  HTTP requests; their pages were reviewed through web sources instead.
  Added an optional link-check script for future maintenance.
- No new database fields or runtime web/AI calls. Resource URLs contain no
  resume/account data, use HTTPS, and suppress referrers on navigation.
- Thirty-four deterministic tests and the production frontend/Docker builds
  pass. Browser checks with mocked APIs cover role/job resources, keyboard
  expansion, new tabs, unchanged progress, search fallbacks, unsafe-URL rejection
  and mobile layout; the earlier roadmap-interaction regression checks also pass.
- Deployed to `192.168.1.99:8000` and verified authenticated responses for three
  existing profiles on their role roadmap and two selected-job plans. Candidate
  responses match the previous API exactly after removing the new resource field;
  no saved profiles or progress were modified. The previous healthy container is
  retained as `resumind-before-learning-resources-20260907`. Not committed/pushed.
- Learn sections now hide for acquired skills and reappear when unchecked,
  including previously saved/CV-detected progress. Browser tests cover both
  roadmap modes, reloads and failed-save rollback; all 34 backend tests still pass.
  Deployed and verified the updated frontend and health endpoint. Previous
  container: `resumind-before-learn-visibility-20260907`; no database changes.

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

The API removes results below `0.60` cosine similarity and applies the requested
filters. It ranks the remaining jobs by displayed fit: 75% semantic similarity
plus 25% detected skill coverage. If no job skills can be identified, the score
uses semantic similarity alone. Authenticated jobs are paginated (25 by default);
the upload-based endpoint returns ten. Fit is a bounded product score, not a
probability of hiring or a validated success rate.

`all-MiniLM-L6-v2` was selected as a practical baseline because it is small, fast on CPU, works locally, and supports semantic matching better than simple keyword comparison. A future improvement would retrieve a larger candidate set and rerank it with a cross-encoder.

The same candidate set feeds **Your statistics**. For each skill, demand is
calculated as `jobs mentioning the skill / all recommended jobs * 100`. Skill
aliases are normalized, and repeated mentions inside one posting count only once.
The page reports how many postings had recognizable skill data because a detected
mention is not guaranteed to be a mandatory requirement.

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

`GET /api/user/roadmap` does not call the LLM when the page loads. It joins
predefined `role_skills` with `user_skills`, uses explicit CV evidence unless
manually overridden, and calculates progress from stored skill weights. With
`job_id`, it builds a plan from that posting's detected skills and saved
job-specific learning progress instead; coverage uses equal skill weights.

During onboarding, deterministic CV detection is combined with allowed skills
identified by the LLM. If the model fails or returns malformed output, the CV
detection remains available. Explicit check/uncheck actions take precedence on
later page loads; re-onboarding resets detection for the selected role.

## Data storage

The application uses one PostgreSQL database:

- Host: `192.168.1.77`
- Port: `5432`
- Database: `postgres`
- PGVector is an extension in this database, not a separate database.

Application tables referenced by the code:

- `users`: email address and password hash.
- `user_profiles`: extracted resume text, original filename, desired role, and onboarding status.
- `user_skills`: acquired state and manual-override flag for role and job-specific skills.
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
- Added GitHub and CI/CD to the DevOps roadmap. Git and GitHub remain separate
  cards but share CV detection and manually saved progress.

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
