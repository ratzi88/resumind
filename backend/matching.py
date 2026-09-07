"""Small, deterministic helpers shared by job matching and roadmap views.

The embedding model is useful for broad semantic similarity, but users also
need a readable explanation. These helpers deliberately stay conservative:
they only mark a skill as present when its name (or a known alias) appears in
the resume text.
"""

from __future__ import annotations

import re
from functools import lru_cache
from html import unescape
from typing import Iterable


SKILL_ALIASES = {
    "js": "javascript",
    "javascript es6": "javascript",
    "javascript es6+": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "postgres sql": "postgresql",
    "k8s": "kubernetes",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "continuous integration": "ci/cd",
    "continuous delivery": "ci/cd",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest apis": "rest api",
    "rest web services": "rest api",
    "restful web services": "rest api",
    "apis": "api",
    "python3": "python",
    "nodejs": "node.js",
    "node js": "node.js",
    "react.js": "react",
    "reactjs": "react",
    "vuejs": "vue.js",
    "vue js": "vue.js",
    "angularjs": "angular",
    "html5": "html",
    "css3": "css",
    "dotnet": ".net",
    "dot net": ".net",
    "c sharp": "c#",
    "csharp": "c#",
    "golang": "go programming",
    "go language": "go programming",
    "springboot": "spring boot",
    "springs": "spring",
    "jdk": "java",
    "j2ee": "java",
    "java ee": "java",
    "plsql": "pl/sql",
    "ms sql server": "sql server",
    "mssql": "sql server",
    "microsoft sql server": "sql server",
    "mongo db": "mongodb",
    "apache kafka": "kafka",
    "apache spark": "spark",
    "apache airflow": "airflow",
    "active mq": "activemq",
    "amazon aws": "aws",
    "microsoft azure": "azure",
    "google cloud": "gcp",
    "ci / cd": "ci/cd",
    "ci-cd": "ci/cd",
    "cicd": "ci/cd",
    "continuous integration/continuous delivery": "ci/cd",
    "argo cd": "argocd",
    "bash & terminal": "bash",
    "linux cli": "linux",
    "networking basics": "networking",
    "testing junit": "junit",
    "caching redis": "redis",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "powerbi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "object oriented programming": "object-oriented programming",
    "object oriented": "object-oriented programming",
    "oop": "object-oriented programming",
    "unit tests": "unit testing",
    "automated testing": "test automation",
    "automation testing": "test automation",
    "natural language processing": "nlp",
    "large language models": "llm",
    "llms": "llm",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
}

# Only technologies/skills actually mentioned in the posting are extracted.
# Avoid ambiguous standalone words such as "Go", "R", "C", or "REST" in
# prose. Unknown, explicit skill labels can still pass through skills_desc.
JOB_SKILL_NAMES = (
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go programming",
    "Ruby", "PHP", "Kotlin", "Swift", "Objective-C", "Scala", "Rust", "Dart",
    "Bash", "PowerShell", "Perl", "MATLAB", "HTML", "CSS", "React", "React Native",
    "Angular", "Vue.js", "Next.js", "Node.js", "Express.js", "Django", "Flask",
    "FastAPI", "Spring", "Spring Boot", "Hibernate", "JPA", "jQuery", "AJAX",
    "Bootstrap", "Tailwind CSS", ".NET", "ASP.NET", "Flutter", "SwiftUI",
    "Jetpack Compose", "Android", "iOS", "SQL", "PL/SQL", "SQL Server",
    "PostgreSQL", "MySQL", "Oracle", "SQLite", "MongoDB", "Redis", "NoSQL",
    "Cassandra", "DynamoDB", "Elasticsearch", "Snowflake", "BigQuery",
    "Kafka", "Spark", "Airflow", "Hadoop", "dbt", "ETL", "Data Modeling",
    "Data Analysis", "Data Pipelines", "Data Quality", "Stored Procedures",
    "AWS", "Azure", "GCP", "Linux", "Windows Server", "Docker", "Kubernetes",
    "Terraform", "Ansible", "Jenkins", "GitHub Actions", "GitLab", "CircleCI",
    "Travis CI", "CI/CD", "Git", "GitHub", "ArgoCD", "Helm", "Prometheus",
    "Grafana", "Splunk", "ELK Stack", "Nginx", "Apache HTTP Server", "HAProxy",
    "HashiCorp Vault", "RabbitMQ", "ActiveMQ", "JMS", "JBoss", "Liquibase",
    "CMake", "vcpkg", "Maven", "Gradle", "npm", "REST APIs", "GraphQL",
    "SOAP", "gRPC", "XML", "JSON", "OAuth", "JWT", "TCP/IP", "DNS",
    "HTTP", "Networking", "Network Security", "Cybersecurity", "Cryptography",
    "Wireshark", "Burp Suite", "OWASP", "Penetration Testing", "Incident Response",
    "Selenium", "Cypress", "Playwright", "Postman", "pytest", "JUnit", "Jest",
    "Vitest", "TestNG", "JMeter", "k6", "Manual Testing", "Unit Testing",
    "Integration Testing", "Regression Testing", "Test Automation", "API Testing",
    "Performance Testing", "Security Testing", "Machine Learning", "Deep Learning",
    "PyTorch", "TensorFlow", "Scikit-learn", "Pandas", "NumPy", "Matplotlib",
    "NLP", "LLM", "RAG", "LangChain", "Hugging Face", "MLflow", "Statistics",
    "Tableau", "Power BI", "Excel", "Agile", "Scrum", "SDLC", "Jira",
    "Confluence", "Microservices", "Distributed Systems", "System Design",
    "Design Patterns", "Object-Oriented Programming", "UML", "SOLID",
    "Salesforce", "NetSuite", "Zendesk", "Okta", "SAP", "ServiceNow",
)


def _posting_text(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def normalize_skill_name(value: str) -> str:
    """Return a comparison-friendly representation of a skill name."""

    normalized = re.sub(r"[^a-z0-9+#/.& -]+", " ", str(value).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return SKILL_ALIASES.get(normalized, normalized)


def redact_pii(text: str) -> str:
    """Remove common contact identifiers before text reaches AI/embeddings."""

    value = str(text or "")
    value = re.sub(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", "[email]", value)
    value = re.sub(
        r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)",
        "[phone]",
        value,
    )
    return value


def parse_required_skills(value: str | None) -> list[str]:
    """Split the dataset's comma/bullet/semicolon separated skills field."""

    if not value:
        return []

    pieces = re.split(r"[,;|\n•·]+", str(value))
    result: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        skill = re.sub(r"^\s*[-*]\s*", "", piece).strip()
        skill = re.sub(r"\s+", " ", skill)
        key = normalize_skill_name(skill)
        # Ignore fragments that are clearly prose rather than skills. Short
        # labels such as "SQL" and "Git" still pass this filter.
        if not skill or len(skill) > 80 or len(key.split()) > 10 or key in seen:
            continue
        seen.add(key)
        result.append(skill)
    return result


@lru_cache(maxsize=512)
def _skill_pattern(skill: str) -> re.Pattern[str]:
    key = normalize_skill_name(skill)
    alternatives = [re.escape(key)]
    for alias, canonical in SKILL_ALIASES.items():
        if canonical == key:
            alternatives.append(re.escape(alias))
    # Accept line breaks / extra spaces in extracted PDF text. Including +/#
    # in the boundaries keeps short names from matching other technologies.
    # A dot before an alias must not make "Node.js" a separate "JS" match.
    alternatives = [value.replace(r"\ ", r"\s+") for value in alternatives]
    expression = r"(?<![a-z0-9+#.])(?:" + "|".join(sorted(alternatives, key=len, reverse=True)) + r")(?![a-z0-9+#])"
    return re.compile(expression, re.IGNORECASE)


def extract_job_skills(skills_desc: str | None = None, description: str | None = None) -> dict:
    required, sources = _extract_job_skills_cached(skills_desc, description)
    # Cached values are immutable: callers receive their own lists.
    return {"required_skills": list(required), "skill_sources": list(sources)}


@lru_cache(maxsize=8192)
def _extract_job_skills_cached(skills_desc: str | None, description: str | None) -> tuple:
    """Use explicit skill labels plus named skills found in the job's prose.

    Most imported jobs only describe technologies in description. The same
    extraction feeds Jobs, the job roadmap and the CV coach, without database
    writes or a per-job LLM request.
    """

    field_text = _posting_text(skills_desc)
    description_text = _posting_text(description)
    catalog = {normalize_skill_name(name): name for name in JOB_SKILL_NAMES}
    result: list[str] = []
    seen: set[str] = set()
    sources: list[str] = []

    def add(name: str):
        key = normalize_skill_name(name)
        if key and key not in seen:
            seen.add(key)
            result.append(catalog.get(key, name))

    # Retain concise explicit labels, including tools outside our catalog.
    # Extract known names from prose instead of treating sentences as skills.
    for label in parse_required_skills(skills_desc):
        label = _posting_text(label)
        key = normalize_skill_name(label)
        if key in catalog:
            add(label)
        elif (
            0 < len(label) <= 50 and len(key.split()) <= 4
            and not re.search(r"[:!?]|\.(?:\s|$)", label)
            and not re.search(
                r"\b(?:experience|knowledge|proficiency|required|preferred|ability|with|in|and|or|of|must|strong|excellent|good|working)\b",
                label, re.I,
            )
            and key not in {"n/a", "na", "none", "null", "not specified", "skills", "requirements"}
            and not any(_skill_pattern(name).search(label) for name in JOB_SKILL_NAMES)
        ):
            add(label)
    if result:
        sources.append("skills_desc")

    for source, text in (("skills_desc", field_text), ("description", description_text)):
        mentions = []
        for name in JOB_SKILL_NAMES:
            match = _skill_pattern(name).search(text)
            if match:
                mentions.append((match.start(), name))
        if mentions and source not in sources:
            sources.append(source)
        for _, name in sorted(mentions):
            add(name)
    return tuple(result), tuple(sources)


def analyze_job_skills(resume_text: str, skills_desc: str | None = None, description: str | None = None) -> dict:
    extracted = extract_job_skills(skills_desc, description)
    return {**analyze_skills(resume_text, extracted["required_skills"]), **extracted}


def skill_present(skill: str, resume_text: str) -> bool:
    return bool(_skill_pattern(skill).search(resume_text or ""))


def evidence_for_skill(skill: str, resume_text: str, radius: int = 100) -> str:
    """Return a short resume excerpt around the first matching skill."""

    text = re.sub(r"\s+", " ", resume_text or "").strip()
    match = _skill_pattern(skill).search(text)
    if not match:
        return ""
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt += "…"
    return excerpt


def analyze_skills(resume_text: str, required_skills: Iterable[str]) -> dict:
    """Return matched, missing, and evidence-backed skill details."""

    matched = []
    missing = []
    details = []
    for skill in required_skills:
        present = skill_present(skill, resume_text)
        detail = {
            "name": skill,
            "status": "matched" if present else "missing",
            "evidence": evidence_for_skill(skill, resume_text) if present else "",
        }
        details.append(detail)
        (matched if present else missing).append(skill)

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_details": details,
        "coverage_pct": round(len(matched) / len(details) * 100, 1) if details else None,
    }


def compute_match_pct(raw_score: float, matched_count: int = 0, required_count: int = 0) -> float:
    """Combine semantic similarity and explicit skill coverage.

    This is a product score, not a probability. Keeping the formula stable
    makes it possible to evaluate and calibrate later with labeled examples.
    """

    semantic = max(0.0, min(1.0, float(raw_score))) * 100
    coverage = (matched_count / required_count * 100) if required_count else semantic
    score = semantic * 0.75 + coverage * 0.25
    return round(max(0.0, min(100.0, score)), 1)


def rank_job_matches(rows: Iterable[dict], resume_text: str, *, sort: str = "score", page: int = 1, limit: int = 25) -> list[dict]:
    """Rank all eligible jobs by displayed fit before selecting a page.

    Job extraction is cached independently of the user. Profile skill matches
    are reused only within this request so resume/progress edits apply at once.
    Evidence excerpts are generated later, only for the returned page.
    """

    presence: dict[str, bool] = {}
    ranked = []
    for row in rows:
        required = extract_job_skills(row.get("skills_desc"), row.get("description"))["required_skills"]
        matched = 0
        for skill in required:
            key = normalize_skill_name(skill)
            if key not in presence:
                presence[key] = skill_present(skill, resume_text)
            matched += presence[key]
        fit = compute_match_pct(row["raw_score"], matched, len(required))
        tie = (str(row.get("title") or "").casefold(), str(row["job_id"]))
        order = (*tie[:1], -fit, -float(row["raw_score"]), tie[1]) if sort == "title" else (-fit, -float(row["raw_score"]), *tie)
        ranked.append((order, row))
    ranked.sort(key=lambda item: item[0])
    offset = (page - 1) * limit
    return [row for _, row in ranked[offset:offset + limit]]


def job_market_statistics(rows: Iterable[dict], profile_text: str) -> dict:
    """Aggregate skill demand across every recommended job, once per posting.

    Percentages use all jobs above the recommendation threshold as the
    denominator. Detected skills may be mandatory, preferred, or simply
    mentioned in a posting, so the API deliberately avoids claiming otherwise.
    """

    jobs = list(rows)
    total = len(jobs)
    skills: dict[str, dict] = {}
    jobs_with_skills = 0
    fits = []
    bands = {"strong": 0, "good": 0, "exploratory": 0}
    presence: dict[str, bool] = {}

    for row in jobs:
        required = extract_job_skills(row.get("skills_desc"), row.get("description"))["required_skills"]
        seen = set()
        matched = 0
        for name in required:
            key = normalize_skill_name(name)
            if not key or key in seen:
                continue
            seen.add(key)
            if key not in presence:
                presence[key] = skill_present(name, profile_text)
            matched += presence[key]
            item = skills.setdefault(key, {"name": name, "job_count": 0, "in_profile": presence[key]})
            item["job_count"] += 1
        if seen:
            jobs_with_skills += 1

        fit = compute_match_pct(row.get("raw_score") or 0, matched, len(seen))
        fits.append(fit)
        bands["strong" if fit >= 80 else "good" if fit >= 65 else "exploratory"] += 1

    ordered = sorted(skills.values(), key=lambda item: (-item["job_count"], item["name"].casefold()))
    for item in ordered:
        item["percentage"] = round(item["job_count"] / total * 100, 1) if total else 0.0

    strongest = [item for item in ordered if item["in_profile"]][:8]
    gaps = [item for item in ordered if not item["in_profile"]][:8]
    return {
        "total_jobs": total,
        "jobs_with_detected_skills": jobs_with_skills,
        "average_fit": round(sum(fits) / total, 1) if total else None,
        "fit_bands": bands,
        "strongest_skills": strongest,
        "skills_to_strengthen": gaps,
        "all_skills": ordered[:50],
    }
