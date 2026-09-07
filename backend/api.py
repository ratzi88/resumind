import os
import re
import json
import tempfile
from pathlib import Path
from typing import Optional
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from scraper import scrape_file, get_file_extension
from auth import hash_password, verify_password, create_token, get_current_user_id
from matching import analyze_skills, analyze_job_skills, compute_match_pct, normalize_skill_name, redact_pii, rank_job_matches, extract_job_skills
from roadmap import resolve_role_progress, build_job_roadmap, apply_job_progress
from learning_resources import with_learning_resources
from job_explanations import explain_job_match, posting_plain_text

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": _model,
        "embedding_model": EMBEDDING_MODEL,
        "match_threshold": MATCH_THRESHOLD,
    }

# ── clients ───────────────────────────────────────────────────────────────────
llm = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
    timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
    # Retrying a generation on a single-slot llama.cpp server only adds another
    # long request to the queue. Let the caller retry deliberately instead.
    max_retries=0,
)
_model = os.getenv("OLLAMA_MODEL", "qwen2.5:72b")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "900"))
_embedder: SentenceTransformer | None = None
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.60"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEFAULT_JOB_LIMIT = 25
MAX_JOB_LIMIT = 50

BASE_JOB_COLUMNS = (
    "job_id", "title", "company", "location", "description", "skills_desc",
    "experience_level", "work_type", "remote", "apply_url",
)
OPTIONAL_JOB_COLUMNS = (
    "max_salary", "med_salary", "min_salary", "pay_period", "currency",
    "compensation_type", "listed_time", "expiry", "closed_time", "industry",
    "company_size", "employee_count", "benefits",
)


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _chat(messages, *, max_tokens: Optional[int] = None):
    """Call the local model with a user-friendly API error on failure."""

    try:
        response = llm.chat.completions.create(
            model=_model,
            messages=messages,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            temperature=0.2,
            # llama.cpp forwards this to Qwen's chat template. Resume analysis
            # needs a concise structured answer, not a multi-thousand-token
            # hidden reasoning pass that monopolises the only inference slot.
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
                "reasoning_format": "none",
            },
        )
        content = response.choices[0].message.content if response.choices else ""
        # Some local templates include empty thinking tags even with thinking
        # disabled. Remove those wrappers before downstream JSON parsing.
        content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S | re.I).strip()
        if not content:
            raise ValueError("The model returned an empty response")
        return content
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            503,
            "The AI model took too long or is unavailable. Please try again shortly.",
        ) from exc


def get_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(503, "DATABASE_URL is not configured.")
    return psycopg2.connect(database_url)


def _load_role_progress(cur, user_id: int, role: str, resume_text: str) -> list[dict]:
    cur.execute(
        """
        SELECT rs.skill_name, rs.category, rs.stage, rs.impact,
               COALESCE(us.acquired, FALSE) AS acquired,
               COALESCE(us.manual_override, FALSE) AS manual_override
        FROM role_skills rs
        LEFT JOIN user_skills us
          ON us.skill_name = rs.skill_name AND us.user_id = %s AND us.role = rs.role
        WHERE rs.role = %s
        ORDER BY rs.stage, rs.impact DESC
        """,
        (user_id, role),
    )
    return resolve_role_progress(cur.fetchall(), resume_text)


def _existing_job_columns(cur) -> set[str]:
    """Keep the API compatible with databases created before enrichment."""

    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'jobs'"
    )
    return {row["column_name"] for row in cur.fetchall()}


def _load_matching_profile(cur, user_id: int) -> dict:
    """Use identical CV/progress inputs for ranking and its explanation."""
    cur.execute("SELECT resume_text, desired_role FROM user_profiles WHERE user_id = %s", (user_id,))
    profile = cur.fetchone()
    if not profile or not profile['resume_text']:
        raise HTTPException(400, "No resume found. Complete onboarding first.")
    role_skills = _load_role_progress(cur, user_id, profile['desired_role'], profile['resume_text'])
    acquired = [row['skill_name'] for row in role_skills if row['acquired']]
    cur.execute("SELECT DISTINCT skill_name FROM user_skills WHERE user_id = %s AND role LIKE 'job:%%' AND acquired = TRUE", (user_id,))
    acquired = sorted(set(acquired) | {row['skill_name'] for row in cur.fetchall()})
    career_text = redact_pii(profile['resume_text'])
    if acquired:
        career_text += '\nAcquired roadmap skills: ' + ', '.join(acquired)
    return {'resume_text': profile['resume_text'], 'career_text': career_text}


def _job_select_clause(columns: set[str]) -> str:
    selected = []
    for column in BASE_JOB_COLUMNS + OPTIONAL_JOB_COLUMNS:
        if column in columns:
            selected.append(f"j.{column} AS {column}")
        else:
            selected.append(f"NULL AS {column}")
    return ",\n            ".join(selected)


def _query_job_matches(
    cur,
    cv_embedding: list[float],
    *,
    threshold: float = MATCH_THRESHOLD,
    query: Optional[str] = None,
    remote: Optional[bool] = None,
    work_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    industry: Optional[str] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
):
    """Retrieve filtered candidates; full fit ranking precedes pagination."""

    if min_salary is not None and max_salary is not None and max_salary < min_salary:
        raise HTTPException(422, "Maximum salary must be greater than minimum salary.")
    columns = _existing_job_columns(cur)
    if (min_salary is not None or max_salary is not None) and not {
        "min_salary", "med_salary", "max_salary"
    }.issubset(columns):
        raise HTTPException(400, "Salary filters require the enriched jobs schema.")
    if industry and "industry" not in columns:
        raise HTTPException(400, "Industry filters require the enriched jobs schema.")

    conditions = []
    params: list[object] = [cv_embedding]
    if query:
        like = f"%{query.strip()}%"
        conditions.append("(j.title ILIKE %s OR j.company ILIKE %s OR j.skills_desc ILIKE %s)")
        params.extend([like, like, like])
    if remote is not None:
        conditions.append("j.remote = %s")
        params.append(remote)
    if work_type:
        conditions.append("j.work_type = %s")
        params.append(work_type)
    if experience_level:
        conditions.append("j.experience_level = %s")
        params.append(experience_level)
    if industry:
        conditions.append("j.industry ILIKE %s")
        params.append(f"%{industry.strip()}%")
    if min_salary is not None:
        conditions.append("COALESCE(j.max_salary, j.med_salary, j.min_salary) >= %s")
        params.append(min_salary)
    if max_salary is not None:
        conditions.append("COALESCE(j.min_salary, j.med_salary, j.max_salary) <= %s")
        params.append(max_salary)

    source_filter = "\n        AND ".join(conditions)
    if source_filter:
        source_filter = "\n        AND " + source_filter

    params.append(threshold)
    cur.execute(
        f"""
        WITH scored AS (
          SELECT
            {_job_select_clause(columns)},
            1 - (j.embedding <=> %s::vector) AS raw_score
          FROM jobs j
          WHERE j.embedding IS NOT NULL{source_filter}
        )
        SELECT scored.*, COUNT(*) OVER() AS total_count
        FROM scored
        WHERE raw_score >= %s
        ORDER BY raw_score DESC, job_id ASC
        """,
        params,
    )
    return cur.fetchall(), columns


def _format_job_rows(rows, resume_text: str) -> tuple[list[dict], int]:
    result = []
    total = int(rows[0]["total_count"]) if rows else 0
    for row in rows:
        job = dict(row)
        raw_score = float(job.pop("raw_score") or 0)
        job.pop("total_count", None)
        explanation = analyze_job_skills(resume_text, job.get("skills_desc"), job.get("description"))
        job["semantic_similarity"] = round(max(0.0, min(1.0, raw_score)), 4)
        job["skill_coverage_pct"] = explanation["coverage_pct"]
        job["match_pct"] = compute_match_pct(
            raw_score,
            len(explanation["matched_skills"]),
            len(explanation["required_skills"]),
        )
        job["match_details"] = explanation
        job["description_text"] = posting_plain_text(job.get("description"))
        job["skills_text"] = posting_plain_text(job.get("skills_desc"))
        if isinstance(job.get("benefits"), str):
            job["benefits"] = [b.strip() for b in job["benefits"].split(";") if b.strip()]
        result.append(job)
    return result, total


# ── helpers ───────────────────────────────────────────────────────────────────

def extract_text(file: UploadFile) -> str:
    filename = file.filename or ""
    ext = get_file_extension(filename)
    if ext not in (".pdf", ".docx"):
        raise HTTPException(400, "Only PDF and DOCX files are supported.")
    contents = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Files must be smaller than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        text = scrape_file(tmp_path, ext)
    finally:
        os.unlink(tmp_path)
    if not text or not text.strip():
        raise HTTPException(422, "Could not extract text from the file.")
    return text


# ── Flow 1 — resume suggestions ───────────────────────────────────────────────

SUGGEST_PROMPT = """\
/no_think
You are an expert tech-industry career coach. Analyse the resume below for the target role and respond ONLY in this exact format — no extra text before or after:

OVERALL: <one concise sentence verdict>

STRENGTHS:
- <what the candidate already does well, max 4 bullets>

GAPS:
- <skills or experience missing for the target role, max 4 bullets>

IMPROVEMENTS:
- <specific, actionable rewording or structural fixes, max 4 bullets>

KEYWORDS: <comma-separated list of 5-8 keywords the resume should add>

Rules:
- Every bullet must be a single sentence, under 15 words.
- Do NOT invent experience the candidate does not have.
- Use the specific job posting and required skills as the primary source when provided.
- Use roadmap skill gaps to prioritise practical improvements.
- Never repeat or request private contact details.
- Do NOT add greetings, conclusions, or any text outside the format above.
"""


def _parse_suggest(raw: str) -> dict:
    def section(tag):
        m = re.search(rf"{tag}:\s*\n(.*?)(?=\n[A-Z]+:|$)", raw, re.S | re.I)
        if not m:
            return []
        return [
            re.sub(r"^[-*•]\s*", "", l).strip()
            for l in m.group(1).splitlines()
            if l.strip() and re.match(r"^[-*•]", l.strip())
        ]
    overall_m  = re.search(r"OVERALL:\s*(.+)", raw, re.I)
    keywords_m = re.search(r"KEYWORDS:\s*(.+)", raw, re.I)
    return {
        "overall":      overall_m.group(1).strip() if overall_m else "",
        "strengths":    section("STRENGTHS"),
        "gaps":         section("GAPS"),
        "improvements": section("IMPROVEMENTS"),
        "keywords":     [k.strip() for k in keywords_m.group(1).split(",") if k.strip()] if keywords_m else [],
    }


def _role_slug_for_title(job_title: str) -> Optional[str]:
    normalized = re.sub(r"\s+", " ", str(job_title or "").strip()).casefold()
    return next(
        (slug for slug, label in ROLE_DISPLAY.items() if label.casefold() == normalized),
        None,
    )


def _build_suggest_context(
    cur,
    resume_text: str,
    job_title: Optional[str],
    *,
    job_id: Optional[str] = None,
    user_id: Optional[int] = None,
    desired_role: Optional[str] = None,
) -> str:
    """Build grounded context for the coach from the role roadmap and job data."""

    target_role = str(job_title or "").strip()
    role_slug = _role_slug_for_title(target_role) or desired_role
    redacted_resume = redact_pii(resume_text)
    sections = []

    if job_id:
        cur.execute(
            "SELECT title, company, description, skills_desc, experience_level "
            "FROM jobs WHERE job_id = %s",
            (job_id,),
        )
        job = cur.fetchone()
        if not job:
            raise HTTPException(404, "Selected job was not found.")
        # The database job is authoritative; the coach is job-first.
        target_role = str(job['title'] or target_role).strip()
        role_slug = _role_slug_for_title(target_role) or desired_role

        job_lines = [
            f"Title: {job['title']}",
            f"Company: {job['company']}" if job.get('company') else "",
            f"Experience level: {job['experience_level']}" if job.get('experience_level') else "",
            f"Description:\n{str(job['description'])[:2500]}" if job.get('description') else "",
            f"Required skills: {job['skills_desc']}" if job.get('skills_desc') else "",
        ]
        sections.append("SPECIFIC JOB POSTING:\n" + "\n".join(line for line in job_lines if line))

        job_analysis = analyze_job_skills(redacted_resume, job.get('skills_desc'), job.get('description'))
        if job_analysis['required_skills']:
            sections.append(
                "JOB SKILL CHECK:\n"
                "These are skills mentioned in the posting; some may be preferred or alternatives.\n"
                f"Skills shown in resume: {', '.join(job_analysis['matched_skills']) or 'None'}\n"
                f"Skills not found in resume: {', '.join(job_analysis['missing_skills']) or 'None'}"
            )

    if not target_role:
        raise HTTPException(422, "Select a job before analysing the resume.")
    sections.insert(0, f"TARGET ROLE:\n{target_role}")

    if role_slug and not job_id:
        cur.execute(
            "SELECT skill_name FROM role_skills "
            "WHERE role = %s ORDER BY stage, impact DESC LIMIT 150",
            (role_slug,),
        )
        roadmap_skills = [row['skill_name'] for row in cur.fetchall()]
        if roadmap_skills:
            roadmap_analysis = analyze_skills(redacted_resume, roadmap_skills)
            sections.append(
                f"{ROLE_DISPLAY.get(role_slug, role_slug)} ROADMAP CONTEXT:\n"
                f"Skills shown in resume: {', '.join(roadmap_analysis['matched_skills']) or 'None'}\n"
                f"Roadmap gaps to prioritise: {', '.join(roadmap_analysis['missing_skills']) or 'None'}"
            )

        if user_id:
            progress = _load_role_progress(cur, user_id, role_slug, redacted_resume)
            acquired = [row['skill_name'] for row in progress if row['acquired']]
            if acquired:
                sections.append("ACQUIRED ROADMAP SKILLS (CV DETECTION OR SAVED PROGRESS):\n" + ", ".join(acquired))

    return "\n\n".join(sections)


@app.post("/api/user/suggest")
def user_suggest(
    job_title: Optional[str] = Form(default=None),
    job_id: Optional[str] = Form(default=None, max_length=120),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT resume_text, desired_role FROM user_profiles WHERE user_id = %s",
            (user_id,),
        )
        profile = cur.fetchone()
        if not profile or not profile["resume_text"]:
            raise HTTPException(400, "No resume found. Complete onboarding first.")
        context = _build_suggest_context(
            cur,
            profile["resume_text"],
            job_title,
            job_id=job_id,
            user_id=user_id,
            desired_role=profile.get("desired_role"),
        )
    finally:
        cur.close()
        conn.close()
    raw = _chat([
        {"role": "system", "content": SUGGEST_PROMPT},
        {
            "role": "user",
            "content": f"{context}\n\nRESUME:\n{redact_pii(profile['resume_text'])[:5000]}",
        },
    ], max_tokens=650)
    return _parse_suggest(raw)


@app.post("/api/suggest")
def suggest(
    file: UploadFile = File(...),
    job_title: Optional[str] = Form(default=None),
    job_id: Optional[str] = Form(default=None, max_length=120),
):
    file.file.seek(0)
    resume_text = redact_pii(extract_text(file))
    context = f"TARGET ROLE:\n{str(job_title or '').strip()}"
    if job_id or _role_slug_for_title(str(job_title or '')):
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            context = _build_suggest_context(cur, resume_text, job_title, job_id=job_id)
        finally:
            cur.close()
            conn.close()
    raw = _chat([
        {"role": "system", "content": SUGGEST_PROMPT},
        {"role": "user", "content": f"{context}\n\nRESUME:\n{resume_text[:5000]}"},
    ], max_tokens=650)
    return _parse_suggest(raw)


# ── Flow 2 — job matching ─────────────────────────────────────────────────────

@app.post("/api/jobs")
def jobs(file: UploadFile = File(...)):
    file.file.seek(0)
    resume_text = redact_pii(extract_text(file))

    embedder = get_embedder()
    cv_embedding = embedder.encode(resume_text, normalize_embeddings=True).tolist()

    conn = get_db()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        rows, _ = _query_job_matches(cur, cv_embedding)
        total = len(rows)
        ranked = rank_job_matches(rows, resume_text, limit=10)
        result, _ = _format_job_rows(ranked, resume_text)
        return {"jobs": result, "total": total, "score_method": "semantic + skill coverage"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ── Flow 3 — RAG roadmap ──────────────────────────────────────────────────────

ROADMAP_PROMPT = """\
You are a senior tech career coach. Given a candidate's resume and a target job description, identify the skill gaps and produce a career roadmap.

Respond ONLY in this exact JSON format — no markdown fences, no extra text:
{{
  "target_role": "<job title>",
  "score": <integer 0-100 representing current fit>,
  "skills_acquired": [
    {{"id": "s1", "name": "<skill>", "category": "<category>", "impact": <integer 1-20>}}
  ],
  "skills_to_acquire": [
    {{"id": "g1", "name": "<skill>", "category": "<category>", "impact": <integer 1-20>, "resource": "<short course/topic suggestion>"}}
  ]
}}

Rules:
- skills_acquired: skills the candidate ALREADY HAS from their resume (max 6)
- skills_to_acquire: skills the job requires that the candidate LACKS (max 8)
- impact: how much this skill improves match score (all impacts must sum to ~100)
- category: one of Foundations, Languages, Frameworks, Infrastructure, Engineering, Data, Soft Skills
- Do NOT invent skills the candidate already has.
- Output valid JSON only.
"""


@app.post("/api/roadmap")
def roadmap(file: UploadFile = File(...), job_id: str = Form(...)):
    file.file.seek(0)
    resume_text = redact_pii(extract_text(file))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT title, description, skills_desc FROM jobs WHERE job_id = %s",
        (job_id,),
    )
    job = cur.fetchone()
    cur.close()
    conn.close()

    if not job:
        raise HTTPException(404, "Job not found.")

    job_context = f"Job title: {job['title']}\n"
    if job["description"]:
        job_context += f"Description: {job['description'][:2000]}\n"
    if job["skills_desc"]:
        job_context += f"Required skills: {job['skills_desc']}\n"

    raw = _chat([
        {"role": "system", "content": ROADMAP_PROMPT},
        {"role": "user", "content": f"RESUME:\n{resume_text[:3000]}\n\nJOB:\n{job_context}"},
    ], max_tokens=1200).strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(500, f"Model returned invalid JSON: {raw[:200]}")


# ── Auth ──────────────────────────────────────────────────────────────────────

ROLE_DISPLAY = {
    "backend": "Backend Engineer", "frontend": "Frontend Engineer",
    "full-stack": "Full-Stack Engineer", "devops": "DevOps Engineer",
    "devsecops": "DevSecOps Engineer", "data-engineer": "Data Engineer",
    "machine-learning": "ML Engineer", "cyber-security": "Cybersecurity Engineer",
    "ai-engineer": "AI Engineer", "data-analyst": "Data Analyst",
    "qa": "QA Engineer", "software-architect": "Software Architect",
    "mlops": "MLOps Engineer", "network-engineer": "Network Engineer",
    "android": "Android Developer", "ios": "iOS Developer",
}


@app.get("/api/roles")
def get_roles():
    return {"roles": [{"slug": k, "label": v} for k, v in ROLE_DISPLAY.items()]}


@app.post("/api/auth/register")
def register(email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Enter a valid email address.")
    if len(password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters.")
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM users WHERE email = %s", (email.lower(),))
    if cur.fetchone():
        raise HTTPException(400, "Email already registered.")
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
        (email.lower(), hash_password(password)),
    )
    user_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return {"token": create_token(user_id), "user_id": user_id}


@app.post("/api/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email.lower(),))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    return {"token": create_token(user["id"]), "user_id": user["id"]}


@app.get("/api/auth/me")
def get_me(user_id: int = Depends(get_current_user_id)):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT u.email, p.desired_role, p.onboarding_done, p.resume_filename "
        "FROM users u LEFT JOIN user_profiles p ON p.user_id = u.id "
        "WHERE u.id = %s", (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(404, "User not found.")
    return dict(row)


@app.post("/api/user/resume")
def save_user_resume(
    resume_text: str = Form(...),
    resume_filename: str = Form("resume-generated.txt"),
    user_id: int = Depends(get_current_user_id),
):
    """Save a resume created in the browser so every flow uses the same profile."""

    cleaned_text = re.sub(r"\s+", " ", resume_text or "").strip()
    if len(cleaned_text) < 40:
        raise HTTPException(422, "Add more resume content before saving.")
    if len(cleaned_text) > 50000:
        raise HTTPException(413, "Resume text is too long.")

    filename = os.path.basename(resume_filename or "resume-generated.txt")[:255]
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            INSERT INTO user_profiles
                (user_id, resume_text, resume_filename, onboarding_done)
            VALUES (%s, %s, %s, FALSE)
            ON CONFLICT (user_id) DO UPDATE
              SET resume_text = EXCLUDED.resume_text,
                  resume_filename = EXCLUDED.resume_filename,
                  updated_at = NOW()
            RETURNING desired_role, onboarding_done
            """,
            (user_id, cleaned_text, filename),
        )
        profile = cur.fetchone()
        conn.commit()
        return {
            "ok": True,
            "resume_filename": filename,
            "desired_role": profile["desired_role"] if profile else None,
            "onboarding_done": profile["onboarding_done"] if profile else False,
        }
    finally:
        cur.close()
        conn.close()


# ── Onboarding ────────────────────────────────────────────────────────────────

SKILL_DETECT_PROMPT = """\
You are given a resume and a list of skills for a specific tech role.
Return ONLY a JSON array of skill names from the list that the candidate clearly has based on their resume.
Do NOT include skills not in the provided list.
Do NOT invent skills. Output valid JSON array only, e.g.: ["Python", "Docker", "Git"]
"""


@app.post("/api/onboarding")
def onboarding(
    file: UploadFile = File(...),
    role: str = Form(...),
    user_id: int = Depends(get_current_user_id),
):
    if role not in ROLE_DISPLAY:
        raise HTTPException(400, "Unsupported target role.")
    file.file.seek(0)
    resume_text = extract_text(file)

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Save profile
    cur.execute(
        """
        INSERT INTO user_profiles (user_id, resume_text, resume_filename, desired_role, onboarding_done)
        VALUES (%s, %s, %s, %s, TRUE)
        ON CONFLICT (user_id) DO UPDATE
          SET resume_text = EXCLUDED.resume_text,
              resume_filename = EXCLUDED.resume_filename,
              desired_role = EXCLUDED.desired_role,
              onboarding_done = TRUE,
              updated_at = NOW()
        """,
        (user_id, resume_text, file.filename, role),
    )

    # Load role skills
    cur.execute(
        "SELECT skill_name FROM role_skills WHERE role = %s ORDER BY impact DESC",
        (role,)
    )
    skill_names = [r["skill_name"] for r in cur.fetchall()]
    if not skill_names:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(503, "This role roadmap is not seeded yet.")

    # LLM detects acquired skills — gracefully falls back if LLM is unavailable
    acquired = analyze_skills(redact_pii(resume_text), skill_names)['matched_skills']
    try:
        skills_list = "\n".join(f"- {s}" for s in skill_names[:150])
        raw = _chat([
            {"role": "system", "content": SKILL_DETECT_PROMPT},
            {"role": "user", "content": f"RESUME:\n{redact_pii(resume_text[:3000])}\n\nSKILLS LIST:\n{skills_list}"},
        ], max_tokens=500).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            acquired.extend(skill for skill in parsed if isinstance(skill, str))
    except Exception:
        pass  # CV evidence is still available when AI detection fails.

    # Models sometimes return aliases, different casing, or a short variant
    # of a canonical database skill. Keep only allowed canonical names.
    allowed_skills = {
        normalize_skill_name(skill): skill for skill in skill_names
    }
    acquired_set = {
        allowed_skills[normalize_skill_name(skill)]
        for skill in acquired
        if normalize_skill_name(skill) in allowed_skills
    }

    # Upsert user_skills
    records = [(user_id, role, s, s in acquired_set) for s in skill_names]
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO user_skills (user_id, role, skill_name, acquired, manual_override)
        VALUES %s
        ON CONFLICT (user_id, role, skill_name) DO UPDATE
          SET acquired = EXCLUDED.acquired, manual_override = FALSE, updated_at = NOW()
        """,
        [(*record, False) for record in records],
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Onboarding complete", "skills_detected": len(acquired_set)}


# ── User roadmap (from DB, no LLM) ───────────────────────────────────────────

@app.get("/api/user/roadmap")
def get_user_roadmap(
    job_id: Optional[str] = Query(default=None, max_length=120),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT desired_role, resume_text FROM user_profiles WHERE user_id = %s",
            (user_id,),
        )
        profile = cur.fetchone()
        if not profile or not profile["desired_role"]:
            raise HTTPException(400, "No role set. Complete onboarding first.")

        role = profile["desired_role"]
        skills = _load_role_progress(cur, user_id, role, profile["resume_text"] or "")
        if not skills and not job_id:
            raise HTTPException(503, "This role roadmap is not seeded yet.")

        acquired_names = [s["skill_name"] for s in skills if s["acquired"]]
        career_text = redact_pii(profile["resume_text"] or "")
        if acquired_names:
            career_text += "\nAcquired roadmap skills: " + ", ".join(acquired_names)

        target_job = None
        job_match = None
        if job_id:
            cur.execute(
                """
                SELECT job_id, title, company, location, description, skills_desc,
                       experience_level, work_type, remote, apply_url
                FROM jobs WHERE job_id = %s
                """,
                (job_id,),
            )
            job = cur.fetchone()
            if not job:
                raise HTTPException(404, "Job not found.")
            job_match = analyze_job_skills(career_text, job["skills_desc"], job["description"])
            cur.execute("SELECT skill_name, category, stage FROM role_skills")
            catalog = cur.fetchall()
            cur.execute(
                "SELECT skill_name, acquired FROM user_skills WHERE user_id = %s AND role = %s",
                (user_id, f"job:{job_id}"),
            )
            skills = build_job_roadmap(job_match, catalog, cur.fetchall())
            job_match = apply_job_progress(job_match, skills)
            target_job = {
                "job_id": job["job_id"],
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "description": (job["description"] or "")[:1200],
                "required_skills": job_match["required_skills"],
                "experience_level": job["experience_level"],
                "work_type": job["work_type"],
                "remote": job["remote"],
                "apply_url": job["apply_url"],
            }
    finally:
        cur.close()
        conn.close()

    total  = sum(s["impact"] for s in skills)
    earned = sum(s["impact"] for s in skills if s["acquired"])
    score  = round(earned / total * 100) if total else 0

    return {
        "role": role,
        "role_label": target_job["title"] if target_job else ROLE_DISPLAY.get(role, role),
        "mode": "job" if target_job else "role",
        "score": score,
        "roadmap_score": score,
        "skills": with_learning_resources(skills),
        "target_job": target_job,
        "job_match": job_match,
    }


@app.post("/api/user/skills/toggle")
def toggle_skill(
    skill_name: str = Form(...),
    acquired: bool = Form(...),
    job_id: Optional[str] = Form(default=None, max_length=120),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT desired_role FROM user_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        if not profile or not profile["desired_role"]:
            raise HTTPException(400, "Profile not found.")
        progress_role = profile["desired_role"]
        if job_id:
            cur.execute("SELECT skills_desc, description FROM jobs WHERE job_id = %s", (job_id,))
            job = cur.fetchone()
            if not job:
                raise HTTPException(404, "Job not found.")
            if skill_name not in extract_job_skills(job["skills_desc"], job["description"])["required_skills"]:
                raise HTTPException(404, "Skill is not part of this job's roadmap.")
            progress_role = f"job:{job_id}"
        else:
            cur.execute(
                "SELECT 1 FROM role_skills WHERE role = %s AND skill_name = %s",
                (progress_role, skill_name),
            )
            if not cur.fetchone():
                raise HTTPException(404, "Skill is not part of your roadmap.")
        cur.execute(
            """
            INSERT INTO user_skills (user_id, role, skill_name, acquired, manual_override)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (user_id, role, skill_name) DO UPDATE
              SET acquired = EXCLUDED.acquired, manual_override = TRUE, updated_at = NOW()
            """,
            (user_id, progress_role, skill_name, acquired),
        )
        conn.commit()
        return {"ok": True}
    finally:
        cur.close()
        conn.close()


# ── User jobs (uses stored resume) ────────────────────────────────────────────

@app.get("/api/user/jobs")
def get_user_jobs(
    query: Optional[str] = Query(default=None, max_length=120),
    remote: Optional[bool] = Query(default=None),
    work_type: Optional[str] = Query(default=None, max_length=80),
    experience_level: Optional[str] = Query(default=None, max_length=80),
    industry: Optional[str] = Query(default=None, max_length=120),
    min_salary: Optional[float] = Query(default=None, ge=0),
    max_salary: Optional[float] = Query(default=None, ge=0),
    sort: str = Query(default="score", pattern="^(score|title)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_JOB_LIMIT, ge=1, le=MAX_JOB_LIMIT),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        profile = _load_matching_profile(cur, user_id)
        career_text = profile['career_text']

        embedder = get_embedder()
        cv_embedding = embedder.encode(career_text, normalize_embeddings=True).tolist()
        rows, _ = _query_job_matches(
            cur,
            cv_embedding,
            query=query,
            remote=remote,
            work_type=work_type,
            experience_level=experience_level,
            industry=industry,
            min_salary=min_salary,
            max_salary=max_salary,
        )
        total = len(rows)
        ranked = rank_job_matches(rows, career_text, sort=sort, page=page, limit=limit)
        result, _ = _format_job_rows(ranked, career_text)
        return {
            "jobs": result,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": page * limit < total,
            "score_method": "75% semantic similarity + 25% explicit skill coverage",
        }
    finally:
        if cur:
            cur.close()
        conn.close()


@app.get('/api/user/jobs/{job_id}/explanation')
def get_job_explanation(job_id: str, user_id: int = Depends(get_current_user_id)):
    if not job_id or len(job_id) > 120:
        raise HTTPException(400, 'Invalid job ID.')
    conn = get_db()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        profile = _load_matching_profile(cur, user_id)
        cur.execute('SELECT job_id, title, description, skills_desc, embedding IS NOT NULL AS has_embedding FROM jobs WHERE job_id = %s', (job_id,))
        job = cur.fetchone()
        if not job:
            raise HTTPException(404, 'Job not found.')
        if not job['has_embedding']:
            raise HTTPException(422, 'This job does not have a semantic embedding yet.')
        embedder = get_embedder()
        embedding = embedder.encode(profile['career_text'], normalize_embeddings=True).tolist()
        cur.execute('SELECT 1 - (embedding <=> %s::vector) AS raw_score FROM jobs WHERE job_id = %s', (embedding, job_id))
        raw_score = cur.fetchone()['raw_score']
    finally:
        if cur:
            cur.close()
        conn.close()
    result = explain_job_match(job, profile['resume_text'], profile['career_text'], raw_score, embedder)
    result['embedding_model'] = EMBEDDING_MODEL
    return result


# ── Production frontend ──────────────────────────────────────────────────────

def mount_frontend() -> None:
    """Serve the compiled React SPA when FRONTEND_DIST_DIR is configured."""

    configured = os.getenv("FRONTEND_DIST_DIR")
    if not configured:
        return

    frontend_dir = Path(configured).resolve()
    index_file = frontend_dir / "index.html"
    if not index_file.is_file():
        raise RuntimeError(f"Frontend build not found at {frontend_dir}")

    assets_dir = frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "API route not found.")

        requested = (frontend_dir / full_path).resolve()
        try:
            requested.relative_to(frontend_dir)
        except ValueError:
            raise HTTPException(404, "File not found.")

        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(index_file)


mount_frontend()
