"""
ingest_jobs.py — Load LinkedIn job postings into Supabase PGVector.

Usage:
    python ingest_jobs.py

Reads postings.csv from the data directory, embeds each job with
Sentence-BERT, and upserts into the jobs table in batches.
Runtime: ~10-20 min for 123K jobs on CPU.
"""
import os
import math
from pathlib import Path
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_data_dir = Path(os.getenv("RESUMIND_DATA_DIR", PROJECT_ROOT.parent / "data"))
DATA_DIR   = (_data_dir if _data_dir.is_absolute() else PROJECT_ROOT / _data_dir).resolve()
CSV_PATH   = str(DATA_DIR / "postings.csv")
DB_URL     = os.getenv("DATABASE_URL")
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 256
# Limit to tech-relevant rows — set to None to load all 123K
LIMIT      = None

TECH_KEYWORDS = [
    "engineer", "developer", "software", "data", "machine learning",
    "devops", "backend", "frontend", "full stack", "cloud", "python",
    "java", "javascript", "typescript", "react", "node", "infrastructure",
    "security", "qa", "analyst", "architect", "product", "mobile", "ios",
    "android", "ai", "ml", "nlp", "cyber", "network", "database", "sql",
]


def load_csv(path: str) -> pd.DataFrame:
    print(f"Loading {path}...")
    df = pd.read_csv(path, low_memory=False)
    if LIMIT:
        df = df.head(LIMIT)

    # Keep only rows where title contains a tech keyword
    mask = df["title"].fillna("").str.lower().apply(
        lambda t: any(kw in t for kw in TECH_KEYWORDS)
    )
    df = df[mask].reset_index(drop=True)
    print(f"  {len(df):,} tech-relevant jobs after filtering")
    return df


def build_text(row) -> str:
    parts = []
    if pd.notna(row.get("title")):
        parts.append(f"job title: {row['title']}")
    if pd.notna(row.get("description")):
        parts.append(f"description: {str(row['description'])[:1000]}")
    if pd.notna(row.get("skills_desc")):
        parts.append(f"skills: {row['skills_desc']}")
    return " ".join(parts)


def load_auxiliary_data(data_dir: Path) -> dict[str, dict]:
    """Load optional salary, benefits, industry, and company metadata."""

    result = {
        "benefits": {}, "industries": {}, "company_size": {}, "employee_count": {},
    }

    benefits_path = data_dir / "jobs" / "benefits.csv"
    if benefits_path.exists():
        benefits = pd.read_csv(benefits_path, low_memory=False)
        if {"job_id", "type"}.issubset(benefits.columns):
            grouped = benefits.dropna(subset=["type"]).groupby("job_id")["type"]
            result["benefits"] = grouped.apply(
                lambda values: "; ".join(dict.fromkeys(str(v).strip() for v in values))
            ).to_dict()

    industries_path = data_dir / "jobs" / "job_industries.csv"
    mapping_path = data_dir / "mappings" / "industries.csv"
    if industries_path.exists() and mapping_path.exists():
        links = pd.read_csv(industries_path, low_memory=False)
        mapping = pd.read_csv(mapping_path, low_memory=False)
        if {"job_id", "industry_id"}.issubset(links.columns) and {"industry_id", "industry_name"}.issubset(mapping.columns):
            merged = links.merge(mapping, on="industry_id", how="left").dropna(subset=["industry_name"])
            grouped = merged.groupby("job_id")["industry_name"]
            result["industries"] = grouped.apply(
                lambda values: "; ".join(dict.fromkeys(str(v).strip() for v in values))
            ).to_dict()

    companies_path = data_dir / "companies" / "companies.csv"
    if companies_path.exists():
        companies = pd.read_csv(companies_path, low_memory=False)
        if {"company_id", "company_size"}.issubset(companies.columns):
            result["company_size"] = dict(zip(
                companies["company_id"],
                pd.to_numeric(companies["company_size"], errors="coerce"),
            ))

    counts_path = data_dir / "companies" / "employee_counts.csv"
    if counts_path.exists():
        counts = pd.read_csv(counts_path, low_memory=False)
        if {"company_id", "employee_count"}.issubset(counts.columns):
            result["employee_count"] = dict(zip(
                counts["company_id"],
                pd.to_numeric(counts["employee_count"], errors="coerce"),
            ))

    return result


def _number(value):
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_or_none(*values, limit=None):
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text[:limit] if limit else text
    return None


def _integer(value):
    number = _number(value)
    return int(number) if number is not None else None


def _to_bool(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def ingest():
    df = load_csv(CSV_PATH)
    auxiliary = load_auxiliary_data(DATA_DIR)
    model = SentenceTransformer(MODEL_NAME)
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    total = len(df)
    batches = math.ceil(total / BATCH_SIZE)
    inserted = 0

    print(f"Embedding and inserting {total:,} jobs in {batches} batches...")

    for i in range(batches):
        batch = df.iloc[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        texts = [build_text(row) for _, row in batch.iterrows()]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

        records = []
        for (_, row), emb in zip(batch.iterrows(), embeddings):
            records.append((
                str(row.get("job_id", "")),
                str(row.get("title", ""))[:255],
                str(row.get("company_name", ""))[:255] if pd.notna(row.get("company_name")) else None,
                str(row.get("location", ""))[:255] if pd.notna(row.get("location")) else None,
                str(row.get("description", ""))[:4000] if pd.notna(row.get("description")) else None,
                str(row.get("skills_desc", ""))[:1000] if pd.notna(row.get("skills_desc")) else None,
                str(row.get("formatted_experience_level", ""))[:100] if pd.notna(row.get("formatted_experience_level")) else None,
                str(row.get("formatted_work_type", ""))[:100] if pd.notna(row.get("formatted_work_type")) else None,
                _to_bool(row.get("remote_allowed")),
                _text_or_none(row.get("application_url"), row.get("job_posting_url"), limit=500),
                _number(row.get("max_salary")),
                _number(row.get("med_salary")),
                _number(row.get("min_salary")),
                _text_or_none(row.get("pay_period"), limit=30),
                _text_or_none(row.get("currency"), limit=10),
                _text_or_none(row.get("compensation_type"), limit=40),
                _integer(row.get("listed_time")),
                _integer(row.get("expiry")),
                _integer(row.get("closed_time")),
                auxiliary["industries"].get(row.get("job_id")),
                _integer(auxiliary["company_size"].get(row.get("company_id"))),
                _integer(auxiliary["employee_count"].get(row.get("company_id"))),
                auxiliary["benefits"].get(row.get("job_id")),
                emb.tolist(),
            ))

        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO jobs
                (job_id, title, company, location, description, skills_desc,
                 experience_level, work_type, remote, apply_url,
                 max_salary, med_salary, min_salary, pay_period, currency,
                  compensation_type, listed_time, expiry, closed_time, industry,
                  company_size, employee_count, benefits, embedding)
            VALUES %s
            ON CONFLICT (job_id) DO UPDATE SET
              title = EXCLUDED.title,
              company = EXCLUDED.company,
              location = EXCLUDED.location,
              description = EXCLUDED.description,
              skills_desc = EXCLUDED.skills_desc,
              experience_level = EXCLUDED.experience_level,
              work_type = EXCLUDED.work_type,
              remote = EXCLUDED.remote,
              apply_url = EXCLUDED.apply_url,
              max_salary = EXCLUDED.max_salary,
              med_salary = EXCLUDED.med_salary,
              min_salary = EXCLUDED.min_salary,
              pay_period = EXCLUDED.pay_period,
              currency = EXCLUDED.currency,
              compensation_type = EXCLUDED.compensation_type,
              listed_time = EXCLUDED.listed_time,
              expiry = EXCLUDED.expiry,
              closed_time = EXCLUDED.closed_time,
              industry = EXCLUDED.industry,
              company_size = EXCLUDED.company_size,
              employee_count = EXCLUDED.employee_count,
              benefits = EXCLUDED.benefits,
              embedding = EXCLUDED.embedding
            """,
            records,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)",
        )
        conn.commit()
        inserted += len(records)
        pct = (i + 1) / batches * 100
        print(f"  [{pct:5.1f}%] batch {i+1}/{batches} — {inserted:,} jobs loaded")

    cur.close()
    conn.close()
    print(f"\nDone. {inserted:,} jobs in the database.")


if __name__ == "__main__":
    ingest()
