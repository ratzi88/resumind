import os
import re
import json
import tempfile
import psycopg2
import psycopg2.extras
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from scraper import scrape_file, get_file_extension
from auth import hash_password, verify_password, create_token, get_current_user_id

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── clients ───────────────────────────────────────────────────────────────────
llm = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
)
_model = os.getenv("OLLAMA_MODEL", "qwen2.5:72b")
_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


# ── helpers ───────────────────────────────────────────────────────────────────

def extract_text(file: UploadFile) -> str:
    ext = get_file_extension(file.filename)
    if ext not in (".pdf", ".docx"):
        raise HTTPException(400, "Only PDF and DOCX files are supported.")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file.file.read())
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


@app.post("/api/user/suggest")
async def user_suggest(
    job_title: str = Form(...),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT resume_text FROM user_profiles WHERE user_id = %s", (user_id,))
    profile = cur.fetchone()
    cur.close()
    conn.close()
    if not profile or not profile["resume_text"]:
        raise HTTPException(400, "No resume found. Complete onboarding first.")
    response = llm.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": SUGGEST_PROMPT},
            {"role": "user",   "content": f"Target role: {job_title}\n\n{profile['resume_text']}"},
        ],
    )
    return _parse_suggest(response.choices[0].message.content)


@app.post("/api/suggest")
async def suggest(file: UploadFile = File(...), job_title: str = Form(...)):
    file.file.seek(0)
    resume_text = extract_text(file)
    response = llm.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": SUGGEST_PROMPT},
            {"role": "user",   "content": f"Target role: {job_title}\n\n{resume_text}"},
        ],
    )
    return _parse_suggest(response.choices[0].message.content)


# ── Flow 2 — job matching ─────────────────────────────────────────────────────

@app.post("/api/jobs")
async def jobs(file: UploadFile = File(...)):
    file.file.seek(0)
    resume_text = extract_text(file)

    embedder = get_embedder()
    cv_embedding = embedder.encode(resume_text, normalize_embeddings=True).tolist()

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
            job_id, title, company, location,
            skills_desc, experience_level, work_type, remote, apply_url,
            1 - (embedding <=> %s::vector) AS raw_score
        FROM jobs
        WHERE 1 - (embedding <=> %s::vector) >= 0.60
        ORDER BY embedding <=> %s::vector
        LIMIT 10
        """,
        (cv_embedding, cv_embedding, cv_embedding),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {"jobs": []}

    # Normalize: map [min_score, max_score] → [70, 97] for a readable display range
    scores = [r["raw_score"] for r in rows]
    min_s, max_s = min(scores), max(scores)
    def normalize(s):
        if max_s == min_s:
            return 85
        return round(70 + (s - min_s) / (max_s - min_s) * 27, 1)

    result = []
    for r in rows:
        d = dict(r)
        d["match_pct"] = normalize(d.pop("raw_score"))
        result.append(d)
    return {"jobs": result}


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
async def roadmap(file: UploadFile = File(...), job_id: str = Form(...)):
    file.file.seek(0)
    resume_text = extract_text(file)

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

    response = llm.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": ROADMAP_PROMPT},
            {"role": "user",   "content": f"RESUME:\n{resume_text[:3000]}\n\nJOB:\n{job_context}"},
        ],
    )

    raw = response.choices[0].message.content.strip()
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
async def register(email: str = Form(...), password: str = Form(...)):
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
async def login(email: str = Form(...), password: str = Form(...)):
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


# ── Onboarding ────────────────────────────────────────────────────────────────

SKILL_DETECT_PROMPT = """\
You are given a resume and a list of skills for a specific tech role.
Return ONLY a JSON array of skill names from the list that the candidate clearly has based on their resume.
Do NOT include skills not in the provided list.
Do NOT invent skills. Output valid JSON array only, e.g.: ["Python", "Docker", "Git"]
"""


@app.post("/api/onboarding")
async def onboarding(
    file: UploadFile = File(...),
    role: str = Form(...),
    user_id: int = Depends(get_current_user_id),
):
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

    # LLM detects acquired skills — gracefully falls back if LLM is unavailable
    acquired = []
    try:
        skills_list = "\n".join(f"- {s}" for s in skill_names[:150])
        response = llm.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": SKILL_DETECT_PROMPT},
                {"role": "user", "content": f"RESUME:\n{resume_text[:3000]}\n\nSKILLS LIST:\n{skills_list}"},
            ],
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            acquired = parsed
    except Exception:
        pass  # LLM unavailable — all skills start as not acquired; user toggles manually

    acquired_set = set(acquired)

    # Upsert user_skills
    records = [(user_id, role, s, s in acquired_set) for s in skill_names]
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO user_skills (user_id, role, skill_name, acquired)
        VALUES %s
        ON CONFLICT (user_id, role, skill_name) DO UPDATE
          SET acquired = EXCLUDED.acquired, updated_at = NOW()
        """,
        records,
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Onboarding complete", "skills_detected": len(acquired_set)}


# ── User roadmap (from DB, no LLM) ───────────────────────────────────────────

@app.get("/api/user/roadmap")
def get_user_roadmap(user_id: int = Depends(get_current_user_id)):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        "SELECT desired_role FROM user_profiles WHERE user_id = %s", (user_id,)
    )
    profile = cur.fetchone()
    if not profile or not profile["desired_role"]:
        raise HTTPException(400, "No role set. Complete onboarding first.")

    role = profile["desired_role"]
    cur.execute(
        """
        SELECT rs.skill_name, rs.category, rs.stage, rs.impact,
               COALESCE(us.acquired, FALSE) as acquired
        FROM role_skills rs
        LEFT JOIN user_skills us
          ON us.skill_name = rs.skill_name AND us.user_id = %s AND us.role = rs.role
        WHERE rs.role = %s
        ORDER BY rs.stage, rs.impact DESC
        """,
        (user_id, role),
    )
    skills = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    total  = sum(s["impact"] for s in skills)
    earned = sum(s["impact"] for s in skills if s["acquired"])
    score  = round(earned / total * 100) if total else 0

    return {
        "role": role,
        "role_label": ROLE_DISPLAY.get(role, role),
        "score": score,
        "skills": skills,
    }


@app.post("/api/user/skills/toggle")
def toggle_skill(
    skill_name: str = Form(...),
    acquired: bool = Form(...),
    user_id: int = Depends(get_current_user_id),
):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT desired_role FROM user_profiles WHERE user_id = %s", (user_id,))
    profile = cur.fetchone()
    if not profile:
        raise HTTPException(400, "Profile not found.")
    cur.execute(
        """
        INSERT INTO user_skills (user_id, role, skill_name, acquired)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, role, skill_name) DO UPDATE
          SET acquired = EXCLUDED.acquired, updated_at = NOW()
        """,
        (user_id, profile["desired_role"], skill_name, acquired),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


# ── User jobs (uses stored resume) ────────────────────────────────────────────

@app.get("/api/user/jobs")
def get_user_jobs(user_id: int = Depends(get_current_user_id)):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT resume_text FROM user_profiles WHERE user_id = %s", (user_id,))
    profile = cur.fetchone()
    if not profile or not profile["resume_text"]:
        raise HTTPException(400, "No resume found. Complete onboarding first.")

    embedder     = get_embedder()
    cv_embedding = embedder.encode(profile["resume_text"], normalize_embeddings=True).tolist()

    cur.execute(
        """
        SELECT job_id, title, company, location,
               skills_desc, experience_level, work_type, remote, apply_url,
               1 - (embedding <=> %s::vector) AS raw_score
        FROM jobs
        WHERE 1 - (embedding <=> %s::vector) >= 0.60
        ORDER BY embedding <=> %s::vector
        LIMIT 10
        """,
        (cv_embedding, cv_embedding, cv_embedding),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {"jobs": []}

    scores = [r["raw_score"] for r in rows]
    min_s, max_s = min(scores), max(scores)
    def normalize(s):
        if max_s == min_s:
            return 85
        return round(70 + (s - min_s) / (max_s - min_s) * 27, 1)

    result = []
    for r in rows:
        d = dict(r)
        d["match_pct"] = normalize(d.pop("raw_score"))
        result.append(d)
    return {"jobs": result}
