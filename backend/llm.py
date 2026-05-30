"""
llm.py – resume improvement suggestions via local Ollama (Qwen 3.5 80b)
or OpenAI-compatible API.

Set in .env:
    OLLAMA_BASE_URL=http://localhost:11434/v1   # local Qwen via Ollama
    OLLAMA_MODEL=qwen2.5:72b
    # OR for OpenAI:
    OPENAI_API_KEY=sk-...
"""
import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
from scraper import scrape_file, get_file_extension

load_dotenv()

# ── client setup ─────────────────────────────────────────────────────────────
# Defaults to local Ollama; falls back to OpenAI if OPENAI_API_KEY is set.
_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
_api_key  = os.getenv("OLLAMA_API_KEY", "ollama")  # Ollama ignores the key
_model    = os.getenv("OLLAMA_MODEL", "qwen2.5:72b")

client = OpenAI(base_url=_base_url, api_key=_api_key)


def suggest_resume_improvements(resume_text: str, job_title: str) -> str:
    """
    Ask the LLM for actionable improvements to the CV for a given job title.
    Returns the model's text response.
    """
    response = client.chat.completions.create(
        model=_model,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are an expert career coach specialising in the tech industry. "
                    f"Analyse the following resume and give concise, actionable suggestions "
                    f"to improve it for a '{job_title}' position. "
                    f"Focus on skill gaps, wording, and missing keywords. "
                    f"Do NOT invent experience the candidate does not have."
                ),
            },
            {"role": "user", "content": resume_text},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python llm.py <file_path> <job_title>")
        sys.exit(1)

    file_path = sys.argv[1]
    job_title = sys.argv[2]
    extension = get_file_extension(file_path)
    resume_text = scrape_file(file_path, extension)

    print("=== Resume Improvement Suggestions ===\n")
    print(suggest_resume_improvements(resume_text, job_title))
