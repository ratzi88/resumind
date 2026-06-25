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
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

CSV_PATH   = os.path.expanduser("~/Learning/final_project/data/postings.csv")
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


def ingest():
    df = load_csv(CSV_PATH)
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
                bool(row.get("remote_allowed")) if pd.notna(row.get("remote_allowed")) else None,
                str(row.get("job_posting_url", ""))[:500] if pd.notna(row.get("job_posting_url")) else None,
                emb.tolist(),
            ))

        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO jobs
                (job_id, title, company, location, description, skills_desc,
                 experience_level, work_type, remote, apply_url, embedding)
            VALUES %s
            ON CONFLICT (job_id) DO NOTHING
            """,
            records,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)",
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
