"""
ingest_roadmaps.py — Fetch skill trees from roadmap.sh GitHub and load into Supabase.

Pulls each role's JSON from the kamranahmedse/developer-roadmap repo,
extracts topic/subtopic nodes grouped by their parent section,
assigns impact weights, and upserts into role_skills.
"""
import os
import json
import math
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

ROADMAP_DIR = "/tmp/roadmapsh/src/data/roadmaps"

ROLES = [
    "backend", "frontend", "full-stack", "devops", "devsecops",
    "data-engineer", "machine-learning", "cyber-security", "ai-engineer",
    "data-analyst", "qa", "software-architect", "mlops",
    "network-engineer", "android", "ios",
]

# Map role slug → display name
ROLE_DISPLAY = {
    "backend":           "Backend Engineer",
    "frontend":          "Frontend Engineer",
    "full-stack":        "Full-Stack Engineer",
    "devops":            "DevOps Engineer",
    "devsecops":         "DevSecOps Engineer",
    "data-engineer":     "Data Engineer",
    "machine-learning":  "Machine Learning Engineer",
    "cyber-security":    "Cybersecurity Engineer",
    "ai-engineer":       "AI Engineer",
    "data-analyst":      "Data Analyst",
    "qa":                "QA Engineer",
    "software-architect":"Software Architect",
    "mlops":             "MLOps Engineer",
    "network-engineer":  "Network Engineer",
    "android":           "Android Developer",
    "ios":               "iOS Developer",
}


def fetch_nodes(role: str):
    path = os.path.join(ROADMAP_DIR, role, f"{role}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return data.get("nodes", [])
    return None   # signal to use content-based fallback


def skills_from_content(role: str) -> list[dict]:
    """Fallback for roadmaps that use markdown content files instead of JSON."""
    content_dir = os.path.join(ROADMAP_DIR, role, "content")
    if not os.path.isdir(content_dir):
        return []
    skills = []
    for fname in sorted(os.listdir(content_dir)):
        if not fname.endswith(".md"):
            continue
        slug = fname.split("@")[0]
        name = slug.replace("-", " ").replace("_", " ").title()
        if name and name != "Index":
            skills.append({"skill_name": name, "category": "General", "impact": 5})
    return skills


def extract_skills(nodes: list) -> list[dict]:
    """
    Build skill list from nodes.
    - section nodes  → category name
    - topic nodes    → skill (impact 8)
    - subtopic nodes → skill (impact 4)
    Returns list of {skill_name, category, impact}
    """
    # Build id → node map
    by_id = {n["id"]: n for n in nodes}

    # Find parent section for each node by proximity (sections are visual containers)
    # We use y-position: each topic belongs to the nearest section above it
    sections = [n for n in nodes if n.get("type") == "section"]
    sections_sorted = sorted(sections, key=lambda n: n.get("position", {}).get("y", 0))

    def nearest_section(node) -> str:
        ny = node.get("position", {}).get("y", 0)
        best = "General"
        for s in sections_sorted:
            sy = s.get("position", {}).get("y", 0)
            if sy <= ny:
                label = s.get("data", {}).get("label", "General")
                if label:
                    best = label
        return best

    skills = []
    seen = set()
    for node in nodes:
        ntype = node.get("type")
        if ntype not in ("topic", "subtopic"):
            continue
        label = node.get("data", {}).get("label", "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        category = nearest_section(node)
        impact   = 8 if ntype == "topic" else 4
        skills.append({"skill_name": label, "category": category, "impact": impact})

    return skills


def normalise_impacts(skills: list[dict]) -> list[dict]:
    """Scale impacts so they sum to 100."""
    total = sum(s["impact"] for s in skills)
    if total == 0:
        return skills
    for s in skills:
        s["impact"] = max(1, round(s["impact"] / total * 100))
    return skills


def ingest():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur  = conn.cursor()

    total_skills = 0
    for role in ROLES:
        print(f"Processing {role}...", end=" ", flush=True)
        nodes = fetch_nodes(role)
        if nodes is None:
            skills = skills_from_content(role)
            if not skills:
                print("  SKIP: no data found")
                continue
        else:
            skills = extract_skills(nodes)
        skills = normalise_impacts(skills)

        # Deduplicate within batch before inserting
        seen = set()
        records = []
        for s in skills:
            key = (role, s["skill_name"])
            if key not in seen:
                seen.add(key)
                records.append((role, s["skill_name"], s["category"], s["impact"]))
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO role_skills (role, skill_name, category, impact)
            VALUES %s
            ON CONFLICT (role, skill_name) DO UPDATE
              SET category = EXCLUDED.category,
                  impact   = EXCLUDED.impact
            """,
            records,
        )
        conn.commit()
        total_skills += len(records)
        print(f"{len(records)} skills loaded")

    cur.close()
    conn.close()
    print(f"\nDone. {total_skills} skills across {len(ROLES)} roles.")


if __name__ == "__main__":
    ingest()
