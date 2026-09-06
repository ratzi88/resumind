"""
recommendation.py – semantic job recommendation using Sentence-BERT + cosine similarity.

Usage:
    python recommendation.py path/to/resume.pdf [top_n]

Requires:
    pip install sentence-transformers scikit-learn pdfplumber pandas

The job dataset (Kaggle fake_job_postings or similar) must be available via
Supabase/PostgreSQL with PGVector in production. This module provides a local
CSV-based version for development / testing.
"""
import sys
import pandas as pd
import numpy as np

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ── config ────────────────────────────────────────────────────────────────────
MODEL_NAME      = "all-MiniLM-L6-v2"   # 384-dim, fast, good semantic quality
MATCH_THRESHOLD = 0.60                  # practical semantic-similarity floor
DEFAULT_TOP_N   = 10

# Columns to drop (non-semantic metadata)
DROP_COLS = ["telecommuting", "has_company_logo", "has_questions", "fraudulent"]

# ── model (loaded once at module level) ───────────────────────────────────────
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


# ── data loading ─────────────────────────────────────────────────────────────

def load_jobs(csv_path: str, limit: int = 500) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Load job postings from a local CSV and embed them.
    Returns (dataframe, embeddings_matrix).
    """
    df = pd.read_csv(csv_path)
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors="ignore")
    df = df.head(limit)

    texts = (
        "job title: "       + df["title"].fillna("") +
        " description: "    + df["description"].fillna("") +
        " requirements: "   + df["requirements"].fillna("")
    )

    model = _get_model()
    embeddings = model.encode(texts.tolist(), normalize_embeddings=True)
    return df, embeddings


# ── PDF parsing ───────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    if pdfplumber is None:
        raise ImportError("Install pdfplumber: pip install pdfplumber")
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ── recommendation ────────────────────────────────────────────────────────────

def recommend_jobs_by_pdf(
    pdf_path: str,
    job_df: pd.DataFrame,
    job_embeddings: np.ndarray,
    top_n: int = DEFAULT_TOP_N,
    threshold: float = MATCH_THRESHOLD,
) -> pd.DataFrame:
    """
    Given a CV PDF and pre-computed job embeddings, return the top-N jobs
    above `threshold` similarity, sorted descending.
    """
    cv_text = extract_text_from_pdf(pdf_path)
    if not cv_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    cv_text = cv_text.replace("\n", " ").lower()

    model = _get_model()
    cv_embedding = model.encode(cv_text, normalize_embeddings=True)

    scores = cosine_similarity([cv_embedding], job_embeddings)[0]

    # Apply threshold and select top-n
    top_idx = np.argsort(scores)[::-1]
    top_idx = [i for i in top_idx if scores[i] >= threshold][:top_n]

    results = job_df.iloc[top_idx].copy()
    results["semantic_score"] = scores[top_idx]
    # This local CSV mode exposes raw semantic similarity. The API mode adds
    # explicit skill coverage and labels its result as an estimated fit score.
    results["match_pct"] = (results["semantic_score"] * 100).round(1)

    return results.reset_index(drop=True)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python recommendation.py <resume.pdf> <jobs.csv> [top_n]")
        sys.exit(1)

    pdf_path  = sys.argv[1]
    csv_path  = sys.argv[2]
    top_n     = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_TOP_N

    print(f"Loading jobs from {csv_path}...")
    job_df, job_embeddings = load_jobs(csv_path)

    print(f"Analysing {pdf_path}...")
    results = recommend_jobs_by_pdf(pdf_path, job_df, job_embeddings, top_n=top_n)

    if results.empty:
        print(f"No jobs found above the {MATCH_THRESHOLD:.0%} threshold.")
    else:
        cols = [c for c in ["job_id", "title", "company_profile", "match_pct"] if c in results.columns]
        print(f"\nTop {len(results)} matches:\n")
        print(results[cols].to_string(index=False))
